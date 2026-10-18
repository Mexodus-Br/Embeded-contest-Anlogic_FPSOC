# AXI DMA S2MM-only 调用方式独立对照

2026-10-18，Asia/Taipei。源码基线 `88af6ee`（最新交接：`pl_safety/optimization/timing_20261017/HANDOFF.md`）。生产实现未改。本实验没有上板、访问 COM4/存储、生成启动镜像或执行运动命令。

## 结论

**正式 TD IP Catalog 可以生成与当前有效 S2MM 配置一致的单向实例，而且该生成物仍稳定复现 SYN-5066。** A、B 各两次独立综合均出现同一内部后缀。已排除“必须绕过官方入口才会触发”这一解释；没有找到能消除警告的调用差异，内部根因未确定，也未证明警告无害。不能据此直接认定厂商 RTL 或综合器哪一方有缺陷。

另发现一个可复核的配置依赖问题：只勾选写通道 Allow Unaligned Transfers，首个官方包装层实际传 `AL_INCLUDE_S2MM_DRE=0`；安装的 `Dependency.tcl` 将 S2MM DRE 的值关联到 `INCLUDE_MM2S_DRE_dis`。先在读通道启用时勾选其 DRE 显示开关、再关闭读通道，第二个官方生成物才传 S2MM DRE=1。两组均保留。**这不是 SYN-5066 的已隔离根因**：DRE0、DRE1 都复现警告。

生产建议：保持实现和发布门禁原样，将本附件提交厂商澄清内部两个驱动、断开规则及正式配置流程。可评估今后使用正式生成物管理 IP，但本实验没有得到通过更换调用方式消除警告的依据，不建议改生产参数、关闭 DRE 或改双向架构来规避。没有联系厂商。

## 工具、基线和生成来源

- TD：`D:/Anlogic/TD_Release_2026.1_SP2.200.067`，启动日志实际版本 `6.2.2.200067`；IpTool 输出元数据 `2026.03(193873 2026/03/31)`，AXI_DMA 1.0。
- 器件 DR1M90GEG400，参考 speed2（不表示实物速度等级已核验）。实际 clk=100MHz、SDC=10ns。
- 每次 TD 综合显式 `set_param flow thread 16`，开头/结尾 `get_num_thread` 均读回16。没有使用无效的 `threads` 参数。
- A2：当前 `telemetry_dma_lite_top.v`、guard、原厂 DMA/转换器，使用历史独立组件的相同扫描夹具；只纳入实际依赖。A_repeat 再次从当前源码构造。它是**本轮独立组件复现**，不是声称取得了完整工程的最小复现。
- B2/B_repeat：真实 GUI 输出 `build/al_ip/AXI_DMA_1/AXI_DMA_1.v` 及其 `RTL/axi_dma_AXI_DMA_1.v`。实验只编写外围适配，未手写或改动官方包装层/受保护模型。
- `build/al_ip/AXI_DMA_0/` 是首轮 DRE0 输出，仅作补充对照，不能充作 DRE1 的 B 组。
- 工厂 IP 与生成后保护文件的密文不同，公共模块名也不同；本实验没有解密、手工改写或假定二者字节等价。分别记录关键源码哈希。

正式 GUI 步骤（在实验目录内建立空 TD 工程，DR1M90GEG400-2）：

1. Tools → IP Catalog → 搜索 DMA → 双击 AXI DMA；Export Path 置于本实验 `build/al_ip`，Component Name 分别 `AXI_DMA_0`、`AXI_DMA_1`。
2. ASYNC/SG/Micro 维持关闭；地址32、BTT16；写通道开启，memory64、stream64、burst16，勾选写通道 Allow Unaligned Transfers。
3. `_0`：直接关闭读通道。`_1`：关闭读通道前，先勾选读通道 Allow Unaligned Transfers，再关闭读通道。没有生成或综合双向 DMA 对照。
4. OK → Behavior → Generate。界面显示 “Generation of output products completed successfully”。
5. 核对包装层 S2MM DRE 分别0/1，不能以复选框或 `.m_params` 的省略行数值替代最终传参。DRE1 的厂商 GUI 操作记录在 `evidence/official_DRE1_gui_steps.log`。

