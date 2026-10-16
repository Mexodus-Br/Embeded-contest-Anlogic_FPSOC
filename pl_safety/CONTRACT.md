# PL 安全/HOME 契约 v1

2026-10-16。用户已确认行为并授权 RTL/自检；数值、电气/接线、实体轴映射未冻结。本文覆盖 CONTRACT_DRAFT.md 中的开放项与不同建议。生产配置禁止启动，独立仿真/资源夹具不得用于带电机运行。

## 行为与所有权

- 三限位和急停 NO 反馈均低有效，接点闭合接 GND。GPIO 为输入、须有上拉。急停 NC 属于外部切电链路；独立 NO 仅反馈动作，单路 NO 不检断线、不测 12V。
- 两级同步后快速触发、锁存原因；即使释放稳定时间尚未配置，已完成采样的急停断言仍被锁存；不加毫秒级触发去抖。独立 RELEASE_CYCLES 连续稳定释放，任一再次触发将释放资格清零。复位初始化为未获许可，输入资格完成前不允许 HOME。
- 普通轨迹/点动任一限位触发：整组取消，撤销三轴 position_valid，保留已输出计数；取消 PL session、FIFO、预规划和 transport 半包，禁止迟到记录复活。M4 当前未配置，未增加独立继续策略。
- 普通 STOP 保留 EN/位置有效性；HOME 中 STOP/失败必须完整重做。急停反馈撤销三轴 valid，取消任务/HOME，禁止新 STEP，脉冲安全排空后按已有 EN_DISABLE_CYCLES 失能。
- 急停释放后需人工确认、显式 CLEAR_FAULT，再显式 HOME。清 IRQ/清错/供电恢复不会重新使能、重开 session 或自动启动。PS 任务生命周期须由后续 BSP/服务消费取消状态与 IRQ；本批不实现 BSP/HMI。

现有 motion_executor 是唯一 STEP/DIR/EN 和 position 所有者，HOME 使用其私有端口、原 H/L/S/Q/E/OFF 年龄计数与脉冲排空。HOME接受当拍撤销valid和普通所有权；其专用EN授权寄存一拍后进入已由HOME持有的空闲执行器，断开pulse-safe经启动许可回到普通执行控制的长组合链。输入快停、STOP和立即失效仍直接生效，优先于延迟的EN授权。无第二套脉冲源、无 STEP 与门、无公共复位停止、无假 REBASE。

## HOME 状态机

`NEED → PRE → SEARCH → SEARCH_DRAIN → REF → PULL → FINISH → READY`。
STOP/失败进入 DRAIN，停稳后到 NEED 或 FAULT；锁存故障须显式清除。READY 表示安全层已完成 HOME，普通运行状态仍由原运动服务报告。

1. HOME_START 仅在配置完整、输入资格完成、急停稳定释放、故障清除、无普通命令在途、无 session/partial/FIFO/planner、executor 空闲且 pulse-safe 时接受。该显式命令授权 HOME 所需 EN；无公开 HOME_ARM。
2. 接受时三轴 valid 原子撤销；关闭 transport 的旧所有权。PRE 记录启动时闭合的开关，仅相应轴反向运行，其余轴等待。每个需退离轴执行独立 PRE_DISTANCE，要求终点触点已释放且取得稳定资格；有独立最大步数与时间上限。预退离不建立参考、不恢复 valid。参数未定时不填机械默认值。
3. 全部预退离条件满足且停稳，进入一次三轴并行 SEARCH。固定步频、无加减速；每轴首次同步触发独立禁止该轴新边沿并锁存 hit，其他轴继续。任一搜索步数/时间上限先到整组失败。
4. 全部 hit 且 H/L/Q 排空后，REF 通过私有门载入各轴 signed64 REFERENCE_POSITION，public valid 仍为 0。
5. PULL 反向固定步频执行每轴 PULL_DISTANCE，独立到达后停止。终点仍闭合、稳定释放后重闭合、上限或内部错误均失败。终点电平已释放但资格计数尚未完成时只等待稳定判据，不增加距离；等待也计入退离超时。没有二次接近或自动重试。
6. 全部达到配置距离、稳定释放且 pulse-safe，FINISH 原子置三轴 valid，报告 HOME_DONE。最终位置 = reference + 实际带符号退离步数。

限位恢复不构成死锁：停止后 valid 为 0 的闭合限位可在急停健康、停稳且无其他持续源时显式清错，状态只能回 NEED；只有上述有界 HOME/PRE 获得运动权限，普通运动仍被禁止。

HOME 候选边沿先做整组时序/溢出预检，任一候选轴将溢出则同拍全部不发 STEP。任何安全动作覆盖新请求和 STEP。多原因 OR 锁存，首事件时间不被后续事件覆盖，急停与其他源同拍时首因为急停。公开 REBASE 在新安全 profile 中被拒绝；原 legacy profile 行为保持。HMI 使能预览没有本接口的运动副作用。

## 时间与响应

使用实际共享 system_time_us（u64、1MHz、100MHz 同源/整域复位）。事件/快照采样边沿前登记值；不因 STOP、清 IRQ/清错或 DMA-only reset 重置。u64 时间/事件序号按模 2^64 观察；阶段超时为无符号差值，配置 max_us 必须非零且小于 2^63。

