# DMA → 四轴连续运动 PL 交接 — 2026-10-13

固定源码提交：`22ea0a41daa974d24f16b72df7c31db212b7ab8f`。完整源码、规范、真实 PS 属性、厂商 IP 和证据 SHA256 见 `MOTION_RELEASE.json`；源码 SHA 使用 LF 规范化，IP/证据使用原始字节。后续交接提交不改变 RTL/ABI。接收本交接后 PL 任务结束，由 BSP 继续集成。本交付未下载板卡、修改 BSP、接电机或生成部署镜像。

## 冻结范围与兼容性

用户于 2026-10-13 回复“全部接受”，确认 `MOTION_INTEGRATION_CONTRACT_DRAFT.md` 六项推荐。唯一机器源是 `pl_interface/schema.json` 的 `motion_integration_profiles.gp_motion_v1` 和 `frames.motion_stream_v2`；C/Verilog 定义、寄存器/错误表由它生成。全局其他草案没有因此冻结。

- 新 GP：`0x80600000/4KiB`，A33/D32，VERSION1、PROFILE=`0x31544f4d`、CAPS=`0xf`、FEATURES=`0xf`；IRQ3/SPI85/INTID117，高有效 level。FEATURES 明确不支持 S2MM 遥测。窗口未与当前 recovery 镜像数字 CPU 资源冲突，最终 DT/HPF/IRQ 仍须 BSP 核对。
- 原 GP probe：`0x80400000/4KiB`、VERSION1/CAPSf/FEATURES7、IRQ0/SPI82、全部地址/数值/NOP/快照/IRQ/时间行为保持；原快照仍是原 profile 的空闲源。实际运动状态只从新窗口读取。
- 原 DMA：`0x80500000/4KiB`、IRQ1/2（SPI83/84）、真实 simple 双向 IP/HP0/参数与保护保持。独立回环入口及原回归保留；运动入口不会产生等长回包。
- Golden、单轴/四轴、continuous_motion/FIFO/planner 的算法不改。`motion_executor.v` 仅将两个连续赋值移到被引用声明之后，以兼容 Questa；接口、运算和时序不变。

## 72B 记录与 packet

`MOT2`/version2、length72、小端、8B 对齐，signed64 绝对目标 A0..A3；session u64、sequence u32 从0连续不回绕；每点相对 duration_tick（1μs），END 是末点，未参与轴 target=0。字段 offset/类型来自 schema；严格宿主 codec 为 `pl_interface/motion_v2.py`，不使用历史 80B Draft codec。

CRC32/ISO-HDLC 覆盖前68B，CRC 在68..71，reflected polynomial 0xedb88320，init/xorout=0xffffffff。KEEP 必须每拍0xff。一条 simple MM2S transfer 含1..910条记录（72..65520B），不跨/切记录；TLAST 只在该 packet 最后记录的最后一拍。提交前 GP PACKET_ARM 声明记录数量，并仅允许一个在途 packet。

`motion_stream_rx.v` 保存一整条，逐字节寄存 CRC，完整 header/版本/长度/保留位/mask/未参与目标/session非零/duration/CRC 与包边界合法才发布逻辑元组；背压期间全部字段保持。入队是每记录原子，不是整 packet 原子。后续记录损坏会取消会话及未执行点；此前实际 STEP 不回滚。不搜索 magic 重同步。

提前/缺失 TLAST、部分 KEEP、额外长度/错误格式使入口关闭并安全停止；生产者无后续 VALID 的截断需 BSP 超时后 GP STOP、terminate/reset。完整合法旧 session 只丢弃并计 stale，不破坏新会话；破损记录不能根据未校验 session 判为旧数据而忽略。

## 接线、资源与隔离

集成入口：`pl_dma/rtl/motion_gp_ps_top.v`。它替换原 GP/DMA 入口，包含原 PS 写所有权适配、真实 GP AXI3→Lite 转换器、三路 A33 路由、原 GP probe、真实 DMA/HP 转换器、新运动服务；不能再把旧 GP 从机并联接 GP0。接线文件由 `generate_motion.py` 再生，禁止手改生成 RTL。