同步模式下四个频率编辑框禁用，GUI 默认显示50/250/200/100MHz；最终没有传相应底层参数。实验中所有**存在的**时钟端口实际接100MHz，未把禁用字段当实际时钟。该区别见下表和完整 CSV。

独立 IpTool 启动探测未成功；手工准备配置的 xmlipgen 探测缺 `.m_params`；复制真实 GUI 配置的 xmlipgen 命令行重放又报 `incorrect random string size` / `can not match component file in user xml`。因此命令行重放尚未打通，不能把 `OFFICIAL_REPLAY_COMPLETE` 打印标志当成功。**正式 GUI 路径已成功**，上述失败不否定它。失败输入、脚本和原始日志均保留。

## 实际参数、端口与依赖差异

完整32参数：`evidence/parameters.csv`（A显式值、B传入/省略、底层默认、B最终有效值逐项列出）。官方 B 传17项，省略15项。关键项：

| 项目 | A直接实例化 | 官方 B 实际生成结果 | 底层有效结果 |
|---|---|---|---|
| 有效 S2MM | Simple/SG0/Micro0/ASYNC0，addr32，memory/stream64，burst16，DRE1，SF1，BTT16 | 同A，显式传入 | 同A |
| 关闭 MM2S 的 stream width | 显式64 | 省略 | 默认32 |
| 关闭 MM2S 的 burst | 显式16 | 省略 | 默认32 |
| 关闭 MM2S 的 DRE/SF | 显式1/1 | 省略（GUI计算MM2S DRE为0也未传入） | 默认1/1，不能认定DRE应为0 |
| MM2S addr/memory width | 显式32/64 | 省略 | 默认32/64 |
| SG addr/data，控制/状态流宽、STSAPP | 显式32/32、32/32、0 | 省略 | 默认相同 |
| 频率元数据 Lite/MM2S/S2MM/SG | 显式100/100/100/100MHz | 全省略 | 默认50/250/200/100MHz；ASYNC0，实际端口接100MHz |
| 端口 | 底层115个全部连接 | 包装层仅46个公开端口 | 底层69个端口省略 |

`Component.xml` 的 `isPresent` 是**官方文件描述**；上述省略结论依据**真实 GUI 输出**；“不能由这些差异解释本轮警告”依据**受控实验**。没有将描述直接称作 GUI 结果。

完整115端口清单：`evidence/ports.csv`。A将关闭 MM2S 的读响应连到原协议转换器，MM2S stream ready=0；SG响应输入置0，control stream ready=1，status stream输入置0，四个clock都接100MHz，axi_resetn 接同一同步释放复位。B省略MM2S/SG/control/status流端口及未使用clock；相关底层输入不连接，未在包装层偷偷补默认常量。S2MM有效输入、sideband置0、primary reset输出、IRQ接线一致。

B外围为了保留同一协议转换器，将不再存在的MM2S读请求地址/长度/属性/valid/rready接0；这是**实验适配器**，不是声称官方有这些连接。C_ports只改变这组端口处理而保留A全部参数。guard、转换器、输出扫描及复位链保持一致。

生成依赖：官方目录含生成包装层、重命名受保护RTL、`axi_dma_func_pkg.vh`、`axi_dma_param_pkg.vh` 和空 `define.v`；包装层没有额外宏。实验外围仍依赖冻结的 `pl_interface/generated/interface_defs.vh`、guard及厂商转换器。A/B综合的精确输入分别见 `build/A2/sources.json`、`build/B2/sources.json`；RTL仿真由 `simulate.py` 使用同组文件并增加现有自检TB。没有改安装内容。

