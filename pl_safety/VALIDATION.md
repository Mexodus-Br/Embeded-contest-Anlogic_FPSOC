# 验证范围与时延报告

冻结RTL功能证据见SAFETY_HANDOFF.md所列10个tag。输入/停止时延以100MHz实际STEP引脚边沿与独立检查器核验，不以1us时间戳推断纳秒级响应。未连接板卡或电机。18项旧回归的具体命令见timing_regress1/result.json；真实安全系统包含RS485顶层但未追加专用RS485激励套件，RS485 RTL保持原封存源码。

## 数字输入与停止预算

稳定异步输入在第1采样边沿进入meta、第2进入sync、第3由执行器禁止新STEP；数字模型的pad到禁止新边沿为2..3周期（20..30ns，取决于相位）。同步active生效到执行器抑制新边沿为1周期。触发不加毫秒滤波；释放按独立RELEASE_CYCLES资格。复位/未知状态不授权HOME，尚未配置释放时间也不屏蔽已采样急停。

predecode_phases1覆盖7场景各24相位，其中两类HOME急停共48个案例输出LATENCY明细：

| 指标 | 观察范围（100MHz周期） | 说明 |
|---|---:|---|
| pad_qualified | 2 | 此表仅含固定亚周期注入相位的48例，输入测试另覆盖10种亚周期相位 |
| executor_inhibit_bound | 3 | 每个执行器采样边沿均断言不产生被禁止的新STEP |
| qualified_drain | 0..6 | 从同步触发生效到pulse-safe，受当前H/L/Q残余影响 |
| qualified_en_off | 6..11 | 独立观察EN实际关闭，不能用停止应答代替 |

快速夹具H=3、L=2、S=4、Q=7、E=5、OFF=3。predecode_resource1另用H/L/S/Q/E/OFF均500周期、max100kHz，检查真实高脉冲精确500周期、低电平/方向/EN建立保持、位置与退离距离；不是用快速夹具替代完整工程参数。

通用保守排空边界为检测后max(H+L,Q)+2周期；EN_OFF保守边界再加OFF+3周期。完整工程资源夹具为1002周期（10.02us）与1505周期（15.05us），分别表示排空与EN关闭的保守上界，并非实物测得停止时间。普通STOP只禁新边沿和排空，保留EN与valid；急停另失能。已有高脉冲不被截短，公共复位不作正常停止。

物理最大允许延迟尚未冻结；预算不含外部RC/触点传播、布线及亚稳态统计影响。短脉冲可能漏采，本实现不是异步捕获器。独立NO只能反馈急停动作，不能测12V切断、检测断线或证明机械停止。

## 完整工程身份与门禁

2026-10-17目标收紧为最终布线setup WNS>1ns且hold≥0；布局估计通过或setup仅非负均不能封存。所有后续TD操作明确threads=16。TD 6.2的有效Tcl属性名为`flow thread`，由`get_num_thread`核验实际16线程；`flow threads`会成为不生效的wild参数，不能使用。完整工程采用`open_project -single_run`，参数在打开工程/导入数据库后设置。完整构建与独立CDC审计均记录设置和读回。

| 构建 | 线程 | 综合setup WNS | 最终布线结论 |
|---|---:|---:|---|
| sealed_top1 | 默认22 | -3.319ns | setup -1.355ns、hold +0.021ns，失败 |
| timing_top2 | 默认22 | -3.878ns | 中断，无最终结论 |
| split_top3 | 默认22 | -2.254ns | 布局中断，无最终结论 |
| threads16_top4 | 启动检查拒绝auto | 未执行 | 单次工程模式修复前的保护拒绝 |
| threads16_top5 | 显式16 | 未完成 | 旧接收器源码候选被主动停止 |
| rxcarry_top6 | 显式16并实际读回 | -1.630ns | 布局+2.392ns；最终setup +0.240ns、hold +0.020ns，未达到>1ns目标 |
| predecode_top7 | 显式16并实际读回；high/128/high/on | -1.306ns | 布局+2.332ns；最终setup +0.016ns、hold +0.020ns，未达到>1ns目标，用户要求暂停 |

rxcarry_top6综合报告所列最差路径转为安全寄存器address→submit→normal_ok→执行器dir_age的CE，11级，最大fanout607；原接收器completed+1路径已退出最差路径。与split_top3综合-2.254ns、13级、该路径最大fanout1064相比有所改善，但不能把综合估计或所列路径fanout当作最终布线/全网结论。

predecode_top7对SUBMIT/STOP提前译码后，综合所列最差路径为controller/count→executor/dir，11级、最大fanout214。AW/W错开、所有公开输出及检测拍由predecode_equivalence1对前版62048次检查证明；32功能/168相位/真实IP/500周期自检也重新通过。布局设置high HFN、max_fanout128、high opt_timing、logic_level_opt on，实际读回见effective_parameters.tcl（本版TD输出的是参数表，不作为可执行Tcl使用）；run.tcl保存实际设置命令。

