# 完整实际 GPIO/HP1 顶层资源与时序 — 2026-10-14

同一最终 system_wrapper 的布线映射资源；DR1M90GEG400 参考 speed2，实物速度未确认。不是独立夹具相加。

|资源|已用|工具总量|占比|剩余|
|---|---:|---:|---:|---:|
|LUT6|32720|52480|62.35%|19760|
|Slice|44346|52480|84.50%|8134|
|Slice 寄存器|48872|104960|46.56%|56088|
|ERAM|34|280|12.14%|246|
|DSP|15|240|6.25%|225|
|GCLK|1|32|3.12%|31|
|SCLK|6|72|8.33%|66|
|IO/PAD|13|126|10.32%|113|

寄存器设计总计48881=Slice寄存器48872+独立PAD寄存器9；104960是工具给出的Slice寄存器容量，PAD另列，避免重复计数。IO13为时钟/RS485 RX两个输入及九根真实运动输出+RS485 TX/DE两个输出；113余量是工具封装资源，不等于连接器空闲GPIO。另有F7MUX255/26240、F8MUX94/13120、SOC1/1、PLL0/8、LCLK0/20、MLCLK0/8、IOCLK0/16；分布RAM使用2704个DRAM LUT（338个DRAM硬结构），见原始area。

|阶段|setup WNS ns|hold WNS ns|覆盖率|corner|
|---|---:|---:|---|---|
|gate|-1.739|+0.000|99.99%|Both (Slow and Fast)|
|place|+2.152|+0.000|99.99%|Both (Slow and Fast)|
|route|+0.104|+0.021|99.99%|Both (Slow and Fast)|

内部100MHz route通过，setup/hold违例端点为0。gate负估计、布线中负裕量、主机超时及后续修复日志完整保留。同源board_100m和真实PS GEN_PL_GP0S/HP0/HP1均100MHz。保持既有九GPIO异步20ns预算，没有新增false-path/多周期或放宽10ns。

check_timing：无时钟0、时钟定义问题0、非法约束0、组合环0；dummy节点2（原厂ERAM未用复位/规划物理OFB说明见原报告），RS485缺input_delay1/output_delay2。真实UART外部时序仍须资格确认，99.99%不能当实体IO全部签核。SYN-5066内部多驱动未关闭：timing_pass=true、diagnostics_closed=false、signoff_pass=false。未bitgen。

拥塞：详细布线早期overflow177375，最终225526条路径全部完成、overflow0，eco open net0；初始/优化后的top1等区域拥塞指标和完整route.qor/DRC日志保留。高局部拥塞曾与84.50%总Slice并存，不能用总体余量承诺后续资源可无代价放入。

## 层级资源（包含子模块，不能相加）

下表是route层级逻辑LUT/ripple/seq/DRAM-LUT计数，不是可相加的顶层LUT6/Slice增量。gate估计另列于hardware-review.json和gp_gate.area。

|模块|logic LUT|ripple|seq|ERAM|DSP|DRAM LUT|
|---|---:|---:|---:|---:|---:|---:|
|motion_dma_lite_top|6643|3826|10669|16|4|864|
|motion_service|5568|3627|8512|0|4|864|
|rs485_probe_time_regs|422|0|588|0|0|0|
|axi_lite_six_way|129|0|305|0|0|0|
|rs485_gp_bridge|5639|1221|10186|6|1|16|
|rs485_latest_cache|5392|1024|21044|0|10|0|
|rs485_telemetry|928|573|1140|0|0|1824|
|telemetry_dma_lite_top|981|135|1676|12|0|0|

保留检查：九输出均映射为对应J12焊球OREG；缓存仍有21044个seq、完整15×128B快照/有效值和结果路径；运输FIFO映射1824个DRAM LUT；原DMA/运动16 ERAM、新独立DMA12 ERAM及RS4856 ERAM保留。源文件/显式端口审查、六路所有权391项和真实双controller系统测试配合验证可观测路径。受保护IP的综合等价性仍不由这些计数证明。

## 对照（不叠加）

旧scope：LUT6 13051、Slice15335、设计寄存器13616、ERAM16、DSP4，route +0.031/+0.021ns；当前分别增加19669、29011、35265、18、11。新增采集/15组cache/原子快照/256条运输FIFO及独立DMA/HP1解释资源增长。

telemetry_soc参考夹具：LUT6 34187、Slice45387、寄存器49540、ERAM34、DSP15、IO4、route +0.018/+0.020ns。当前LUT6少1467、Slice少1041、寄存器总数少659而IO增至13。参考夹具使用四轴3/2/4/7/5/3cycle、10MHz测试参数，且没有保留完整运动引脚；本顶层使用三轴5us/100kHz、M4禁用及真实输出，优化/映射上下文不同。差值不是隐藏GPIO或缩小缓存获得，不能把参考资源直接代替本报告。