## 受控综合矩阵

所有成功项均为 gate 综合；未为探索候选跑布局布线。资源是整个相同扫描夹具的综合估计，不是整机或最终布线资源。LUT6为TD报告 `#unit lut*`，寄存器为slice reg，PAD reg=0；总容量LUT6 52480、reg104960、ERAM280、DSP240。

| 组 / 本地 build 标签 | 与 A 的改变 | SYN-5066 | LUT6 / reg / ERAM / DSP |
|---|---|---|---|
| A2、A_repeat | 当前直接调用，两次 | 各1条 | 1191 / 2097 / 12 / 0 |
| B2、B_repeat | 官方 DRE1 实例，两次 | 各1条 | 1191 / 2097 / 12 / 0 |
| C_width2 | 仅禁用MM2S stream64→32 | 1条 | 1191 / 2097 / 12 / 0 |
| C_burst | 仅禁用MM2S burst16→32 | 1条 | 1191 / 2097 / 12 / 0 |
| C_mm_dre | 仅禁用MM2S DRE1→0（推断对照，非官方B有效值） | 1条 | 1191 / 2097 / 12 / 0 |
| C_params | A端口保持，仅采用官方17项覆盖/15项省略 | 1条 | 1191 / 2097 / 12 / 0 |
| C_ports | A参数保持，仅采用官方端口省略及读端适配 | 1条 | 1191 / 2097 / 12 / 0 |
| B_dre0 | 首个官方生成物，有效S2MM DRE0 | 1条 | 939 / 1862 / 12 / 0 |

A原文：

```text
SYN-5066 CRITICAL-WARNING: Disconnect the driver 'dut/dma/vyjqtk/rucwti_i1' of the multi-driven net 'dut/dma/vyjqtk/rucwti'
```

B原文：

```text
SYN-5066 CRITICAL-WARNING: Disconnect the driver 'dut/dma/axi_dma_Inst/vyjqtk/rucwti_i1' of the multi-driven net 'dut/dma/axi_dma_Inst/vyjqtk/rucwti'
```

所有成功项还有扫描夹具5个未约束位置端口的SYN-6021；本实验不做bitgen，没有屏蔽它。与A相比B/C_ports多1条HDL-5317（`m_axi_sg_aclk`未连接）、1条HDL-5323（`m_axi_mm2s_aclk`仍未连接），均来自真实官方端口省略。基线其他HDL-5370/5007/5314/5317/5106均保留，不能称无新增警告。完整文本与各组代码计数见 `evidence/results.json`、`evidence/warnings.md`，不以阶段末摘要抹掉早期警告。

没有候选消除警告，因而没有隔离出可切换 SYN-5066 的单项调用差异。C_params是单项实验后的组合核验，不作为根因定位证据。

## 功能验证与证据边界

A/B真实受保护RTL模型均通过原2251项接收检查。随后实验TB增加了超长包错误/实际长度、缺TLAST不完成的明确断言；最终RTL为2254项、综合网表为2241项。两者正常/短包IOC长度、超长状态0x4012、缺TLAST不完成及复位后再次接收的观测一致；每组176个DDR写beat，无HP读。最终记录分别 `build/sim_A_asserted/`、`sim_B_asserted/`、`sim_gate_A_asserted/`、`sim_gate_B_asserted/`。

综合网表采用厂商脚本 `scripts/PRFlow.tcl` 已使用的 `set_param flow ooc_flow on`，保留功能端口，通过 `optimize_gate` 后 `write_verilog` 导出；仍报告同后缀SYN-5066。它是单独的OOC验证构建（`gate_function_A`、`gate_function_B2`），不与扫描矩阵混算资源。使用安装包common/dr1真实原语和 `work.DR1_PHY_GSR`，零延时功能仿真，没有替换受保护逻辑、手工修网或关闭警告。

