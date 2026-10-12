# GP 最小控制契约 — 2026-10-12

同日实施进展：本 profile 的 GP RTL、独立/真实转换器集成自检及参考100MHz OOC时序已通过，见 [GP_VALIDATION.md](GP_VALIDATION.md)、[GP_INTEGRATION.md](GP_INTEGRATION.md)。下面保留冻结时的范围和部署门槛；唯一schema的implementation-pending指平台整体尚未完成，不表示已有RTL/仿真证据不存在。PS/HPF/DTS/FSBL及板级仍未验收。

状态：**USER_CONFIRMED_IMPLEMENTATION_PENDING / NOT_DEPLOYABLE**。用户于 2026-10-12 对集中五项提问答复“接受”，确认本文最小 profile。文件名保留供原评审链接继续使用。资源选择与逻辑契约已确认；实际 HPF/DTS、IP、时序和板级证据尚未完成。唯一机器规范为 `pl_interface/schema.json` 的 `gp_control_profiles.gp_control_probe_v1`；所有常量由该源生成，本文是语义说明，不是另一套定义来源。

## 1. 首轮范围与确认边界

本 profile 命名 `gp_control_probe_v1`：验证 GP MMIO、无动作命令应答、原子状态快照、level IRQ、屏蔽/清除/重新触发。只支持 NOP 与 SNAPSHOT；运动命令、配置提交、DMA、HOME、REBASE 均不接入。板级顶层不导出电机 STEP/DIR/EN 引脚。四轴快照接口保留，但首轮板级源为空闲、位置 0/invalid、pulse_total 0，不能把该试验作为运动验证。

已有确认：GP/Lite 控制方向、JSON 唯一规范与生成 C/Verilog 定义、100MHz PL 基础时钟、1MHz/u64 时间戳、signed64 命令位置。本轮端口/窗口/适配器/IRQ/复位/寄存器子集与命令语义已获确认，实际平台能力与映射仍须核验。其他运动与连续层已确认契约保持。

## 2. 已确认资源、协议和时钟选择

| 项目 | 用户确认方案 | 证据与部署门槛 |
| --- | --- | --- |
| GP 端口 | PS master GP0，AXI3，地址 33bit、数据 32bit、ID 12bit | 厂商 GP0 生成 RTL 有这些宽度；实际新工程生成端口须再次核对 |
| 转换 IP | 当前 TD 的 Anlogic AXI Protocol Converter 1.0，AXI3 → AXI4-Lite，A33/D32/ID12，读写使能，无 USER | 已安装 IP 参数表支持该组合；尚未生成和验证该实例 |
| 控制窗口 | GP0 `0x80400000–0x80400FFF`，4KiB，32bit little endian | 本 profile 的已确认窗口；暂避开既有 `0x80000000–0x803FFFFF` 显示/网络区域，不把避让范围视为永久预留。生成 HPF、完整地址图及所用 DTS 无冲突才可部署 |
| 地址检查 | 转换及窗口 decode 保留完整 33bit，窗口命中后才使用低 12bit offset | 禁止先截成 32bit/12bit 造成别名；不命中返回 DECERR |
| 中断 | `f2p_irq[0]`，PL 电平高有效；约定 GIC INTID 114 / SPI 82（资料推导，部署前实核），DTS `<0 82 4>` | 厂商同一示例 RTL 的 bit0 与 SDK 的 114 配对，114−32=82。这是资料推导，不是新工程/实板验证；Linux 动态 IRQ 号不固定为 114 |
| 时钟 | 板载 H16 100MHz 经合法全局时钟网络，同一时钟驱动 GP0 ACLK、转换器、寄存器、快照源与时间戳 | GP0 ACLK 在厂商 RTL 为外部输入，示例接 p2f_clk0；本 profile 改接共同 100MHz，须验证 PS IP 配置和实际时序。首轮自研 GP↔控制逻辑无异步 CDC |
| 复位 | 整个上述 PL 控制域共同复位，异步置位、至少两级同步释放；初始化完成时进入 NOT_READY 并启动 timestamp | 首轮不提供独立 GP-only reset 或 Linux reset ioctl。复位/重配置前驱动停止访问，AXI 通道须静止；运行中不得单独复位从机留下挂起事务 |

