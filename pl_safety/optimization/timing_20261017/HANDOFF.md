# PL高扇出与长路径专项交接（2026-10-17启动，2026-10-18完成）

授权起点2f09a56；比较RTL 5ccd875、检查点2befa00及完整predecode_top7。保留项目方AGENT.md工作区修改。本报告是数字功能/资源/STA专项结果，生产PROFILE=0仍禁止启动，不是部署许可。

## 完整实际顶层资源

|资源|基线已用/总量|基线占比/剩余|最终已用/总量|最终占比/剩余|绝对增量|
|---|---:|---:|---:|---:|---:|
|LUT6等效|27866/52480|53.0983%/24614|28185/52480|53.7062%/24295|+319|
|Slice|35605/52480|67.8449%/16875|35919/52480|68.4432%/16561|+314|
|Slice寄存器|36263/104960|34.5494%/68697|36403/104960|34.6827%/68557|+140|
|PAD寄存器|9/工具未报告|N/A/N/A|9/工具未报告|N/A/N/A|+0|
|ERAM|58/280|20.7143%/222|58/280|20.7143%/222|+0|
|DSP|6/240|2.5000%/234|6/240|2.5000%/234|+0|
|IO|17/126|13.4921%/109|17/126|13.4921%/109|+0|
|GCLK|1/32|3.1250%/31|1/32|3.1250%/31|+0|
|SCLK|6/72|8.3333%/66|6/72|8.3333%/66|+0|
|LCLK|0/20|0.0000%/20|0/20|0.0000%/20|+0|
|PLL|0/8|0.0000%/8|0/8|0.0000%/8|+0|
|IOCLK|0/16|0.0000%/16|0/16|0.0000%/16|+0|
|MLCLK|0/8|0.0000%/8|0/8|0.0000%/8|+0|

最终Slice变化+314（+0.5983个百分点），Slice寄存器变化+140，PAD寄存器变化+0。不同层级含子模块，不相加；所有收益/代价使用真实完整顶层。PAD寄存器容量没有在原工具报告单列，不能拿126个IO数量冒充寄存器总量。

源码新增状态位87bit：计数边界21、阶段截止时间/回绕65、CRC校验1。完整顶层gate综合实际净增76个FF（controller+75、receiver+1）；PRE/PULL相同阈值可共享6位，截止时间低5位与原phase_time相同可共享。最终布线总量还包括工具的等价复制与打包变化，以上表实测为准。

## 原约束下时序

|阶段|基线setup/hold ns|最终setup/hold ns|基线/最终覆盖率|
|---|---:|---:|---|
|gate|-1.306/+0.000|-1.439/+0.000|99.99%/99.99%|
|place|+2.332/+0.000|+2.786/+0.000|99.96%/99.96%|
|route|+0.016/+0.020|+1.133/+0.020|99.96%/99.96%|

- 基线gate最差组board_100m -> board_100m：-1.306ns，control/core/fabric/dma_core/motion/controller/count_reg[128].clk (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 }) → control/core/fabric/dma_core/motion/motion/kernel/executor/dir_reg[0].d (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })；11 ( LUT5=4  LUT6=3  ADDER=2  LUT4=1  LUT3=1 )，ADDER2，fanout214，11.236ns (cell 3.053ns (27%), net 8.183ns (73%))。

- 最终gate最差组board_100m -> board_100m：-1.439ns，control/core/fabric/dma_core/reset_release_reg[1].clk (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 }) → control/core/fabric/dma_core/motion/motion/kernel/executor/state_reg[1].d (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })；9 ( LUT6=4  LUT3=2  LUT2=2  LUT5=1 )，ADDER0，fanout16927，11.369ns (cell 2.379ns (20%), net 8.990ns (80%))。

- 基线place最差组board_100m -> board_100m：2.332ns，control/core/fabric/dma_core/motion/motion/timestamp_reg[0]_syn_2.clk (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 }) → a0_step_syn_4.ce (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })；9 ( LUT6=4  ADDER=4  LUT2=1 )，ADDER4，fanout36，7.608ns (cell 1.939ns (25%), net 5.669ns (75%))。

- 最终place最差组board_100m -> board_100m：2.786ns，control/core/fabric/telemetry/transport/ramread0_syn_384.clkb (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 }) → control/core/fabric/telemetry/transport/ready_lateness_max_us_reg[15]_syn_2.cea (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })；8 ( ADDER=4  LUT5=2  LUT4=1  LUT2=1 )，ADDER4，fanout22，7.086ns (cell 3.955ns (55%), net 3.131ns (45%))。

最终100MHz原约束setup严格>1ns：+1.133ns；hold +0.020ns，STNS=0.000、HTNS=0.000。按所有路径组统计的违例端点明细、双corner、最差组和完整路径见comparison_closure_cofactor_route5.json及原始报告，不使用布局估计或额外预算下的中间值作为通过证据。

