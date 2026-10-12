# DMA → 四轴连续运动：集中确认稿

2026-10-13。状态：**USER_CONFIRMED / IMPLEMENTATION_IN_PROGRESS**。用户回复“全部接受”，确认六项推荐及验证配置；产品容量继续参数化。原提案/备选文字保留为评审记录，备选不属于本次选择。新 profile、字段和错误码落实到 `pl_interface/schema.json` 并生成 C/Verilog 定义。本文件不是 MOTION_HANDOFF。

## 已读基线与保留范围

基线提交：`7966c8335b1f40b0880616911120917f494b5ae5`。依据：AGENT.md、PHASE0_CONSTRAINTS.md；pl_interface 的 README/SPECIFICATION/MOTION/TELEMETRY/REGISTERS/DMA_LINUX/DECISIONS/VALIDATION/schema；pl_motion 的 README/CONTINUOUS/GP_CONTROL_DRAFT/GP_INTEGRATION/VALIDATION/GP_VALIDATION；pl_dma 的 README/VALIDATION/DMA_HANDOFF，以及 BSP BOARD_VALIDATION 的 2026-10-13 实板结果。

保持 Golden Model、单轴/四轴算法、continuous_motion 的绝对目标、sequence/session、共同槽、预规划、END、暂停、安全排空契约。原 GP probe 的窗口 `0x80400000/4KiB`、VERSION=1/CAPS=0xf/FEATURES=7、空闲快照源、寄存器数值和 IRQ0 行为保持；动态四轴快照在新增独立 profile 提供。DMA 窗口 `0x80500000`、IRQ1/2 和真实 HP0 端口保持。

旧 DMA/GP 文档中的“未板测”是原批次历史状态。2026-10-13 BSP 已验收独立回环：444 场景、18 次预期异常恢复、GP epoch 保持、errors=0。该证据没有运动 FIFO、记录解包、动态运动或运动取消，也没有持续生产吞吐签核。

此次不下载、不生成部署镜像、不修改 BSP、不绑定实体 STEP/DIR/EN、不自动使能。AGENT.md 的已有修改和无关日志不处理。

## D1：新线格式（推荐 72B，独立版本）

对比：旧 80B 候选有未使用 batch_id 和额外保留空间；128B 是遥测草案。最小执行记录实际需要 header、session、sequence、END/mask、duration、四轴目标及 CRC。推荐独立 `motion_stream_v2`，72B/9 个 64bit 拍，小端、8B 对齐，避免把旧 Draft 编解码样例误认成可执行格式。

| 字节 | 字段 | 校验 |
|---|---|---|
| 0..3 | magic，字节 `MOT2` | 固定 |
| 4..5 | version=2 | 只接受此版本 |
| 6..7 | length=72 | 不接受扩展/缩短 |
| 8..15 | session_id u64 | 非零，必须匹配当前 OPEN |
| 16..19 | sequence u32 | 从 0 连续、不回绕 |
| 20..21 | flags u16 | bit0 END，其余零 |
| 22..23 | axis_mask u16 | 仅低 4 位可用 |
| 24..31 | duration_tick u64 | 非零，乘 100 不溢出 u64 |
| 32..63 | A0..A3 signed64 绝对目标 | 未参与轴 target=0；逻辑轴不绑定实体 |
| 64..67 | reserved u32 | 零 |
| 68..71 | CRC32/ISO-HDLC | bytes[0:68]；reflected polynomial 0xEDB88320，init/xorout=0xffffffff |

CRC check(`123456789`)=0xcbf43926。CRC 是完整性检查，不取代 DMA/AXI 状态，也不认证来源。完整线校验后才向 continuous_motion 提交整条逻辑元组；运动时序可行性继续由现有 planner 检查。first target 不隐式 REBASE。

备选：经本次明确审查后选择旧 80B 布局，保留 batch_id；这会多 1 个流拍和 11.1% 数据量。任何选择均须建立本次冻结记录，不能直接继承旧 Draft 状态。

## D2：packet 与 TLAST（推荐批量；修改旧单记录单 packet 选择）

一条 simple MM2S transfer 是一个 packet，含 1..910 条连续 72B 记录；最大 65520B，遵守 BTT16 上限 65535B。TLAST 只在该 packet 最后一条记录的最后一拍；全部 KEEP=0xff。不允许记录跨 packet，不搜索 magic 重同步。USER/ID/DEST 无运动含义。