稳定异步触点在第一个采样边沿进 meta，第二边沿进 sync，第三边沿执行器禁止新 STEP：RTL 数字模型 pad→禁止新边沿为 2..3 个周期（20..30ns），同步 active→执行器禁止新边沿为 1 个周期。各触点短脉冲能否被采样取决于采样相位；本接口没有异步捕获器。该预算不包含外部 RC/传播、实体布线和亚稳态统计风险，不替代尚未冻结的物理最大响应指标。

已有高脉冲精确完成 H；低电平 L 与方向保持 Q 同时满足后 pulse-safe。EN 另等待原 OFF 延迟，仅急停/显式 DISABLE 关闭 EN。保守排空边界为检测后 `max(H+L,Q)+2` 个周期；含状态提交的 EN_OFF 保守上限再加 `OFF+3` 周期，使用宽算术评估，实际各轴由残余脉冲相位决定。时间戳单位 1us 不能分辨上述亚微秒预算，仿真用 100MHz cycle 和实体 STEP 边沿单独核验。

RX 数据错误仍在原检测当拍停止正常执行；只将发给 HOME 的错误通知寄存一拍，断开 error→abort→error 组合反馈。HOME 入口要求 transport 空闲，且执行期间不接收普通 session。持续安全源保持禁止和 transport 取消，只首次断言触发执行器排空，不反复制造 stopped。

## 软件可见接口

唯一机器源：pl_interface/schema.json 的 safety_profiles.gp_safety_home_v1；由 pl_safety/generate.py 生成 C/Verilog 定义。旧 ABI/数值、72B MOT2、32B 采集和64B遥测记录不变。

- 候选资源：0x80A00000/4KiB，A33/D32；f2p_irq[7]/SPI89/INTID121，高有效 level。最终地址/GIC 由 BSP 核验。
- PROFILE=0x31464153（LE SAF1），VERSION=1。CAPS/FEATURES=0x3f，bit0..5 为三限位、并行HOME、固定退离、急停反馈、原子快照、配置身份；不包括 Watchdog/RS485自动停机。
- 命令：HOME_START=1、CLEAR_FAULT=2，ARG=0。非零 u32 TXN 单调递增不回绕；相同最近 ID/内容只返回既有结果，不重放。同 ID 不同内容、倒退、新命令遇 busy 为 SLVERR。
- HOME 接受与完成分开：ACK_STATUS bit0 valid、1 accepted、2 complete、3 busy、4 snap_valid。ACK_ERROR 为 OK/REJECTED/CANCELLED。HOME 失败/STOP 需排空/释放 owner 后才发布取消完成。
- STOP=1 是独立全字写，不被命令 busy/事务编号阻塞；原运动窗口 STOP 同样中止 HOME。B 应答不表示机械停止或 EN 已关闭。
- 所有写要求对齐/full WSTRB；非法窗口（包括 A33 高位）DECERR，非法偏移/值 SLVERR。AW/W 独立捕获，读写响应各自保持所有权和背压稳定。
- SNAP_REQ 为非零递增 u32，捕获 64 words 的完整快照；重复/倒退 ID 拒绝。各字段与偏移使用生成定义。快照含状态、输入/释放资格、原因/首因/首时、事件序号、逐轴 hit/released/distance_done 掩码、valid/EN/pulse-safe、共同时间、HOME开始/完成时间、signed64位置、阶段步数与累计真实脉冲。
- MASKS bit[2:0] hit、[6:4] released、[10:8] distance_done。hit 不等于已经完成脉冲排空；最终看 pulse-safe/状态。TRAVEL 为当前阶段实际步数，不是编码器反馈。
- IRQ_PENDING bit0 锁存故障（持续原因 set 优先）、bit1 HOME_DONE、bit2 命令结果、bit3 stopped；IRQ_MASK 同位。W1C 不改变运动状态。
- CONFIG_ID_0..7 返回当前安全配置规范化 JSON 的 SHA256，低 word 先读；CONFIG_VALID 还检查外层驱动参数/步频及参考终点溢出。配置 hash 只标识安全配置 JSON，完整驱动参数、源码/IP/约束身份见构建清单。

## 配置和集成

CONFIG_PROFILE=0 使用 production.json：未批准/零参数，不能 HOME、普通 ENABLE/START 或用维护 REBASE 绕过；这是发布默认值。
PROFILE=1 为 simulation.json；PROFILE=2 为 resource_fixture.json，匹配原完整顶层500cycle/100kHz夹具。两者是明确的非生产夹具，不代表驱动器或机械保护参数。方向、距离/参考、各阶段速度/上限、释放稳定时间均为显式 elaboration 配置；参考值加带符号退离距离必须落在 signed64 范围。

新生成链：safety_rs485_gp_ps_top → safety_rs485_gp_full_top → safety_rs485_shared_lite_top（七窗口）→ safety_motion_dma_lite_top → safety_motion_service → 原 continuous/executor 的 HOME_SUPPORT=1 模式。
旧生成顶层及其 .fault(4'd0) 保留原身份/行为，不是安全交付入口。新入口的三限位/急停经专用 stop/invalidate/HOME 门接入，不将 HOME hit 转成普通全组 fault。

当前不分配新实体针脚。完整工程保留原九路 J12 观察输出、RS485、PS/HP0/HP1/DDR及原时钟约束，新增四个异步输入端口；参考构建的自动 pad 位置不构成接线授权。新安全输入上拉/保护/电气、轴映射、驱动供电恢复及真实机械停止仍须项目方验证。