整域 PL 复位/重配置建立新 epoch：timestamp=0、位置=0/invalid、IRQ pending/mask=0、ack/snapshot invalid、LAST_TXN_ID=0。驱动解绑/重绑、普通 IRQ 清除、STOP、清错、DMA 复位不重置时间戳。Linux 在整域复位/重配置后重建设备会话、丢弃缓存样本；首轮不支持透明热重配置，也不宣称有硬件持久 epoch 编号。需要独立 GP warm reset 或异步 GP 时钟时，另行设计 reset fence、稳定 mailbox 和 epoch 识别，不能沿用本方案直接连接。

## 3. 最小寄存器子集

表内为**本 profile 已确认的相对偏移**；已有草案寄存器不挪位，新项占目前空位。未列寄存器在本 profile 不实现，不能据全局草案自动访问。

| offset | 名称 | 语义/首轮值 |
| --- | --- | --- |
| 0x000 | VERSION | RO，控制 ABI 1 |
| 0x004 | CAPS | RO，0xF，仅表示四个快照轴槽；不表示电机已可执行 |
| 0x008 | STATE | RO，INIT=0，初始化后 NOT_READY=1 |
| 0x010 | CMD_STATUS | RO，busy bit0 / ack_valid bit1 / accepted bit2 / completed bit3 |
| 0x014 / 0x018 | ACK_ID / ACK_ERROR | RO，最近已发布应答；复位均 0、ack_valid=0 |
| 0x044 | POSITION_VALID | RO，低四位；首轮板级 0 |
| 0x048 / 0x04C | IRQ_PENDING / IRQ_MASK | W1C / RW，bit0 ACK、bit7 TEST；其他位保留 0；复位 0 |
| 0x050 / 0x054 | SNAP_ID / SNAP_VALID | RO，最后成功快照的事务 ID / 有效标记 |
| 0x058 / 0x05C | SNAP_TIME_LO / HI | RO，快照 timestamp，1MHz u64 |
| 0x068 | TICK_HZ | RO，1000000 |
| 0x06C | TEST_RW（新增） | RW，reset=0，支持逐字节 WSTRB；不连接运动控制 |
| 0x070 | FEATURES（新增） | RO，bit0 NOP、bit1 SNAPSHOT、bit2 IRQ_TEST；首轮 0x7；bit3 MOTION/bit4 DMA 为 0，其余 0 |
| 0x074 | TEST_IRQ_LEVEL（新增） | RW，bit0 为持续测试源，reset=0；全 WSTRB；其余保留 0 |
| 0x078 | LAST_TXN_ID（新增） | RO，最近消费的合法新事务 ID；驱动重绑后据此继续编号 |
| 0x080–0x0BC | SNAP_A0…A3_POS/PULSE_LO/HI | 各轴 stride=0x10；每轴 +0/+4 signed64 实际命令位置，+8/+C u64 实际 pulse_total |
| 0x0C0 | SNAP_STATE | RO，同一快照帧状态 |
| 0x0C4 / 0x0C8 | SNAP_SESSION_LO / HI | RO，同一快照帧 session；首轮板级 0 |
| 0x0CC / 0x0D0 | SNAP_ACCEPTED_SEQ / DONE_SEQ | RO，同一快照帧序号；首轮板级 0xFFFFFFFF（无点） |
| 0x0D4 | SNAP_POSITION_VALID | RO，同一快照帧 valid；首轮板级 0 |
| 0x100 / 0x104 / 0x108 | CMD_OPCODE / CMD_ARG / TXN_ID | RW 影子，reset=0；OPCODE/ARG/TXN 均按整 32bit 字节更新 |
| 0x114 | CMD_SUBMIT | WO doorbell，仅全 WSTRB、data=1 有效 |