GP0 是实际 PS A33/D32/ID12/LEN4/SIZE2/LOCK1，无 WID；保持 AW→B 所有权适配，内部补零及 WID 缓存。HP0 是 A33/D64/ID6/LEN4/SIZE2/LOCK1/QoS4，无 WID；DMA A32 地址补0，AXI4→AXI3 使用真实转换器，不截 LEN。HP ARQOS/AWQOS 为0，不承诺优先级。

H16 板载100MHz 同源驱动 GP/Lite/HP/DMA/运动，ASYNC0；GP probe 与新快照的1MHz时间逐拍一致已断言。p2f_rst0_n 为启动/整域 epoch reset：异步 assert、两拍同步 release，立即位置0/invalid、EN禁用，可能截短脉冲。运行中不 toggle 它。GP/HP PS 内部 soft reset 必须另由 BSP 确认已释放。

隔离实际 PS 顶层由 `build_motion_soc.py` 生成，厂商 PS property Tcl 仅重映射实际实例层级 `ps/DR1_PHY_PROCESSOR_SYSTEM_Inst`，属性值保留。仅有 H16 时钟 pad；STEP/DIR/EN 作为内部真实逻辑，通过 GP 观测，不绑定实体电机引脚。

所有发布 RTL 默认 H/L/速率等参数0，config_valid=0，不自动 ENABLE。STA/仿真显式使用 H/L/S/Q/E/OFF=3/2/4/7/5/3 cycles、max_rate10MHz，四轴同值，仅为验证夹具，不能用于实际驱动器。物理轴映射、极性、电气/驱动时序未批准。

## 控制及动态状态

正常流程：识别新 profile/FEATURES → 软件确认 DMA 静止 → 写递增 RECOVER_GEN 并 LINK_RECOVER → 停止态维护 MAINT=1/REBASE 四轴影子 → 显式 ENABLE → 新非零 SESSION/OPEN → PACKET_ARM/提交 MM2S → 查询 START_READY/接收结果 → 显式 START。

非安全命令 payload/事务 ID 捕获并寄存派发，串行单 writer。非零递增 ID、同 ID 同 payload 返回最近缓存，不重复动作；不同 payload、倒退或 busy 拒绝。PAUSE ACK.completed 到点边界才发布，RESUME 显式且准备好；END 优先于暂停。DISABLE 完成安全排空/失能延迟并撤销选定轴 valid；清错不恢复会话/EN。

STOP 是独立全字写 `STOP=1`，不经过 mailbox busy/事务编号。AW 和 W 分别捕获并预译码；合法配对写生效的同一个运动上升沿，直接抑制新 STEP、撤销会话/清队列，不等 DMA、S2MM 或遥测。已经发出的 H/L/DIR hold 完整排空，实际计数保留；stop_complete 表示 pulse-safe，B响应只表示写已接受。软件不得持有等待 PAUSE 的长锁而阻止 STOP ioctl。

GP 单独提供：DMA/packet/record/运动事实的分立状态、accepted/active/done sequence及valid、饱和接收/完成/stale/reject/cancel/stop/END计数、FIFO/预规划/总未执行水位、错误、session/link generation、四轴 position/position_valid、pulse_total、STEP/DIR/EN。

SNAP_REQ 使用独立非零递增 ID，不被等待 PAUSE 阻塞；同 ID 不重采样。全部 snapshot word 在同一个上升沿捕获边沿前已登记值，四轴64位位置与脉冲数来自同一时刻；保持至新快照，SNAP_ID/VALID 与帧一致。无效位置仍可保留诊断数值，必须检查 valid；计数不是编码器反馈。控制事务完成不代表运动点/整会话完成。

IRQ 为 pending&mask 的 level，W1C 同拍 set 优先；mask 不清 pending。接受/point_done/session_done/取消/停止/快照/控制应答分开发布，可合并为水位/计数通知。fault_latched 存在时 ERROR 源持续重新置位，先处理源/清错再 W1C/readback。统计只在整域 epoch reset 清零，普通清错/取消/DMA reset 保留。

## 取消与恢复握手

STOP/故障/欠流/记录错误/primary reset 清 raw、planner/准备队列、预测、完整暂存及半包、ARM；同拍禁止新 STEP，正常脉冲安全排空。DMA-only reset 从未接到 kernel rst_n 或时间戳 reset。新入口保持 CLOSED，不能随 reset 输出变高自动 OPEN。