GP `PACKET_ARM(record_count)` 在每次 DMA 提交前声明期望记录数，捕获当前 session 和 link generation。一次仅允许一个在途 packet；须上一 packet 接收结束或取消后再 ARM。声明使接收器能在最后一拍立刻区分缺失 TLAST 与合法中间记录，也能识别短、长包。ARM 不代表 DMA 已完成或记录已经接受。

记录单独原子提交，**不是整 packet 原子提交**。后面的损坏记录/包边界错误会取消整个会话和全部尚未执行记录，但已输出 STEP 不回滚。已验收正确的前面记录可能已开始执行；若要求整个 packet 验证后才执行，需要额外整包存储，另选架构。

packet 接收器只在 VALID&&READY 时消耗字节；背压时保存完整记录、CRC、计数和所有元数据。提交端 valid 不等待 ready；持有期间数据稳定。已声明最后一拍缺 TLAST、提前 TLAST、非全 KEEP、额外拍或错误格式均不提交该条记录，锁存错误并取消；关闭入口等待显式链路恢复。VALID 长时间未到不由接收器猜测截断：BSP 超时后必须 GP STOP/取消，再 terminate。

推荐批大小 16..32；短 END 可用 1 条。预启动 packet 不得超过可容纳的未执行记录数，否则等 DMA 完成才 START 会死锁；可等 `start_ready` 后 START，使 DMA 与执行并行。生产者依 GP credit/水位提交，不凭 DMA IOC 判断缓存空闲。

旧选择“一记录一 packet”可以保留为 count=1 特例；推荐允许批量是本次需用户确认的契约变更。每记录单独提交的实板提交开销至少 8.010μs，不能支持 1μs 连续点流。

## D3：GP 独立控制 profile 和完成通知

推荐新增 `gp_motion_v1`，独立 `0x80600000/4KiB`，完整 A33/D32 decode，经现有 GP0 真转换器和三路 Lite 路由。建议 IRQ3（SPI85/INTID117，最终须 BSP 审核），高有效 level。新窗口必须对当前及最终 BSP 资源重新审计；不修改原 GP probe VERSION/FEATURES 或动态替换其空闲源。

首版新窗口提供 PROFILE_ID/VERSION/CAPS、配置有效标志、容量/阈值、控制事务、独立 STOP、PACKET_ARM、恢复握手、实时水位/ready，以及动态快照。所有寄存器/字段/opcode/error/IRQ 数值只在 schema 定义后生成；具体 offset 分配是确认后的实现步骤，保留原全部定义。未实现功能不标 capability。

非安全控制沿用单 writer、非零递增事务 ID、最近同 ID 同 payload 返回缓存、不同 payload 拒绝、busy 不覆盖。支持 OPEN/ENABLE/START/PAUSE/RESUME/DISABLE/CLEAR_FAULT/维护 REBASE/SNAPSHOT/LINK_RECOVER；HOME、软限位、运行时配置提交不在本集成 profile 宣称完成。

新增 STOP 独立全字写入口，不经过普通控制 mailbox 的 busy 或事务编号门。配对合法 AW/W 并接受写副作用的那个运动时钟上升沿，直接优先禁止新 STEP、撤销 session、清所有队列及半包；无需 DMA/遥测/IRQ handler 应答。B 响应表示 GP 写已接受；`stop_complete` 另在四轴 pulse-safe 后发布。不能承诺从 CPU 发起写到停止的固定延迟。

OPEN/START/PAUSE/RESUME/REBASE 复用 continuous_motion 门：START 首点已预检且达到阈值，短 END 例外；PAUSE 到当前点边界，END 优先；RESUME 显式、下一点 ready；维护 REBASE 须维护标志、选定轴 EN 禁用、全组空闲/无会话/所有缓存和半包为空，并原子载入 signed64。REBASE 不清 pulse_total/时间戳。ENABLE 只由显式事务触发，默认驱动参数为 0、配置无效，禁止自动使能。

通知分开：

| 事实 | 观察口 | 含义 |
|---|---|---|
| DMA IOC / callback | 原 DMA 寄存器/IRQ、BSP | DMA 字节传送结果；不证明记录合法 |
| packet_closed | 新 GP packet 状态及累计完成编号 | 期望字节和 TLAST 边界匹配；不保证每条点被接受 |
| record_accepted | 新 GP accepted_seq/valid、接收计数 | 内核整条入队，不保证 planner 可执行 |
| point_done | 新 GP done_seq/valid、执行计数 | 精确 duration 和全部脉冲安全完成 |
| session_done / cancelled / stopped | 新 GP 分立状态/计数/原因 | END 正常完成、会话撤销、pulse-safe 排空分别报告 |