最差setup路径（按实际slack排序）：
- 1.133ns：ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.slave_hp0_axi_rvalid (rising edge triggered by clock ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_HP0  { rise@0.000000ns  fall@5.000000ns  period=10.000000 }) → a2_dir_syn_6.doq[0] (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })；6 ( LUT6=3  LUT2=2  LUT4=1 )；ADDER（工具计数）0；fanout 36；8.066ns (cell 2.111ns (26%), net 5.955ns (74%))。
- 1.149ns：ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.slave_hp0_axi_rresp[1] (rising edge triggered by clock ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_HP0  { rise@0.000000ns  fall@5.000000ns  period=10.000000 }) → a2_dir_syn_6.doq[0] (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })；5 ( LUT6=2  LUT5=1  LUT4=1  LUT2=1 )；ADDER（工具计数）0；fanout 39；8.050ns (cell 2.033ns (25%), net 6.017ns (75%))。
- 1.151ns：ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.slave_hp0_axi_rvalid (rising edge triggered by clock ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_HP0  { rise@0.000000ns  fall@5.000000ns  period=10.000000 }) → a2_dir_syn_6.doq[0] (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })；6 ( LUT6=2  LUT2=2  LUT5=1  LUT4=1 )；ADDER（工具计数）0；fanout 36；8.048ns (cell 1.998ns (24%), net 6.050ns (76%))。
- 1.188ns：ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.slave_hp0_axi_rvalid (rising edge triggered by clock ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_HP0  { rise@0.000000ns  fall@5.000000ns  period=10.000000 }) → a2_dir_syn_6.doq[0] (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })；6 ( LUT6=2  LUT2=2  LUT5=1  LUT4=1 )；ADDER（工具计数）0；fanout 39；8.011ns (cell 2.192ns (27%), net 5.819ns (73%))。
- 1.196ns：ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.slave_hp0_axi_rresp[0] (rising edge triggered by clock ps/DR1_PHY_PROCESSOR_SYSTEM_Inst.GEN_PL_HP0  { rise@0.000000ns  fall@5.000000ns  period=10.000000 }) → a2_dir_syn_6.doq[0] (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })；5 ( LUT6=2  LUT5=1  LUT4=1  LUT2=1 )；ADDER（工具计数）0；fanout 39；8.003ns (cell 2.072ns (25%), net 5.931ns (75%))。

三个DIR的CE和PAD数据输入均纳入pulse_event定点查询，当前最差1.841ns：control/core/fabric/dma_core/motion/motion/kernel/executor/pulse_event_reg[1]_syn_2.clk (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 }) → a1_dir_syn_6.ce (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })，7 ( LUT6=3  LUT5=3  LUT4=1 )，fanout59，7.892ns (cell 1.602ns (20%), net 6.290ns (80%))。完整首条数据源net为controller/pulse_event[1]，不是凭打包后cell名称判断。原观测加法不再串到DIR检测链；HP0响应到DIR仍是剩余全局最差路径，不能称整条物理长路径或所有高扇出已消失。

原最差pulse_event→65bit观测加法→HOME资格→DIR为+0.016ns、10级、2ADDER、fanout11、data9.757ns（cell2.372/net7.385）。第一次候选将该观测链移走，但新最差timestamp→阶段减法/比较→执行器CE仅+0.326ns，仍未达目标；失败候选完整保留。最终pulse_to_dir.timing定点查询与所有路径组报告共同证明改善，不能从最差列表未出现推断某网扇出为0。

## 高扇出与拥塞

下表穷举所有负载>=64的实际物理网，每个网逐项核对flat pin、driver和完整load pin条数。类别依据实际负载引脚及CLOCK属性；混合负载逐项保留，普通逻辑输入可能包含控制译码，不把DataNet表当全网结论。

|物理类别|基线数量/最大负载|最终数量/最大负载|基线区间64-127/128-255/256-511/512-1023/>=1024|最终同区间|
|---|---:|---:|---|---|
|普通逻辑输入|69/168|79/189|65/4/0/0/0|75/4/0/0/0|
|CE|188/531|181/645|160/17/10/1/0|150/25/5/1/0|
|直接复位引脚分发|92/618|96/421|60/26/4/2/0|57/31/8/0/0|
|合法时钟分发|6/6035|6/5969|0/0/0/0/6|0/0/0/0/6|
|常量|1/860|1/860|0/0/0/1/0|0/0/0/1/0|

此次并非所有类别最大扇出下降：普通Data最大168→189、CE最大531→645上升；reset最大618→421下降，clock6035→5969为合法分发重平衡。CE645及宽快照/GP读选择仍是后续热点，不宣称全部控制网已治理完毕。