硬件直接观察 MM2S HP 非 OKAY RRESP，检测同拍通过安全取消并锁存 DMA 错误。当前原厂 IP 无独立“error-only”输出，IOC/error 共用 IRQ：其他内部 DMA 错误必须由 BSP 解读 DMASR 后先 GP STOP；不能把所有 DMA IRQ 都连成 fault（正常 IOC 也会产生 IRQ）。其软件响应延迟尚未板测。

恢复顺序：阻断新提交 → GP STOP/等 pulse-safe → DMAengine terminate_sync → 按真实 controller reset 作用域停止相关方向 → 确认 HALTED/回调/tasklet/描述符与在途 DDR 静止 → 检查 PL 队列/半包清空与 primary reset 两拍释放 → 新软件 generation/LINK_RECOVER 应答 → 清已解除故障 → 从保留实际位置快照重新规划 → 新 session/OPEN/预缓存/START。

PL 的 FIFO 空、primary reset high、reset bit 自清或 LINK_RECOVER ACK 不能证明 DDR 静止。失败时 buffer quarantine，禁止释放/重用；旧回调按软件 generation 丢弃。PL 全历史 session 唯一性由 PS 保证；至少拒绝当前/最近关闭 ID，sequence 不回绕。

真实 DMA controller 可能同时复位两方向，任一 primary reset 都取消运动入口；这是共享 controller 生命周期，不是运动等待 S2MM ready。首版 S2MM tvalid=0、不投 RX。未来异步事件/RS485遥测需独立 FIFO/buffer/generation，满不背压运动/STOP；要让遥测 controller reset 完全不取消运动，需独立 controller 或另行证明隔离。

## 容量与性能依据

验证配置 raw64/prepared8/START32；planner 另有1条，解包暂存另有1条，正在执行点不计 buffered_points。最多73个已接受未执行点；原始/准备数据36520bit，不能把DMA内部缓冲算成产品 motion FIFO。

验证 envelope：Tmin100μs、补给间隔≤2ms、裕量1ms、2点规划裕量，ceil(3ms/100μs)+2=32。真实 DMA bench 在执行中等2ms再提交下一 packet，完成48点且无欠流。此处是仿真条件，不宣称 Linux 最坏调度已达到2ms。

2026-10-13 板测提交8.010..16.770μs，IOC完成17.160..104.970μs、口径吞吐199.756MB/s，只来自独立回环，不是持续运动保证。采用16..32条批量，不要求每点单独 DMA。实际 MM2S IOC 可先于最后 stream beat 消费，DMA完成、packet_closed、record_accepted、point_done/session_done必须分别查询。

现有非零 planner 延迟71拍、请求间隔73拍，逻辑记录入口至少提前74拍；解包/CRC/排队另加提前量。保留1μs点的已有内核回归，但本产品容量仍参数化；若产品要1μs与3ms覆盖约需3002点，持续72MB/s及真实成功提交下界须另测，不能直接沿用本验证配置。

## 实际验证与时序

Questa2025.2：独立 RX 276检查，72个字节分别损坏、完整记录变化 ready/背压保持、每个截断阶段取消；服务151597检查、114 start、22 done、114 cancel、旧会话、CRC合法的非法字段、不同四轴 Ni/方向/零差分、END/暂停、FIFO满、欠流、60个STOP及30个fault相位、busy PAUSE 时独立STOP/快照、DMA-only reset 后显式恢复、动态快照位置/脉冲原子性。

真实未经修改 Anlogic DMA/GP/HP converter：2150076检查、7次正常传输、1613 HP读拍、162 start/done，73点满缓存、96点批量、100μs/2ms补给、CRC拒绝、旧会话、在途GP STOP/controller reset/显式恢复及真实 HP RRESP 错误；没有任何 S2MM 写拍。新顶层原 GP probe 全套7632检查通过。Questa49项连接宽度 warning 均为原厂受保护内部，没有自研公开端口 warning。

既有单轴、四轴12组、连续组件/22组（包括73/74拍预检截止、欠流、各阶段STOP/故障/复位）、原GP、独立/共享DMA、接口、Golden全套通过；Golden算法/参数/基线不改。最终生成4文件逐字节一致，C定义与实际HDL核对1121常量通过。原批次 GP/DMA 验证 JSON 字节保留，新增结果独立保存。

