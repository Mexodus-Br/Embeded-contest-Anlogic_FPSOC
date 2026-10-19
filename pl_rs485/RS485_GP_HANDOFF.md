# RS485 GP bridge 独立交接

2026-10-18补充：下文保留旧R5S1独立交接状态。新增R5S2仅在interlock_*完整链启用，
其空闲配置门、真实RUN、提交旁路与联锁资格见[SAF2契约](../pl_safety/INTERLOCK_CONTRACT.md)
和[合并交接](../pl_safety/INTERLOCK_HANDOFF.md)；旧R5S1行为/偏移不变。

本交付尚未系统集成或实板验收。BSP、运动/DMA顶层、Golden、GPIO和启动镜像没有修改；没有下载板卡。用户于2026-10-14接受GP_PROFILE_PROPOSAL.md三组契约。完成本交接后停止，系统接入由BSP统一安排。

源码身份以本交接提交及 `evidence/identity_gp.json` 为准；清单固定源文件、唯一规范、工具、夹具和证据SHA256。采集基线2792c66；原协议schema.json/rate_design.json、transaction/UART/FIFO/divider/master字节不变。多速率模块仅增加只读观测端口，freeze_gp.py逆向去除该增量后逐字比较原调度模块，证明调度/退避逻辑未重写。历史MULTIRATE_HANDOFF.md仍是原采集器交接，本文件描述新增桥。

## 已确认profile与互连入口

`pl_interface/schema.json:rs485_gp_profiles.gp_rs485_v1` 是寄存器、位域和桥错误码唯一来源；Verilog/C定义由全局generate.py及本地tools/generate_gp.py生成，本地头使用RG_前缀。采集器配置拒绝码引用原rate_design.json，线上协议及记录仍引用pl_rs485/schema.json。不要运行一次性authoring迁移define_gp.py来维护布局；后续只编辑规范再生成。旧profile JSON逐项相等，由freeze检查。

- 候选0x80700000/4KiB、A33/D32，小端D32访问；VERSION1/PROFILE0x31533552/CAPS0x1f/FEATURES0x1f（配置、完整捕获、原子统计、IRQ、revision旁带）。无S2MM、DDR、任意串口命令或运动功能。
- 高有效level输出irq，后续接f2p_irq[4]，候选SPI86/INTID118、DTS `<0 86 4>`。原0x80400000/0x80500000/0x80600000和SPI82..85保留。
- `evidence/GP_RESOURCE_AUDIT.json`记录当前BSP展开DT来源/哈希及数字CPU窗口审核，候选无冲突；未证明最终HPF decode、child-bus转换或实际GIC映射。BSP部署前必须重审完整最终地址和IRQ。
- `rtl/rs485_gp_bridge.v`是独立AXI-Lite从机入口，同源100MHz clk/rst_n/time_us；收发TX/RX/DE，irq输出。复用现有PS全AXI→Lite转换器。现有axi_lite_three_way没有第四端口，BSP需扩展现有路由并保持独立读写应答所有权；本批没有改它或运动顶层。
- 保持完整33bit地址到端点，不能截为低12bit。窗口外DECERR；未对齐、未知偏移、非法方向/保留位/strobe为SLVERR。shadow/RUN/IRQ_MASK支持byte strobes；WO/W1C全word；WSTRB=0无动作OKAY（仍要求合法地址/方向）。R/B背压保持，AW/W独立到达，每方向一笔在途，写配对拍产生一次副作用，不等BREADY。

完整表见generated/gp_registers.md，字段掩码见generated/gp_defs.h/vh。LOCAL_RESET不作为驱动器复位命令。

## 模块接口和参数

bridge参数透传原100MHz/115200/8N1、E0/E1/E2、最多10节点、FIFO8、原超时/重试/DE换向/错误隔离/预算/退避；均见generated/parameters.vh、rate_parameters.vh及原契约。GP仅配置五个period_us/mask及RUN，不修改地址列表、串口格式或编译时换向参数。默认10ms兼容guard；TD --fast和真实端到端仿真只覆盖编译覆盖NORMAL/POLL=1ms的候选，不能当作实板授权。

