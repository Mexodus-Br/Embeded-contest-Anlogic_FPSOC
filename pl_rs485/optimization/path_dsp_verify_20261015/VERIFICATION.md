# 2026-10-15 setup 路径与 DSP 复核

仅复核源码提交49e8ac6、证据提交5f88d0f，不改变RTL、IP、约束、冻结交付或优化发布清单。读取原有完整顶层route checkpoint，未重新布局布线或生成部署镜像。旧/新工作工程的route.area与route.timing SHA256均与已归档原件相同；checkpoint身份记录于verification.json。

## +0.080ns setup 路径

原始报告：../top_r1/reports/gp_route.timing:87；完整第一条路径摘录：critical_path.txt。器件DR1M90GEG400，参考speed2，Routed，slow corner，board_100m上升沿到下一上升沿，10.000ns。

起点：control/core/fabric/rs485/collector/sent_reg[387]_syn_3.clk，位置x054y009z4；实际发射数据输出.oqb连接inflight[0]_dup_3。

终点：control/core/fabric/rs485/collector/missed_reg[296]_syn_2.ima，位置x051y004z6；该Slice的.oqa连接observe_tasks[904]，.oqb连接observe_tasks[744]。

功能为inflight选择、missed读取、加quotient及32bit饱和判断/写回。对应rs485_multirate.v:69的65bit sat_add，以及:182的missed[inflight]更新。路径报告中加法网络source line173是工具合并映射标注，不能仅凭这个行号将其归为scheduled更新。

|项目|数值ns|
|---|---:|
|Data Path Delay|9.702|
|cell / net|1.996 / 7.706|
|launch clock arrival|4.810|
|capture clock arrival|4.419|
|setup|0.068|
|默认clock uncertainty|0.060|
|CRPR|+0.301|
|Arrival / Required|14.512 / 14.592|
|Slack|+0.080|

Required=4.419+10.000-0.068-0.060+0.301=14.592；Arrival=4.810+9.702=14.512。报告Clock Skew=0.090ns；从明细计算的有效capture-minus-launch skew为-0.090ns，不应将报告的绝对值理解为正向时序收益。

报告逻辑级数7（5 LUT6+2 ADDER；中间carry链还列出多个物理ADDER单元，不应把7解释为7个物理单元），最大fanout201。inflight[0]_dup_3第一段net延迟1.991ns；末段missed[0]_b17[8] fanout15、延迟2.124ns。两段合计4.115ns，约占全部net延迟53.4%。这条路径主要受布线延迟影响，不能把总资源下降当作这条路径时序改善。

途经cache/frozen_reg[7428]_syn_2的Slice，其LUT输入/输出连接collector/missed网络，而.oqa/.oqb寄存器输出连接cache/frozen[7428]/[8104]；这是组合LUT与快照寄存器共用Slice的物理打包，不能仅凭实例名认定路径执行cache乘法或经过快照寄存器。实际属性/引脚连接见optimized_dsp_final.log。

## 减少的10个DSP

完整顶层route.area：cache 10→0，motion_planner 4→4，rs485_multirate 1→1，总数15→5。层级资源含子模块；这里采用三个互不包含的实际归属，未重复相加。

baseline_dsp.rpt列出以下cache物理DSP（公共前缀control/core/fabric/telemetry/cache/）：

|乘法组|第一DSP实例 / 位置|第二DSP实例 / 位置|
|---|---|---|
|mult0|mult0_syn_167 / [99,36]|mult0_syn_260 / [99,40]|
|mult1|mult1_syn_167 / [99,52]|mult1_syn_260 / [99,52]|
|mult2|mult2_syn_167 / [99,64]|mult2_syn_260 / [99,68]|
|mult3|mult3_syn_167 / [99,60]|mult3_syn_260 / [99,64]|
|mult4|mult4_syn_167 / [99,40]|mult4_syn_260 / [99,44]|

位置报告只给DSP grid，不包含grid内不同offset，因此同grid不等于同一DSP。report_cells -dsp还输出DSP内部乘法/辅助单元；不能将全部37/12行分别当作37/12个物理DSP。物理使用数量以完整顶层area为准。

baseline_connections.log验证mult0_syn_167和mult0_syn_260均为DR1_PHY_DSPSIOU、Type DSP，属于同一mult0宏；分别连接period低17bit和高15bit。mult0_syn_168是DR1_PHY_DSPMULT_V2内部单元，并非额外物理DSP占用。optimized_dsp.rpt没有cache乘法组，仅保留planner和collector。

原cache的snapshot_capture循环使用limit={32'd0,active_period_us[(i%5)*32+:32]}*RT_STALE_PERIODS，RT_STALE_PERIODS=3。15行按查询共享同一period，工具得到五组乘法，每组映射两个DSP。新cache在捕获时对五组查询各计算一次34bit p+(p<<1)，保留max(100000,3p)，冻结34bit结果并在读出时零扩展为64bit。最大值3×0xffffffff=0x2fffffffd=12884901885，34bit完整可表示，没有缩减原可观察数值范围。未删减计数、节点、查询或功能，未迁往PS；既有缓存差分验证覆盖该字段。

复核命令：在本目录串行执行td_commands_prompt.exe baseline_dsp_final.tcl、optimized_dsp_final.tcl、baseline_connections.tcl，然后python extract_evidence.py。脚本只import_db/report_cells；不export_db，不修改原checkpoint。baseline_dsp.tcl/.log保留第一次缺少-mode参数的失败尝试；修正脚本明确使用-mode final，成功标记和无ERROR由extract_evidence.py校验。