普通命令 ACK.accepted 表示合法动作已派发；ACK.completed 对 OPEN/ENABLE/START/RESUME/REBASE 表示相应门接受，对 PAUSE 表示已到边界，对 DISABLE 表示安全排空和失能延迟结束。等待期间仍能用独立 STOP；STOP 终止待完成动作并返回取消应答，不把它伪报成功。快照采用独立请求/保持寄存器，不被等待 PAUSE 的 mailbox 阻塞。

动态快照一次捕获四轴实际位置、position_valid、pulse_total、STEP/DIR/EN、session/generation、running/paused/busy、accepted/active/done 的 sequence 与各自 valid、水位、错误、packet/取消/停止状态及原 GP 同源 1MHz tick。快照 ID/valid 最后发布，全部 LO/HI 保持至下一次快照。边沿与快照同拍采样上升沿前已登记状态，所有字段同一时刻；禁止混合前后拍位置/脉冲计数。

## D4：取消、DMA reset 与显式恢复

common p2f_rst0_n 仅启动/受控整域重建；它可以立即清位置/invalid、重建 GP 时间 epoch。运行中 DMA reset **不得接运动 rst_n 或时间戳 reset**。

STOP、运动故障、欠流、当前会话协议错误、MM2S primary reset/error 都立即使运动入口不可提交、取消旧会话；清 raw FIFO、planner/准备 FIFO、预测、正在持有的完整记录及半包、PACKET_ARM。内核按既有 H/L/DIR hold 排空，保留实际位置和时间。即使 STREAM valid 或边界 launch 同拍也不得发新 STEP。同步错误检测在哪拍成立，就在哪拍优先抑制边沿。

使用 PL link generation 和 PS 软件 generation 分别隔离数据/回调；generation 不能冒充 DDR 静止证明。接收状态 `CLOSED → RECOVERABLE → OPEN` 仅在显式握手推进，上电 CLOSED。STOP 后不以 FIFO 空、reset 输出变高或 DMA reset bit 自清自动恢复。

恢复顺序：

1. GP STOP/取消，软件阻断新 ARM/提交；等待四轴 stop_complete。
2. BSP terminate_sync；按实际 DMA controller reset 作用范围停止相关硬件方向，确认回调/tasklet/描述符和在途 DDR 都静止。失败时 quarantine buffer，不释放或重用。
3. GP 观察 link_closed/partial_empty/queues_empty/reset_released；primary reset release 同步两拍。PL 只证明自身状态，不证明硬 PS 的 DDR 静止。
4. PS 写恢复声明（新软件 generation、quiescent 确认），GP LINK_RECOVER 仅在上述门满足时应答并推进 link generation；清错仍须源解除。失败不开放入口。
5. 从保留实际位置快照重新规划，OPEN 全新非零 session，ARM 新 packet；预缓存/显式 START。CLEAR_FAULT/LINK_RECOVER 均不自动 OPEN/ENABLE/START。

完整合法旧 session 记录被丢弃并 stale 计数，不影响新会话；当前 session sequence 重复/缺号/END 后入点取消。破损格式无法可靠归属旧 session，按链路错误关闭入口，不能根据未校验 session header 忽略 CRC 错误。session 全历史唯一由 PS 在 epoch 内保证，PL 至少拒绝当前/最近关闭 ID。

不把回环“两方向都复位后恢复”接到运动 rst_n。本版保留当前真实双向 DMA IP 实例，S2MM 没有生产流；若真实 controller reset 同时复位两方向，S2MM 必须由 BSP 同步静止。这是 DMA 资源共享事实，不是运动/遥测必须互相 ready。任一 primary reset 若反映共享 controller reset，也关闭运动入口，但只触发安全取消，不清位置/时间。

## D5：容量、预缓存与适用性能范围

产品所需最短 duration `Tmin` 和最坏成功补给间隔 `Jmax` 尚无证据。板测提交 8.010..16.770μs、完成 17.160..104.970μs；199.756MB/s 是 payload/累计完成时间，不包含复位/等待/打印，不能作为连续总线保证。取消恢复期间运动已停止，不将无限恢复时间纳入连续补给承诺。

预算至少满足 `start_points >= ceil((Jmax + margin)/Tmin) + planning_margin_points`，并检查启动后剩余 duration 时间水位。planner 非零间隔 73 拍=0.73μs；零点 8 拍；单点在空闲条件至少提前 74 拍才能边界提交，队列/解包/CRC 背压额外算入。持续点率还须小于 planner 和实际成功提交率的下界，容量不能补救持续生产速率不足。