TD Release_2026.1_SP2.200.067，DR1M90GEG400，**参考speed2**，实际PS属性、同源10ns；final工程 `pl_dma/build/motion_soc_final`：

| 阶段 | setup WNS | hold WNS |
|---|---:|---:|
| 门级网络估算 | −2.621ns | 0.000ns |
| 放置估算 | +2.821ns | 0.000ns |
| 最终布线/Both corners | **+0.454ns** | **+0.020ns** |

最终 STNS/HTNS=0，coverage99.99%，GP/HP实际PS模型捕获时钟均100MHz，critical warning0。无新增 false path/multicycle/放宽时钟；门级负估算保留，最终物理 STA 通过。route资源：LUT6 13995（26.67%）、FF14022（13.36%）、slice16203（30.87%）、ERAM16、DSP4、GCLK1/SCLK6；含原GP/真实DMA/互连/完整运动，不是裸内核资源。

最差 setup 是 executor next_slot[36]→pos[181] enable，8级、数据9.249ns。check_timing 无时钟/无效约束/组合环/缺IO delay均0；remaining HIGH 两类：原厂 ERAM 未用reset端、已验证 executor accumulator 的未用物理 ofb 输出。未删除诊断或修改原厂库；BSP须在最终工程审查。route native checker执行，日志封存；不冒称完整板级/安全签核。

失败保留：Windows沙箱 Icarus访问冲突/Questa DLL重定位，普通本地进程才运行通过；Questa前向声明兼容调整；首轮GP通用资格组合路径−10.306ns并TD布局崩溃，改寄存派发；第二轮STOP通用响应mux与ARM-ready形成结构环，中止并改独立STOP译码；随后STOP地址/数据预译码缩短路径。最终构建报告器最初误将门级估算当最终签核而退出1，未改TD结果；report-only核对所有实际构建源码一致，按最终route签核，保留原门级失败数值。原始日志/失败报告见证据索引/zip。

## 复现与 BSP 接入要求

工作区根、普通本地进程（Windows沙箱可能导致仿真器异常）：

```powershell
python pl_interface/generate.py --check
python pl_dma/prepare_ip.py
python pl_dma/generate_motion.py --check
python pl_dma/audit_ps.py
python pl_dma/audit_motion_address.py
python pl_motion/tests/run_motion_integration.py
python pl_dma/tests/run_motion.py
python pl_motion/tests/run_motion_regressions.py
python pl_dma/build_motion_soc.py
python pl_motion/verify_motion_delivery.py
```

Questa用-batch，不用本机故障的-c/RPC方式；不使用行为stub。build/仅可再生产物，真实PS生成配置/原厂IP保持安装版本与哈希。封存证据在 `pl_dma/reports/motion_20261013/evidence.zip`，index列原始字节SHA；数据库/minidump/保护库不入库。

BSP须新建受控运动client/profile绑定（本任务未修改BSP）：验证窗口/PROFILE/VERSION/CAPS/FEATURES/规范哈希；独占MM2S和controller恢复生命周期，不能原样用loopback-pair client或要求RX；32bit DMA mask、设备DMA API、至少8B对齐、BTT=count×72、coherent/streaming cache所有权和屏障；驱动单writer与短MMIO锁、STOP独立于等待控制完成；accepted/done/packet/IOC分开报告；PS全历史session与软件generation隔离；terminate失败quarantine。

实际系统应重新生成PS/HPF，原厂PS属性按真实层级加载，核对HP/GP soft reset释放、完整地址图、SPI85/level及最终clock/STA/DRC；保持DDR/存储配置。先在隔离输出、无自动使能的SD候选进行BSP/GP/DMA动态验证，再另行批准驱动参数/引脚/电气与电机联调；本交付不授权部署或实体使能。

未验证：新GP运动/IRQ3实板、Linux运动client与2ms最坏提交界、硬PS在途DDR静止、长期吞吐/背压/反复恢复、实物速度等级/时钟抖动、DDR电压/颗粒/压力、实体STEP/DIR/EN时序/驱动输入同步、HOME/限位/报警/Watchdog与物理机械恢复、完整S2MM遥测。命令位置不是驱动反馈或机械回零证明。AGENT.md已有修改和无关日志保留，不纳入交付提交。