读无清除副作用。Lite AW/W 分别缓冲，先 AW、先 W、同时均可，一次配对产生一次写副作用；最多一笔未完成写、一笔读，BVALID 与 RVALID 在背压保持，RDATA/RRESP 稳定。RW 影子/TEST_RW/IRQ_MASK 支持 byte strobes，保留位写 1 整笔拒绝；SUBMIT、TEST_IRQ_LEVEL、W1C 要求全 WSTRB。WSTRB=0 无副作用 OKAY。未知/未对齐 offset、RO 写、WO 读、非法保留位/非零非法 strobe 返回 SLVERR；不产生副作用。Linux 只访问白名单，不用非法 MMIO 试探总线错误（可能形成 CPU external abort）。非法访问由 HDL TB 验证。

## 4. 无动作命令、编号与应答

- 单 writer。opcode SNAPSHOT=13（沿用草案），新增 NOP=16；ARG 必须 0，本 profile 无命令 session 字段。首轮不支持的 opcode 返回 BAD_COMMAND，不触发运动。
- 软件先检查 busy=0，写影子后写 SUBMIT；从机配对 SUBMIT 时原子捕获全部 payload。总线 OKAY 只表示提交；软件以 ack_valid && ACK_ID==TXN_ID && completed 判定结果。NOP/SNAPSHOT 成功 accepted=1/completed=1；错误 accepted=0/completed=1。此 completed 只表示控制操作完成，绝不是电机到位或轨迹完成。
- TXN_ID 使用非零 u32，从 1 开始严格递增、不回绕，允许跳号。合法新 ID 被消费，即使 opcode/ARG 导致 BAD_COMMAND，也更新 LAST_TXN_ID 并缓存错误应答。到 0xFFFFFFFF 后停止提交；通过受控整域初始化建立新 epoch，不提供在线 rollover 命令。
- 最近同 ID、同 payload 重复提交返回缓存结果，SNAPSHOT 不重新采样，可重新置 ACK pending。同 ID 不同 payload、倒退 ID 或 ID=0 的 SUBMIT 返回 SLVERR，保留 LAST_TXN_ID、缓存应答与快照。BUSY 时 SUBMIT 也返回 SLVERR，不覆盖在途 payload/应答；busy 期间写影子不改变已捕获事务。
- 与整域复位同拍时复位优先，取消在途事务，不发布旧 ack/snapshot。新事务提交时清旧 ack_valid、置 busy；结果发布时清 busy、置 ack_valid，并产生一次 ACK 事件。软件在提交新 ID 前读走上一应答。
- 本 profile 只冻结 OK=0、BAD_COMMAND=0x0601 两个 ACK_ERROR 值，沿用 JSON 草案现值；不冻结全局其他错误码。

上述非法编号/忙时的 SLVERR、LAST_TXN_ID 和 NOP 是本轮确认项，较旧 REGISTERS 草案更具体；不应把旧草案的 DUP_COMMAND ACK 行为同时套用到本 profile。首次驱动实现应按此 profile；此前没有冻结/部署的 GP ABI 可迁移。

## 5. 原子快照

SNAPSHOT 在共同 100MHz 域的一拍，采样该上升沿**之前**已登记的四轴实际位置、pulse_total、timestamp、valid、state、session 和两个 sequence，整帧一起发布。若 STEP 计数恰在该拍更新，快照含更新前值；后一次快照才可见新计数。该定义是本轮已确认采样时刻，不改变运动 STEP 计数优先级。

SNAP_ID=TXN_ID、SNAP_VALID=1 与整帧有效发布在同一拍，成功 ack 不早于该拍。保持到下一次成功 SNAPSHOT；NOP、普通读、IRQ 清除、失败命令与重复 ID 不改帧。复位清 invalid，数据清 0（序号无点值为 0xFFFFFFFF）。软件串行请求快照，读 SNAP_ID/VALID → 整帧 LO/HI → 再读 ID/VALID；不一致或 invalid 就丢弃。未完成 snapshot 的旧有效帧仍可读，但不能当作新 ID 的应答。快照读到的是实际 STEP 命令计数，不是规划端点或编码器反馈。