`rs485_gp_regs`是可独立验证端点，连接采集器cfg_valid/ready/applied/rejected、当前配置/状态、完整FIFO和只读观测；`collector_rst_n`仅复位采集器实例。`rs485_multirate`保留原接口，追加observe_push/data、observe_tasks[7999:0]和observe_nodes[1279:0]：50任务每项160bit（低到高scheduled/sent/valid/missed/max_lateness），10节点每项128bit（flags/cooldown_lo/cooldown_hi/backoffs），未配置项零。flags低8bit失败，bit8离线。此并行视图不反向驱动调度。原debug选择口保留。

## 配置流程与版本关联

识别profile/features → RUN=0或按需求保持采集 → 写五shadow周期和mask → 写非零递增TXN_ID → CFG_SUBMIT=1。合法B=OKAY表示桥接受且捕获全部参数，CFG_STATE=ACCEPTED|PENDING；桥持续cfg_valid直到ready，之后等待采集器终态。APPLIED/REJECTED、CFG_TXN、原因、revision/apply_sequence、generation及通知时间公布结果。必须检查txn和generation；不能把SUBMIT返回当应用完成。

最近同ID同完整payload幂等，pending/终态不重发；同ID不同payload、倒退/0、不同事务忙时拒绝；busy期间可写shadow但不改变捕获payload。异步RANGE/LOAD/REVISION拒绝保留旧配置；不降频。mask=0或周期0禁用；非零周期沿用1000..2147483647us与750000ppm预算，masked-off非零周期也需在范围内。ID/revision耗尽不回绕。单writer串行化结果读取及提交。

上电/local reset后RUN=0，采集器验证既有兼容默认配置；自动结果txn_id=0，默认成功revision1。RUN停止新轮询，在途请求/重试/隔离有界完成。

CFG_TIME是桥在观察cfg_applied/rejected时锁存的系统时间，即**结果通知采样时刻**；采集器revision/apply_sequence在前一个100MHz边沿更新，若跨1MHz计数边界，时间标记可能比源应用沿大1us。精确历史记录关联使用不可变旁带revision，不依赖该通知时间作切分。

每条实际入队记录同时保存该拍cfg_revision到等深旁带FIFO，完整source record不改；满/同拍pop的接纳规则与源FIFO完全相同。旧revision记录可以留在FIFO，当前配置不能覆盖其标签。捕获同时冻结generation/revision；PS保存每个(generation,revision)已应用配置、apply_sequence与通知time，默认revision1用已识别编译profile补齐。源sequence自然32bit回绕不会改变旁带关联；模块generation不是新系统时间epoch。

## 捕获、读取与消费

CAPTURE=1锁定一条完整队首副本，未pop；重复CAPTURE保持当前非零capture_id。空FIFO不分配ID并返回SLVERR；先读FIFO_LEVEL可避免非法MMIO。CAPTURE_STATUS bit0 valid，bit15:8为成功R握手交付的read_bitmap。字0=record[31:0]，共8个D32字；可乱序/重复读，无消费副作用。

读取capture_id/generation/revision和8字 → 检查generation未变/捕获仍有效 → 全8字交付后CONSUME_ID=capture_id。只pop一次，最近已消费ID重放无动作；其他旧ID/部分读确认拒绝。ABANDON_ID只释放副本，不pop，重新捕获同一队首会得到新ID。capture_id水位跨local reset保留，不回绕。放弃与读取由软件锁串行化。

VERSION/status/attempt/sequence/request_us/event_us/payload保持原语义。status=VALID才有数据；query30 carry signed32+value unsigned16，33 signed32接收脉冲，39 signed16误差，3A/3E原始枚举。错误记录不是有效零反馈，33不是编码器反馈；未知枚举原样保留。原协议无线上事务号，超隔离窗口同地址迟到帧的歧义仍存在；GP标签不能修复线上无法辨别的关联。

FIFO满丢弃整条新记录，dropped饱和累计，满且同拍消费可入队；不覆盖捕获或未消费记录、不背压UART/运动。捕获占用FIFO槽。详见GP_SERVICE_BUDGET.md；360/s目标、1000/s保守服务包络下，FIFO8建议快采服务间隔<=4ms并每批排空，Linux实际MMIO/调度延迟需实测，不能只按平均采样率承诺无丢失。

## 原子统计、IRQ与复位