clock保留原GCLK/SCLK分发，不当作数据网强行复制。未增加复位级数或改变停止/复位边沿；仍高负载的CE/复位如实保留在完整清单中，不宣称全部高扇出已消除。旧3392 CE/1523 reset不是本轮当前基线，当前实际基线分别531/618。

同阶段拥塞诊断：
- 基线：['RUN-1001 :   Local congestion issue exists, and most congested 1% tile average routing util is 90.385135']；最终wire length=['12476080']。
- 最终：['RUN-1001 :   No local congestion issue, and most congested 1% tile average routing util is 85.087838']；最终wire length=['12872576']。

修改涉及的命名控制网族（含等价复制，按最长名称归属避免重复）：

|逻辑族|基线物理网数/最大实际负载|最终物理网数/最大实际负载|
|---|---:|---:|
|pulse_event|3/3|3/8|
|phase_time|64/1|59/1|
|phase_deadline|0/N/A|65/2|
|search_at|0/N/A|4/3|
|search_before|0/N/A|31/3|
|count_full|0/N/A|47/4|
|checked_bad|0/N/A|207/8|
|rx_error|1/1|10/39|
|rx_error_candidate|0/N/A|0/N/A|
|rx_without_dma|0/N/A|0/N/A|
|stop_kernel|1/4|1/8|

名称不存在记N/A，可能因别名/打包，不能据此推断功能被删除或扇出为0；完整all-net CSV、物理load pin清单和所有路径组报告为准。这一表不能与模块资源数相加。

check_timing各诊断项变化：{'checking no clock': 0, 'checking clock definition': 0, 'checking dummy node': 0, 'checking invalid constraint': 0, 'checking pll/clock buffer clock constraints': 0, 'checking combinational loops': 0, 'checking soft fifo timing exception constraints': 0, 'checking no path constraints': 0, 'checking shadowed/ignored timing exception constraints': 0, 'checking no input delay': 0, 'checking no output delay': 0, 'checking partial input delay': 0, 'checking partial output delay': 0, 'checking abnormal input delay': 0}。全部时钟身份与频率与基线逐项相同，实际负载另存比较JSON。

新增诊断代码：['PHY-5010', 'RUN-6001']；已用最终DB逐项核对，结果见final_warnings2/result.json和原始连接报告。PHY-5010为物理优化等价复制/别名节点在QoR阶段无消费者或已移除，残存有效网要求恰好一个driver；未屏蔽原告警。

详细路由迭代与overflow见比较JSON/原始run.log；不同阶段RUDY、top1利用率、最终wire length不能混为同一指标。

## 实现与接口周期

1. 计数边界同步维护当前count的at/before/full表示，同拍pulse_event只走窄资格判断；计数仍64bit饱和，快照travel不变。
2. 在原阶段装载边沿登记deadline=start+limit及carry。nowrap时timeout=(now>=deadline || now<start)，wrap时为AND，精确保持unsigned(now-start)>=limit，包括时间回绕/反向跳变。消除检测拍串行减法后比较，不延后超时失败。
3. 在原最后CRC字节计算边沿登记完整校验结果，随原state进入CHECK。error及禁止STEP的检测拍、point_valid、ARM/取消/半包/包尾与背压保持。
4. motion_service对DMA错误作等价Shannon展开：rx_error || (D&&B)改为D ? B : rx_without_dma，原非DMA abort逐项保留。receiver只增加内部error_candidate组合端口，不进入外部ABI；DMA检测边沿、idle STOP完成及排空语义不变，没有新增寄存器。

外部可观察周期变化：0。急停/限位/STOP、同拍候选溢出整组禁止、H/L/DIR/EN排空、HOME准确步数/参考/最终位置与唯一执行器所有权保持。私有冗余状态提前计算/同步维护，不把安全动作延后一拍。72B MOT2、32B采集、64B CRC遥测、缓存/FIFO容量和ID/generation/IRQ旧值均未改变。

## 功能/兼容证据

- closure_cofactor_units1：32功能/负面场景；closure_cofactor_phases1：7×24=168停止相位；closure_cofactor_overflow1：signed64同拍整组溢出保护；closure_cofactor_resource1：实际500cycle驱动参数两组，均通过。
- 控制器31个公开输出8个阈值逐拍/组合对照，各33416次，含时间回绕/随机跳变；接收器14个输出10498周期、30计数边界、87损坏场景对照。原始oracle来自冻结Git，边界注入只初始化一致表示，不在运行中修正结果。
- DMA停止展开：65536组独立布尔组合穷举，生产service全部36个输出66799周期对照，原运动场景151597项检查；STOP检测边沿另逐拍相等。
- closure_cofactor_real1：真实受保护GP/DMA/双HP及安全七窗口；closure_cofactor_regress1：18项既有运动/接口/接收器/GP/DMA/Golden回归。原结果文件恢复，Questa串行。
- parser/cache/FIFO/结果/IRQ/C解码/RS485 GP及最终源码真实HP0/HP1并发回归通过，具体source_sha256/命令见证据；没有stub替换原IP。
- 3068个旧schema叶值及旧生成定义保持；生成器check通过。原c9f2e05发布门禁因后来的授权文档提交而拒绝，原断言未改；专项身份门禁以2f09a56为起点，并精确保留全部旧ABI和174个完整工程输入身份。