## 6. 电平 IRQ、清除和重新触发

`irq = |(IRQ_PENDING & IRQ_MASK)`。ACK 为离散发布事件；TEST_IRQ_LEVEL[0] 为持续源。pending 的更新为 `(pending & ~w1c) | event_or_active_source`，同拍 set 优先；mask 只决定输出，不影响事件锁存，不清 pending。持续测试源为 1 时清 bit7 后仍保持/重新置位；源为 0 时方可 W1C 清净。

驱动 IRQ handler 读 pending & mask，必要时先屏蔽持续测试位，再处理/解除源、W1C、readback、最后解除屏蔽。清 pending 不清 ACK、不撤销 snapshot、不复位时间戳。IRQ mask 的 RW 更新保留其他使能位；驱动串行化与 ioctl 的 mask/clear 访问。测试需覆盖 masked event 后 unmask、持续源反复清、set/clear 同拍、快速 NOP/SNAPSHOT 及 IRQ disable/re-enable，无 IRQ storm。

## 7. 规范落实与待执行验收

本 profile 的资源与子集语义已加入唯一 `pl_interface/schema.json`，保留全局其他条目 Draft；补四个新寄存器、NOP、IRQ TEST 定义并统一生成 C/Verilog/表格。全局 SNAP_* 序号 reset 草案未改，本 profile 的两个无点序号 reset=0xFFFFFFFF 由专属 override 常量生成。PS/PL 共用同一 schema 哈希和 profile；FEATURES 必须逐项检查，不能只检查 VERSION/CAPS 就开放运动接口。后续接入运动命令或独立时钟，先说明影响与迁移方案。

本轮契约确认不等于实现验收。实施时先独立寄存器/命令/快照/IRQ self-checking TB，再 AXI 转换器集成、TD 10ns 时序、HPF/DTS 审核，最后板级 MMIO/IRQ 测试。板级前必须填完 actual GP/IP/时钟/复位/IRQ/地址证据；上述资料推导映射有差异则停止部署并重新评审，不能静默更换。

契约实施后的最低试验：AW/W 顺序与背压、字节写/非法写无副作用、33bit 地址别名拒绝；命令重复/倒退/忙/未知 opcode；四轴 64bit 边界与变化源原子采样；持续 IRQ 清除与 mask/rearm；在每个在途阶段复位、旧应答/旧快照不发布；1MHz 时间及整域复位 epoch。既有运动/接口回归和 Golden Model 保留。首轮板级不写运动影子、不下发 START/ENABLE/REBASE、不接 DMA。

## 8. 资料定位（资料事实，不是用户确认）

- GP0 位宽/ACLK：`docs/Analogic/03_demo/3-2_ex_fpsoc/3_2_02_sdk_adv/01_axi_bram_ctrl/soc_prj/uisrc/01_rtl/system/hdl/system.v`，AR/AWADDR 第 11/39 行，AWID 第 47 行，WDATA 第 75 行，ACLK 第 89/228 行。
- 协议转换器：`D:/Anlogic/TD_Release_2026.1_SP2.200.067/ip/depot/AXI_Protocol_Converter_1.0/Dependency.tcl`，protocol 列表第 5 行、ID/ADDR 宽度第 11/12 行。
- IRQ 配对：`docs/Analogic/03_demo/3-2_ex_fpsoc/3_2_02_sdk_adv/05_TPG_Lwip_UDP/soc_prj/uisrc/01_rtl/system_top.v:301` 与同示例 `soc_sdk/tpg_hdmi_lwip_udp/main.c:21,81`。
- 已有资源：`PHASE0_CONSTRAINTS.md` I01 和 Ubuntu 资源记录；当前 BSP PS-only 生成顶层尚未导出 GP/IRQ，不能把当前可启动镜像当作 GP 已可用。
