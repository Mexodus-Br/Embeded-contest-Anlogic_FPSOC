# PL 安全/HOME 最小契约草案

2026-10-16，基于核验后的 HEAD c9f2e05。状态：历史评审草案。开放项已由用户后续确认，现行行为与实现契约见 [CONTRACT.md](CONTRACT.md)；本文不是实现或验收证据。
本任务已授权创建 pl_safety 及必要接口/生成器/顶层改动。已确认规则不再征询。

## 1. 基线与现有门禁

- 开始时 tracked 文件无修改；大量 untracked 日志、build/报告和旧证据保留。
- 运行 round2/seal.py --source-commit f7b570bc59b117a7f902cbdb81c8bad866954d4d --verify：PASS，核对源码/Git/证据/IP/schema/约束。命令输出和本轮关键输入哈希见 BASELINE_AUDIT.json。
- 最新实际完整候选为 bsp/work/telemetry_opt_r2main/system/hdl/system_wrapper.v，实例 rs485_gp_ps_top，经 full/shared 封装接 motion_dma_lite_top → motion_service → continuous_motion → motion_executor。不是仅含运动的历史 motion_gp_ps_top。
- motion_dma_lite_top 当前仍有 .fault(4'd0)。service 中 fault 会取消 transport/会话；continuous 清 raw/planned FIFO；executor 禁新 STEP 后排空 H/L/DIR hold。正常 STOP 保留 EN 和实际已输出计数。
- executor 的 position_valid 与 EN 启动互锁；REBASE 要求所选 EN 禁用、空闲且无故障。直接给未知坐标 REBASE 再 ENABLE 不能冒充 HOME。
- 现有 executor fault 为整组停止，不能表达 HOME 的三轴独立停靠。axis_motion 虽可单轴 STOP，但拥有另一套 STEP/EN/位置，不直接并联为第二套输出所有者。
- 实际系统由 rs485_probe_time_regs 输出 system_time_us；motion_service 另有同源同复位的 1MHz counter。新安全事件直接采样 system_time_us，禁止另起相位不明时间基准。
- round2 仍为 CANDIDATE_PENDING_USER_REVIEW，signoff_pass=false。原 SYN-5066、RS485 IO delay 资格、实物 speed 未确认以及 RX 静止保证问题不因安全开发消失。
- 完整候选旧资源：LUT6 26090、Slice 33222、REG 34381、ERAM 58、DSP 6；参考 speed2、100MHz route setup +0.305ns、hold +0.020ns。这些不是新增安全链的资源/时序结论。

## 2. 拟议模块及所有权

1. safety_inputs：三限位及一急停反馈；各路参数化极性、两级同步、独立断言/释放资格计数和启动资格。输入未完成资格时禁止启动。只生成同步语义信号，不直接组合门控 STEP。
2. safety_controller：全局状态、故障/原因位图、首因及时间戳、HOME 阶段和逐轴掩码、控制仲裁、恢复门禁。
3. safety_regs：A33/D32 AXI-Lite、独立 STOP、显式命令/事务结果、原子快照和 level IRQ。
4. executor 扩展受控 HOME 模式，复用已有 H/L/DIR/EN 年龄计数、脉冲排空与 signed64 溢出检查。HOME 逐轴边沿请求与正常 plan 提交互斥。executor 始终唯一拥有 STEP/DIR/EN、命令位置与脉冲计数，无输出 mux 热切换。

所有新增端口/参数为显式连接；旧调用缺省不启用安全模式。新安全候选必须显式开启并连通输入，未配置不允许普通运动。旧 profile 及原独立工程继续原行为，不把 legacy 模式报告为安全链已接通。

HOME 从未知位置启动需要专用 HOME_ARM/私有参考提交门，不能放宽公开 REBASE/ENABLE 的既有条件：

- HOME_START 只有安全参数完整、输入已资格、急停未动作、无锁存故障、normal executor pulse-safe、无 session/队列/部分记录及未结控制时才接受。
- HOME_START 是显式产生运动/驱动 EN 的命令；HMI“使能/预览”不能触发它。HOME 可在 position invalid 时只获授权执行有时间及步数上限的参考搜索；普通 plan 仍被禁止。
- 本轮建议 HOME_START 显式授权 HOME 的 EN 与低速搜索；若要求另设 HOME_ARM，再由 HOME_START 启动，则由用户选择。
- HOME owner 获得前关闭/取消旧 transport，确认其 PL partial/FIFO/planner 清空；拒绝迟到旧记录，不自动恢复旧 session。PL 清空不表示 DMA/DDR 已静止；BSP 仍按原恢复契约管理 buffer。

## 3. 状态及停止优先级

拟定状态：INIT → NEED_HOME → HOME_SEARCH → HOME_SEARCH_DRAIN → HOME_REFERENCE → HOME_PULLOFF → HOME_PULLOFF_DRAIN → READY。
普通执行为 READY → RUNNING → READY；STOP 经 STOPPING；故障经 STOPPING → FAULT_LATCHED；急停经 STOPPING → ESTOP_LATCHED。状态与 STOP_COMPLETE/EN_OFF 分开，不用单个 FAULT 状态掩盖排空进度。

- SEARCH：三轴并行。各轴资格触发当拍禁止该轴新 STEP，上升沿计数不回滚；该轴完整排空后设置 stopped_mask，其他轴继续。三轴全部触发且 pulse-safe 才捕获参考。
- REFERENCE：每轴参考值属于定义好的资格触发/停止位置；记录 raw 同步事件与 qualified 事件时间。触点物理闭合至资格触发的额外行程必须计入硬件/滤波预算，不声称是机械零误差。
- PULLOFF：反向并行低速退离，等待各轴稳定释放并达到该轴净空，独立停止；全部稳定释放且停稳才 HOME_DONE/READY。无二次接近。释放后再次闭合须停止并按失败处理。
- 单轴搜索/退离超时、步数耗尽、数值溢出或内部时序不变量失败均取消全部 HOME、整组安全停止；不能让其他轴无限继续。
- 普通运动/点动任意限位资格触发，三轴全停、取消当前任务与未来排队点。当前四轴底座采用整组取消，M4 当前禁用；本批不授予 M4 独立继续策略。

安全动作优先于接受 HOME/ENABLE/REBASE/OPEN/START、plan 边界和所有新 STEP；HOME 预期单轴触点事件只在 HOME 对应阶段有特许语义。并发原因全部 OR 锁存，首因显示优先级建议：急停 > 内部故障 > 普通限位/HOME失败 > DISABLE > STOP > 非安全请求。安全动作取并集，低优先级不能取消高优先级的 invalid/disable。

正常 STOP 完成已有 H/L/DIR hold，禁止新边沿，不用异步 reset 或 STEP 与门截断脉冲。复位仍仅为整域 epoch 初始化，不能当正常 STOP。

## 4. 位置契约（建议，待确认）

- executor 单点写入命令位置；每个真正 STEP 上升沿更新一次。外部反馈/预测轨迹不能修改它。
- HOME 开始撤销三轴 public position_valid；搜索期间保留可诊断的相对计数，不能对外报告可靠关节坐标。
- 三轴搜索并安全停止后，仅 HOME 私有门加载确认的 signed64 reference_step，public valid 仍为 0。随后退离每个真实边沿继续计数。
- 最终位置 = reference_step + 实际带符号退离步数，不把退离终点随意重新归零。全部释放并停稳后原子置三轴 valid、记录 HOME_DONE。
- HOME 中 STOP/失败：三轴 valid=0，清除此次参考完成掩码，须新一次完整 HOME。诊断计数保留。
- 普通 STOP 保留 valid；普通限位建议撤销三轴 valid、要求重新 HOME。此项属于恢复策略选择，未冻结。
- 急停反馈建议当拍撤销三轴 valid、取消会话/transport/HOME；禁止新 STEP，完整脉冲排空后按 EN disable delay 撤销 EN。反馈释放仅解除物理源，不清锁存、不恢复 EN/任务/valid。
- 急停恢复建议：源稳定解除 → 人工确认供电/驱动目标一致性 → 显式 ACK/CLEAR → NEED_HOME → 显式 HOME → READY → 新 session/预缓存/显式 START。急停辅助触点不证明 12V 已消失或恢复。ACK 不代替实测或驱动目标校准。

## 5. 输入规则与响应预算（待选择）

建议限位为外部上拉、闭合接 GND 的低有效输入；急停反馈电平待实际电气拓扑确认。J12 BANK11 固定 LVCMOS33，不能直接输入 12V/工业电压或推挽拉高后触点短地。本轮不指定未经核验的新实体针脚。

建议断言走两级同步后的快速路径（连续 1 次采样即动作），释放使用独立稳定计数；HOME 捕获需与停止使用同一资格事件，不能停后抖动重新写参考。若需连续 N 次断言去抖，必须接受其额外行程/响应延迟。对任意相位稳定输入，从 pad 到禁止新边沿的 RTL 预算为两级同步、N 次资格及最终执行消费的明确有界拍数；采用保守 (N+4)×10ns 设计上限并在实现中逐相位自检核对，任何额外寄存/路由级都必须计入。物理传播、外部 RC、触点行为及亚稳态统计风险另行列出；不能将此公式视为未测实板的绝对响应保证。

分别报告 pad→同步观察、资格断言→禁止新边沿、到 pulse-safe、到 EN_OFF 的时间；后两项依 H/L/Q/off 参数变化。急停动作反馈与 12V 切断时序分别验收。

## 6. 新接口建议（待冻结）

保持 pl_interface/schema.json 为唯一机器源，新增 gp_safety_home_v1，不改旧 profile/MOT2/采集 ABI 的值或结构。新 profile 建议 VERSION=1、PROFILE=0x31464153（LE SAF1），capabilities 明确三限位、并行HOME/退离、急停动作反馈、锁存事件/快照；不宣称 Watchdog/RS485自动停机能力。

新窗口建议 0x80A00000/4KiB，f2p_irq[7]/SPI89/INTID121、高有效 level。仅检查现有 schema 中 0x804..0x809/IRQ0..6 未占用此项；最终 PS/BSP 地址与 GIC 由项目方核验。扩展生成器为七窗口独立新路由，不修改旧六窗口行为；A33高位/边界/非法地址/独立读写与背压所有权必须自检。

候选布局（每个 word 32bit，64bit 字段 little-endian；数值最终由 schema 生成）：

|偏移|内容|
|---|---|
|0x000..0x00C|VERSION/PROFILE/CAPS/FEATURES，只读|
|0x010..0x01C|OPCODE/ARG/TXN/SUBMIT；HOME_START、CLEAR_FAULT、ACK_RECOVERY，非零递增事务 ID及重复防护|
|0x020|STOP=1 独立全字写，不等待 mailbox；原运动窗口 STOP 也必须中止 HOME|
|0x024..0x02C|ACK_ID/ACK_STATUS/ACK_ERROR；接收、执行、完成分开|
|0x030..0x038|IRQ_PENDING(W1C)/IRQ_MASK/SNAP_REQ；set优先，持续源清不掉|
|0x040..0x04C|状态/原始同步输入/资格输入/锁存原因位图|
|0x050..0x05C|FIRST_CAUSE、FIRST_TIME_LO/HI、EVENT_SEQUENCE|
|0x060..0x06C|逐轴 hit/stopped/released/done 掩码与位置有效性/EN/pulse-safe|
|0x080..0x0BC|三轴 reference_step 及最终命令位置的 signed64 快照|
|0x0C0..0x0C8|快照 ID/快照 time_lo/hi|
|0x100..|逐轴首次触发时间、释放时间、实际搜索/退离步数及 HOME 开始/完成时间|

最小故障原因包含 LIMIT_A0/A1/A2、ESTOP_FEEDBACK、HOME_START_ACTIVE、SEARCH_TIME/STEP_LIMIT、PULLOFF_TIME/STEP_LIMIT、RECONTACT、PARAM_INVALID、POSITION_OVERFLOW、EXECUTOR_FAULT；STOP/HOME_DONE 为事件、不伪装故障。首因时间/来源不被后续故障覆盖，累计原因保留；清错仅在源解除且停稳后接受。新增事件序号检测漏读，原子快照避免64bit撕裂，不以W1C自动恢复运动。

本批建议参数使用版本化 elaboration 配置 JSON，经脚本生成参数，不开放运行中可写配置寄存器；生产数值未确认则 config_valid=0。仿真夹具明确独立标识。配置含极性/资格、每轴方向/搜索及退离period/reference_step/步数与时间上限、净空及释放稳定阈值、驱动脉冲时序及EN极性；角度换算由 PS 参数边界给出最终 signed64 步数。

## 7. 待用户集中决定

1. 限位低有效是否冻结；急停反馈选 NC闭合健康/断开动作（可将断线视动作）还是 NO闭合动作（不能单独检测断线）；断言快速或 N 次稳定采样、释放稳定时间，以及 pad→禁STEP 最大要求。电气未知可保留可参数化且生产禁用，不猜值。
2. 每轴实际 A0/A1/A2→M1/M2/M3 映射、HOME DIR、搜索 step/s 或 period_cycle、reference_step（或参考角度及换算配置）、搜索 max_step/max_us。
3. 启动时开关闭合：建议拒绝 HOME并报 START_ACTIVE；备选受限反向退离至稳定释放/净空，再进入本来的一次搜索（属于新增启动前流程，需要明确选择）。
4. 每轴自动退离速度、释放后额外净空步数、稳定释放时间、max_step/max_us；选择“稳定释放+净空”还是“固定退离距离且最终稳定释放”。
5. 接受 HOME 开始/STOP/失败三轴坐标 invalid、仅完整成功才 valid，以及普通限位 invalid/重新HOME建议，或给出替代恢复规则。
6. 接受急停后取消任务、invalid、pulse-safe后EN关闭、释放后人工ACK/清错且重新HOME；或明确不同的EN/坐标/恢复策略与条件。
7. 接受独立地址/IRQ/profile、上述最小字段、配置首版只读及显式 HOME_START 授权EN；或给出资源/字段/独立HOME_ARM偏好。用户原消息末尾“及最小”截断，待补齐未发送的约束。

## 8. 实现、自检和交付门禁

确认后先 safety_inputs/controller 与 executor HOME 单元 self-checking，再接 continuous/service/真实DMA/实际PS候选；不得以仅采样GPIO/fault接线宣称完成。

验证覆盖：任意相位输入/抖动/极性/启动资格；三轴各种触发顺序及同时触发、某轴停其余继续、全停后才参考、退离释放/净空、无二次接近、启动闭合选定策略、搜索及退离双上限；STOP/限位/急停/disable在各相位及plan边界并发；无新边沿、完整H/L/Q/EN延迟；坐标仅按真实边沿且失败invalid；旧会话/半包取消、迟到记录不可恢复；GP背压/A33/重复命令/W1C/原子时间快照；默认零配置禁止运动。

保留旧单轴/四轴/连续/GP/DMA/RS485/接口生成及Golden回归。真实IP仿真使用当前厂商模型，Questa许可证单会话串行。失败日志保留，不通过放宽判据、覆写旧证据或改原厂IP处理。

资源与时序使用独立新tag实际 system_wrapper 候选：固定原PS/IP/DDR参数、100MHz/10ns、参考speed2、原九输出/RS485约束，新增输入CDC约束明确到同步器首级；不放宽内部时钟、不加掩盖同步逻辑的false path。报告裸安全组件与完整顶层各自结果，完整顶层资源不能用组件加减推算。区分 gate/place/route、setup/hold、coverage及原/新diagnostic；新输入物理引脚/IO资格未核验则不报告板级签核。

独立交付包括源码提交、唯一schema生成物、参数来源、自检结果、完整日志、资源/100MHz STA、源码/IP/配置/约束/证据哈希和交接说明。原发布与身份门禁不放宽；必要的新身份授权只对本批精确文件/哈希生效。不操作COM4/板卡/启动存储，不生成部署镜像，不执行自动REBASE/ENABLE/START。Watchdog和RS485故障自动停机策略不在本批。
