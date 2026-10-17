# 验证范围与时延报告

冻结RTL功能证据见SAFETY_HANDOFF.md所列8个tag。输入/停止时延以100MHz实际STEP引脚边沿与独立检查器核验，不以1us时间戳推断纳秒级响应。未连接板卡或电机。

## 数字输入与停止预算

稳定异步输入在第1采样边沿进入meta、第2进入sync、第3由执行器禁止新STEP；数字模型的pad到禁止新边沿为2..3周期（20..30ns，取决于相位）。同步active生效到执行器抑制新边沿为1周期。触发不加毫秒滤波；释放按独立RELEASE_CYCLES资格。复位/未知状态不授权HOME，尚未配置释放时间也不屏蔽已采样急停。

split_phases2覆盖7场景各24相位，其中两类HOME急停共48个案例输出LATENCY明细：

| 指标 | 观察范围（100MHz周期） | 说明 |
|---|---:|---|
| pad_qualified | 2 | 此表仅含固定亚周期注入相位的48例，输入测试另覆盖10种亚周期相位 |
| executor_inhibit_bound | 3 | 每个执行器采样边沿均断言不产生被禁止的新STEP |
| qualified_drain | 0..6 | 从同步触发生效到pulse-safe，受当前H/L/Q残余影响 |
| qualified_en_off | 6..11 | 独立观察EN实际关闭，不能用停止应答代替 |

快速夹具H=3、L=2、S=4、Q=7、E=5、OFF=3。split_resource2另用H/L/S/Q/E/OFF均500周期、max100kHz，检查真实高脉冲精确500周期、低电平/方向/EN建立保持、位置与退离距离；不是用快速夹具替代完整工程参数。

通用保守排空边界为检测后max(H+L,Q)+2周期；EN_OFF保守边界再加OFF+3周期。完整工程资源夹具为1002周期（10.02us）与1505周期（15.05us），分别表示排空与EN关闭的保守上界，并非实物测得停止时间。普通STOP只禁新边沿和排空，保留EN与valid；急停另失能。已有高脉冲不被截短，公共复位不作正常停止。

物理最大允许延迟尚未冻结；预算不含外部RC/触点传播、布线及亚稳态统计影响。短脉冲可能漏采，本实现不是异步捕获器。独立NO只能反馈急停动作，不能测12V切断、检测断线或证明机械停止。

## 完整工程身份与门禁

2026-10-17目标收紧为最终布线setup WNS>1ns且hold≥0；布局估计通过或setup仅非负均不能封存。所有后续TD操作明确threads=16。TD 6.2的有效Tcl属性名为`flow thread`，由`get_num_thread`核验实际16线程；`flow threads`会成为不生效的wild参数，不能使用。完整工程采用`open_project -single_run`，参数在打开工程/导入数据库后设置。完整构建与独立CDC审计均记录设置和读回。

独立工程由原round2实际PS/GP/HP0/HP1/DMA/RS485工程按封存输入哈希复制，安装工具TD Release_2026.1_SP2、DR1M90GEG400参考speed2、100MHz/10ns。CONFIG_PROFILE=2资源夹具与500周期底座匹配；生产默认PROFILE=0禁止启动。原厂受保护IP未修改。实际运行脚本、输入哈希、原约束与报告归档在evidence/split_top3/；大型数据库留在忽略的build/split_top3/，没有bitgen。首轮sealed_top1完整报告保留于evidence/sealed_top1_complete/，其setup=-1.355ns、hold=+0.021ns，不能称100MHz通过；timing_top2仅保留综合和中间布局，不代表完整顶层通过。

原九路J12观察输出/RS485约束保留；新增四个安全输入尚无核验针脚，工具自动pad不是接线方案。只有四个异步pad作为例外起点，源码中它们只驱动第一级meta；meta→sync路径起点是寄存器，仍参与时序。首轮按打包前.d名称选择终点未命中，不能使用该无效约束。新工程使用仅指定pad起点的有效约束，CDC逻辑集合与约束门禁另由audit_cdc.py复核；工具报告的属性识别和实物MTBF须单独解释，不能只看RTL有两级就宣称板级CDC通过。

综合QoR的#async_reg为0，虽然RTL使用厂商既有源码中的小写async_reg属性，仍不能声称工具已识别。两级逻辑功能由输入自检证明，约束选择由独立审计复核，物理同步器放置/MTBF没有资格结论。

原SYN-5066受保护S2MM DMA多驱动、RS485输入/输出delay缺失、实物speed、电气/接线/驱动复电及DMA/DDR隔离门禁继续保留。资源/STA报告不解除发布阻塞，实板验证未做。失败及中断见FAILURES.md，原始日志保留。