## CDC与约束审计

final_cdc1/audit.log、meta_to_sync.timing和exceptions.timing核对四个raw pad仅接第一级、4+4逻辑级及实际打包后的8个FF连接。Slice可能以无关accumulator/count命名，按实际路径引脚追踪并打印真实cell属性，不凭实例名。meta→sync仍参与时序，原约束字节、器件/参考speed2、10ns、实际九路GPIO/RS485/双HP及M4禁用保持。所有TD综合/布局/布线/数据库审计明确flow thread=16，get_num_thread记录实际16。
原#async_reg工具识别为0的资格问题不因正slack而自动关闭；ASYNC RESET属性不等于async_reg。实际拓扑/同步路径和例外审计与器件MTBF/实体资格分开，后者仍未取得。check_timing所有变化逐项见原始check，禁止新增false-path/多周期或切掉真实同步路径。

## 失败方案、身份与后续集成

第一候选flags-only：Slice+648、寄存器+191、setup+0.326/hold+0.020，不作为最终通过。第二候选joint_top2为+0.412/+0.020、Slice-53，仍失败。第三次继承布局布线研究经可靠恢复原约束后+0.569/+0.020，仍失败。第四完整候选cofactor_top4为+0.523/+0.020、Slice+314，仍失败；cofactor完整顶层gate logic LUT减少43、FF不变，单项route收益未隔离。CRC语法错误、空引脚探针、UTF-8/GBK读取错误均保留。poll_zero/terminal等仅研究未安装的候选不计最终收益，详见WORKLOG。
预算恢复故障：旧set_clock_uncertainty 0在经过route后没有清除1.25ns预算，原恢复断言拒绝，因此旧route.timing文件名不能证明名义值。constraint_restore_probe1验证clear_user_sdc后载入两份原约束可完全恢复；最终重放原route几何并保留同一经哈希认证的原place报告，逐项核对导出的实际SDC命令、全部路径sdc uncertainty=0及hold。失败原件和纠正证据同时保留。
第四轮place预算实际生效，但再次read同一优化SDC没有保证route重新生效；两份route报告都为0.000额外uncertainty，差值断言拒绝。最终第五轮route_closure_safe.py先清空/重载原约束再读取唯一新margin，结束后再次清空/重载并导出生效命令；原约束全局+1.133/+0.020，收紧预算中间值-0.117不作为通过依据。只读数据库重放再次得到完全相同结果。首次final_nets1/warnings1对四个零引脚占位网查询不支持的FLAT属性而拒绝，原错误保留；final_nets2/warnings2以完整连接报告严格核对Pins/Drivers/Loads/InOuts均0，不把空属性直接当0，不屏蔽原厂诊断。
生产集成需使用本轮三份手写RTL：pl_safety/rtl/safety_controller.v、pl_motion/rtl/motion_stream_rx.v、pl_motion/rtl/motion_service.v，以及原冻结安全生成链/其他RTL。不得把optimization/中的oracle/失败/研究module文件加入产品编译。生成定义与配置保持原值，运行三个生成器--check；所有新实验使用新tag。
复现：controller/receiver/service逐拍检查→run_candidate_tests.py --prefix NEW --stage units→--stage system→相关遥测并发→build_closure.py --tag NEW --optimize-physical→必要时restore_full_top.py --parent NEW --tag NOMINAL→physical_audit.py/pin_inventory.py/cdc_audit.py→report.py。优化place/route可收紧预算，但最终必须清空/重载原用户SDC并核对有效命令和0.000ns额外uncertainty。原完整工程冻结缓存需按原交接恢复并核对哈希，不能替换成简化顶层或stub；全部操作在pl_safety/build新目录，不修改BSP。
TIMING_RELEASE.json与evidence.zip封存源码Git blob、原始/规范化哈希、完整工程174输入、约束/IP/工具脚本和证据。使用seal.py --verify复核；该专项不生成SAFETY_RELEASE.json或部署镜像，旧发布/回退/日志不删除。

## 未关闭发布门禁

S2MM-only原厂IP SYN-5066保留；四个安全输入的实际针脚/电气/极性与输入资格、RS485外部IO delay、实物speed、同步器属性/器件MTBF及机械停止/复电资格、BSP地址/GIC和DMA/DDR静止/quarantine/板测仍独立未关闭。没有操作COM4、SD/eMMC/QSPI或板卡，没有bitgen、自动REBASE/ENABLE/START。WNS达标不等于可以部署。