推荐首个**验证配置**：raw FIFO=64、prepared FIFO=8、START_MIN_POINTS=32；另外 planner 在途 1、解包暂存完整记录 1。`buffered_points` 沿用内核含 raw/planner/prepared，不计尚未被内核接受的解包记录，也不计执行点。raw/plan 元组共 `64*421+8*1197=36520bit` 数据，另加控制、planner/executor/GP/DMA；这不是最后资源报告。

验证补给 envelope：每点至少 100μs，成功补给间隔不超过 2ms，另留 1ms 裕量、2 点规划裕量；`ceil(3ms/100μs)+2=32`。批量 16..32 对应 1152..2304B、数据率 0.72MB/s（10k点/s），允许用 self-checking bench 验证该条件，不声称 Linux 已满足 2ms 最坏界。64+8 的原始/准备资源不是冻结产品容量；最终实际 PS+GP+HP+运动 TD 资源/时序不通过时先报告，不静默降容量。

内核的 1μs 点、74/73 拍规划提前量边界仍用小容量定向测试保留。若产品也要求 1μs：3ms 缓存覆盖约需 3002 点，数据率 72MB/s；32 条一批每 32μs 补给，仅已观测提交/完成数值无法保证。需要明确 Jmax、批大小、缓冲和软件实现，不能以本验证 envelope 代替产品目标。

请确认本次先采用上述验证配置且产品容量保持参数化，或给出产品 Tmin/Jmax/margin/最长允许缓存轨迹时间，以便本次按产品边界定容。配置有效默认 0；这些 duration/缓存数字不批准任何实体驱动脉宽或最高 STEP 频率。

## D6：首版 S2MM 与隔离顶层

推荐首版无 S2MM 运动回包，动态状态/执行结果全部从新 GP profile 获取；真实 DMA 的 S2MM stream 固定无 valid，不投 RX，不要求每点等长回环。GP 明确 advertise telemetry unsupported。原回环顶层和测试保留为独立 profile，不能将回环 BSP client 原样用于运动。

未来 S2MM 用于异步事件/快照/RS485 遥测，独立 FIFO、buffer 所有权和 generation；遥测满/未投 RX 不背压 STEP 或 STOP。controller 级 reset 可能共享，必须协调资源静止；未来需要独立 controller 才能承诺遥测 reset 完全不取消运动。本版不冻结 128B 遥测格式、drop policy 或临界日志容量。

整合参考顶层保留实际 PS+GP0+HP0，100MHz/H16、真实 PS property Tcl 按实际层级加载。运动输出只接隔离内部观测/检查，不绑定电机引脚；另有显式仿真参数的测试顶层。最终默认 config_valid=0，综合验证夹具允许明确非零参数并报告其用途，不能靠把运动常量折叠为零获得时序通过。

## 确认后的实现与交接门槛

按顺序实现：schema 新 profile/生成及 codec → MM2S packet/记录适配器 → GP 运动控制/快照 → 真实 DMA/转换器与 continuous_motion 整合 → 独立自检/集成/既有回归 → TD 实际 PS 整合顶层 10ns 综合与布局布线。

测试必须覆盖合法多点/END/暂停、KEEP/TLAST/长度/CRC/版本/保留位异常、满 FIFO 背压、各个流拍半包取消、旧 session/generation、73/74 拍规划截止、欠流、STOP/fault 与 STEP/launch 同拍、每个执行/规划/等待阶段取消、DMA-only reset 后显式恢复、原 GP ABI 与动态快照原子性。引脚转变独立检查位置/数量/方向/对应槽同步、H/L/DIR/EN 与安全排空；不把内部 planner 输出当期望。真实厂商受保护库用 Questa，不用 stub。受影响既有 Golden/运动/GP/接口/独立 DMA 回归均运行。

TD 必须核实 GEN_PL_GP0S/GEN_PL_HP0 和运动 100MHz、真实 PS 捕获/复位接线、无新增例外；保留所有失败/警告/remaining checker 诊断。报告 LUT/FF/slice/ERAM/DSP、setup/hold/coverage、PS 源与属性/IP/hash。参考 speed2 不确认实物等级。

仅全部授权工作和证据完成后提交 Git，交付 MOTION_HANDOFF.md 与固定 source commit/hash、真实 IP hash、已冻结契约、资源/接线/控制/恢复/复现/BSP 要求及未验证项。本确认稿完成不代表 PL 任务完成。