写递增SNAP_REQ_ID、SNAP_SUBMIT=1，同一posedge锁存所有边沿前已登记值，0x200开始480word固定快照，SNAP_STATUS.valid及独立SNAP_ID标识。同最近ID重放不重采；新ID替换快照。64bit time/cooldown、当前配置/结果/全局计数、节点及任务来自同一拍。reserved/未配置项零；当前配置普通跨字读不原子，请用快照。accepted计有效尝试，即使丢弃仍计；stat_valid在逻辑事务隔离完成时更新，比accepted晚；原missed不含离线取消周期。统计饱和语义不改。

IRQ_PENDING & IRQ_MASK产生level；mask复位0、不清pending，W1C同拍set优先。DATA为FIFO非空/有捕获持续源；CFG_RESULT、COMM_ERROR、PROTECT_OBSERVED（校验有效3E=1）、FIFO_DROP、BUS_DIAGNOSTIC（BUS_BUSY）、RESET_DONE独立。诊断可合并多次事件，结合原子统计/记录判断次数。配置拒绝与通信失败分开，不自动停机。

DATA handler先保留其他mask并屏蔽DATA → 批量捕获/持久化/消费至空 → 确认源已解除 → W1C/readback → 恢复DATA mask。非空时不能反复W1C期望降低level。新事件与清除同拍仍pending。长快照/日志/NPU处理不能饿死FIFO服务。

LOCAL_RESET全字写1只在RUN=0、busy=0、无桥配置pending/cfg_valid、collector ready且无结果发布竞争时接受。清采集FIFO/统计/旁带、捕获、快照和配置结果，generation递增、RUN=0；采集revision/sequence重建，桥txn/capture/snapshot单调水位保留。旧未完成ID无效，已消费缓存清除；generation耗尽拒绝。保留IRQ_MASK及桥shadow参数/ID寄存器（水位仍按上述规则），旧pending替换RESET_DONE；之后默认配置验证产生新CFG_RESULT。

AXI端点不被local reset复位：已形成且未交付的R/B仍保持，旧read_bitmap不会污染新捕获；PS reset后以generation丢弃旧操作。系统64bit/1MHz time_us和运动完全不复位。rst_n仅沿用系统启动/整域复位会话；不支持未经reset fence设计的运行中GP warm reset/透明PL重配置。整域复位后PS按现有epoch契约重建会话，没有持久硬件epoch承诺。

## C接口和访问要求

software/rs485_gp.h/c和example.c可独立C11编译；callbacks接受寄存器offset，BSP提供有序小端D32读写/错误传播和单writer锁。无/dev/mem、最终Linux驱动或NPU实现。rs485_decode从8个逻辑D32字还原源字段及大端payload，正确扩展signed值、保留未知status/enum；先检查返回值与data_valid。时间使用uint64，不通过event>=request判断回绕有效性。

rs485_submit只提交，不阻塞等待终态；调用者用有界截止时间检查CFG_TXN/STATE/GENERATION，保存APPLIED配置。capture_read无消费，consume显式确认；发生中途I/O错误可保留/重读/放弃捕获。snapshot读取完整固定块并检查ID/generation。example展示批量解码/消费，BSP在持久化成功后消费；独立软件测试的mock不是AXI替代验证，实际RTL由自检bench验证。

## 验证、时序和复现

最终证据：sim_gp_final（种子20261014）、software_gp_release、sim_gp_legacy_release及sim_gp_multirate_release（种子20261013）。包含AW/W先后/同时、R/B背压、完整地址/非法访问/WSTRB、原子提交/忙/重放/真实范围预算revision拒绝、8字乱序读取/部分读/放弃/重复消费、旧revision、满FIFO交换、原子64位快照、IRQ竞争/持续源/清除、复位跨R/B、ID耗尽；真实100MHz/115200三节点与模拟从机读取11条记录且故意溢出至少2条。压力209次入队、46消费、163丢新；独立STEP与参考逐拍一致。原采集回归保留全部协议异常/退避/漏采/时间回绕验证。失败与修正记录见evidence/GP_FAILURES.md和各r1目录。