门级TB只去掉已被优化删除的两个内部桥高位结构探针，以及始终关闭的MM2S监视器层次引用；保留公共AXI几何、地址、字节、TLAST、长度、IRQ/状态及复位恢复检查。少13次检查由两个结构探针在多次写事务触发次数造成。TB源和原始编译/仿真日志保留。

覆盖：正常64/1024/192B接收、周期性AW/W背压和延迟B响应、正常TLAST、1024B请求提前64B尾短包、64B请求发送128B超长、缺TLAST部分包、每例软件reset以及复位后的新包。缺TLAST后的软件复位覆盖部分包取消恢复；**不等于Linux在途terminate/所有DDR写静止资格**。

边界：未做全输入形式等价、布局布线/SDF、所有未对齐DRE传输、任意长背压、完整在途写取消相位扫描或实板验证。没有消警候选需要升级为生产；有限综合后测试通过不证明所有状态等价，也没有确认被断开的两个驱动具体语义。

RTL A/B仿真分别有39/109条警告；综合网表各7071条，包含原语缺省端口未显式连接、端口数/类型诊断（vopt-2685、2718、2958、vsim-3016）。没有屏蔽，原始日志保留；这些诊断和OOC/零延时范围限制门级结果的资格，不能宣称已完成厂商认可的全设计等价签核。厂商仍需给出模型/映射缺省连接的资格说明。

## 复现与附件

以下相对路径均以本实验目录为基准；完整本地路径为 `D:/Works/Embedded_contest/dev/pl_dma/experiments/axi_dma_s2mm_calling_20261018/`。

1. 在同版本安装上按前述GUI步骤生成 `_0`、`_1`，核对 `evidence/AXI_DMA_*/` 的配置、包装层和关键身份。原始大型生成RTL本机保留在 `build/al_ip/`，不入Git。
2. 在仓库根执行 `python pl_dma/experiments/axi_dma_s2mm_calling_20261018/experiment.py A_new`；然后 `matrix.py B_new official1`。所有tag必须新建；不要覆盖旧目录。
3. 用 `matrix.py <new_tag> AL_M_AXIS_MM2S_TDATA_WIDTH=32`、`AL_MM2S_BURST_SIZE=32`、`AL_INCLUDE_MM2S_DRE=0`、`params_official`、`ports_official` 逐项复核。
4. `build_functional.py <new_gate_tag> B_new` 导出OOC功能网表；`simulate.py <new_sim_tag> B_new` 运行RTL，或追加 `--gate <new_gate_tag>` 运行门级。Questa始终串行；本机受限环境启动vlib报WinError623，正常Windows执行环境运行成功。
5. `seal.py` 汇总附件；它只对显式关键交付/直接源码白名单计算哈希，不对日志、数据库、综合网表或整目录计算哈希。

附件：`evidence/matrix.csv`（含失败项）、`parameters.csv`、`ports.csv`、`results.json`、`warnings.md`、`identity.json`、`artifact_index.csv`。`identity.json`固定基线提交、工具、器件和38项明确关键源码/配置身份，不是历史证据整树哈希。失败分类见 `FAILURES.md`。

原始路径：`build/<matrix_tag>/run.log`、`gate.area`、`run.tcl`、`sources.json`；正式生成 `build/al_ip/AXI_DMA_*/`；GUI日志 `build/log/ipgen.log`（厂商同名记录器在第二实例启动后重开，附件保存的是DRE1步骤；DRE0的配置/包装层仍完整）；仿真 `build/<sim_tag>/compile.log`、`simulation.log`；门级构建 `build/gate_function_*/run.log`。日志不哈希。大型数据库、网表、Questa库/波形全部在独立build目录保留，未清理其他目录。

提交只包含本实验必要脚本、文档和小型官方配置附件；`AGENT.md`工作区修改保持未提交，生产RTL/schema/生成器/BSP未改。`diagnostics_closed=false`、生产发布门禁保持。