rxcarry_top6完成16线程全流程，但只是前一源码版本的对照，不含后续寄存器预译码，不能作为当前冻结RTL的最终性能证据。其最差物理起点pos_reg[116]_syn_21的oqb实际输出controller/state[1]，经failure/count选择与HOME运行资格到执行器方向时序控制，10级、该路径fanout37；不能据Slice名称将其误判为位置数据通路。最终setup +0.240ns、hold +0.020ns，默认时钟uncertainty 0.060ns保留。check_timing为invalid constraint(0)、combinational loops(0)，no input delay(5)含四个异步安全pad及原rs485_rx；no output delay(2)为原RS485输出。完整报告和输入身份保留。

| 资源 | 原round2完整顶层 | rxcarry_top6对照 | 增量 |
|---|---:|---:|---:|
| LUT6等效 | 26090 | 27742 | +1652 |
| Slice | 33222 | 35243 | +2021 |
| Slice寄存器 | 34381 | 36139 | +1758 |
| Pad寄存器 | 9 | 9 | 0 |
| ERAM | 58 | 58 | 0 |
| DSP | 6 | 6 | 0 |
| IO | 13 | 17 | +4 |

此表只比较同类报告，不把工具中间的资源分布/局部密度比例当成芯片最终利用率。当前候选须另以其最终route.area及route.timing封存。

独立工程由原round2实际PS/GP/HP0/HP1/DMA/RS485工程按封存输入哈希复制，安装工具TD Release_2026.1_SP2、DR1M90GEG400参考speed2、100MHz/10ns。CONFIG_PROFILE=2资源夹具与500周期底座匹配；生产默认PROFILE=0禁止启动。原厂受保护IP未修改。当前源码完整16线程工程为build/predecode_top7，实际脚本、输入哈希、约束及报告归档于evidence/predecode_top7_paused/，大型数据库留在忽略的build/；没有bitgen。首轮sealed_top1完整报告保留于evidence/sealed_top1_complete/，其setup=-1.355ns、hold=+0.021ns，不能称100MHz通过；timing_top2与split_top3仅保留综合和中间布局，不代表完整顶层通过。

原九路J12观察输出/RS485约束保留；新增四个安全输入尚无核验针脚，工具自动pad不是接线方案。只有四个异步pad作为例外起点，源码中它们只驱动第一级meta；meta→sync路径起点是寄存器，仍参与时序。首轮按打包前.d名称选择终点未命中，不能使用该无效约束。新工程使用仅指定pad起点的有效约束，CDC逻辑集合与约束门禁另由audit_cdc.py复核；工具报告的属性识别和实物MTBF须单独解释，不能只看RTL有两级就宣称板级CDC通过。

综合QoR的#async_reg为0，虽然RTL使用厂商既有源码中的小写async_reg属性，仍不能声称工具已识别。两级逻辑功能由输入自检证明，约束选择由独立审计复核，物理同步器放置/MTBF没有资格结论。

本机TD随附SWUG105（2026.01）§4.9.9说明TD6.2.2默认不启用async_reg property，需另设rtl directive:async_reg及place async_reg；report_mtbf所列支持器件为PH1A。本工程DR1尚未获得工具属性/物理放置与器件MTBF资格，不将逻辑两级或正slack替代这些结论。后续改变同步器实现/工具设置须重新综合布局布线及审计。

原SYN-5066受保护S2MM DMA多驱动、RS485输入/输出delay缺失、实物speed、电气/接线/驱动复电及DMA/DDR隔离门禁继续保留。资源/STA报告不解除发布阻塞，实板验证未做。失败及中断见FAILURES.md，原始日志保留。

## 2026-10-17 用户暂停

当前RTL冻结在5ccd875，十组功能/等价性证据保留。predecode_top7完整布线最终setup +0.016ns、hold +0.020ns，严格WNS>1ns门禁未通过。该版本资源为LUT6等效27866、Slice35605、Slice寄存器36263、Pad寄存器9、ERAM58、DSP6、IO17；相对原round2增量分别为1776、2383、1882、0、0、0、4。

predecode_top7最终最差路径为pulse_event[1]经观测计数加法及HOME失败/运行资格到a0_dir，10级，含两级ADDER、该路径最大fanout11，数据路径9.757ns（cell2.372/net7.385）；默认uncertainty 0.085ns保留。这只是后续专项优化的分析入口，未据此追加RTL改动。

closure_top8在布线后物理优化阶段按用户要求停止；其附加预算下中间slack不代表原约束最终结论，缺少恢复原约束后的最终报告。最终CDC审计cdc_final1未执行，未生成SAFETY_RELEASE.json；生产配置禁止启动，未上板。此次只归档现有结果，不追加测试或工具运行。