TD独立100MHz DR1M90GEG400 speed2、TD2026.1 SP2，scan封装保留完整AXI入口和功能输出；无实板球位、无bitstream。最终默认/快采报告分别evidence/td_gp_final和td_gp_fast_final，summary.json和identity_gp.json固定各阶段setup/hold、资源、夹具/约束/源码。具体最终数值见下方发布附录。

从dev目录运行（证据tag选未使用名称）：

```powershell
python pl_interface/generate.py --check
python pl_rs485/tools/generate_gp.py --check
python pl_rs485/tools/audit_gp_resources.py
python pl_rs485/tests/run_gp.py --tag gp_verify --seed 20261014
python pl_rs485/tests/run_gp_software.py --tag gp_verify
python pl_rs485/tests/run_sim.py --tag gp_legacy_verify --seed 20261013
python pl_rs485/tests/run_multirate.py --tag gp_multirate_verify --seed 20261013
python pl_rs485/build_td.py --gp --tag verify
python pl_rs485/build_td.py --gp --fast --tag verify
python pl_rs485/tools/freeze_gp.py
```

freeze_gp.py核验已交付final目录；新验证tag的日志单独保留，若要替换发布证据须明确更新freeze选择并重新固定身份。本机Icarus可能在沙箱内access violation，使用允许本地工具执行的终端，不自动重试或视为通过。Python3.10/Icarus12.0/GCC C11；生成定义byte检查要求pl_interface文件按其.gitattributes LF保存。

## BSP后续接入清单

1. 最终HPF/DT/GIC资源审核，候选节点reg `<0 0x80700000 0 0x1000>`、irq `<0 86 4>`，明确compatible/version/features、共享100MHz时钟及reset provider。不直接复制未审candidate到启动镜像。
2. 将原三路Lite路由扩展第四独立端点，保留GP probe/DMA/motion完整A33译码和应答所有权；本桥接同一100MHz与共同同步释放复位，time_us直接复用系统统一时间。
3. Linux平台驱动有序MMIO、单writer/事务ID、水位、generation/epoch与解绑/重绑定规则；IRQ批量服务，配置终态/诊断分离。非法MMIO可能external abort，软件白名单访问，错误场景由TB测试。
4. 服务端保存原始记录、有效性、request/event时间及revision映射、缺采/退避/丢弃统计；按实际异步采样训练NPU，不将错误补零当实测位置、不把命令脉冲当编码器。不新增自动停机链路。
5. 测量GP消费成本、最坏Linux服务延迟与快照开销，验证容量预算；若4ms服务无法保证，明确允许丢记录或另行批准更深FIFO/独立遥测通路。源满丢新不能反向影响STEP。
6. 后续核对固件/转换模块身份、STP并发查询、实际字节序/校验/枚举、线路回显/迟到边界、DE最后停止位与最早应答；板引脚/电气仍按原协议候选后续验收。快采1ms仅在这些实测通过后部署。

## 最终100MHz发布附录

|profile/阶段|setup WNS ns|hold WNS ns|
|---|---|---|
|10ms兼容/gate|+2.241|+0.000|
|10ms兼容/place|+3.362|+0.000|
|10ms兼容/route|+0.890|+0.025|

10ms兼容含OOC封装资源：7043 lut6, 10593 reg, 9301 slice, 6 eram, 1 dsp；STA coverage=99.03%。

|profile/阶段|setup WNS ns|hold WNS ns|
|---|---|---|
|1ms快采候选/gate|+0.964|+0.000|
|1ms快采候选/place|+3.494|+0.000|
|1ms快采候选/route|+0.444|+0.026|

1ms快采候选含OOC封装资源：7010 lut6, 10640 reg, 9361 slice, 6 eram, 1 dsp；STA coverage=99.05%。

两组均双corner、10ns，无放宽时钟或新增多周期例外，内部setup/hold通过。0无时钟/非法约束/组合环；保留4输入/3输出缺外部delay、8个未绑球位SYN-6021、SYN-5025默认零、物理dummy节点（FIFO ERAM未用输出reset端与指针LSLICE unused ofb）。route.qor及run.log保留路由检查；外部UART/IO、异步复位释放、CDC、电气与真实GP互连时序需后续真实顶层验证。资源不能直接与无GP的宽scan采集器封装相减来声称增量，FIFO映射也受优化上下文影响。
