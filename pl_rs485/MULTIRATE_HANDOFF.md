# PL RS485 多速率采集实现交接

2026-10-13，身份servo42c-multirate-rtl-v1。完成已确认的五查询独立周期、原子配置、正常/异常间隔分离、三次逻辑通信失败后500ms节点退避。源身份与最终仿真/TD绑定见evidence/identity_multirate.json。只在pl_rs485交付；运动/BSP/Golden/GPIO、GP/DMA/DDR与镜像未修改、未下载板卡。

## 源码与协议

- 新顶层rtl/rs485_multirate.v：配置准入、到期扫描、周期合并、节点故障状态及统计。
- rtl/rs485_transaction.v：一条逻辑请求的UART/DE/帧校验/解析、最多一次重试、隔离和整记录发布。
- rtl/div_u64_u32.v：64次迭代无符号64/32除法，用于配置预算和逾期合并，没有组合大除法。
- 原rs485_master、uart_tx/uart_rx、record_fifo源码保留。新引擎复用同一UART及FIFO模块，不将新调度插到运动路径。

线协议及256bit记录仍由schema.json定义，30/33/39/3A/3E白名单、sum8、长度、大端、RX时间戳语义不变。rate_design.json定义周期限制、准入门槛、退避和配置错误码；tools/generate_rates.py生成rate_parameters.vh、rate_defs.vh/h。改常量必须改JSON再生成，不能分别改C/Verilog头。协议没有应答命令/事务号的关联限制，以及实际固件/STP/转换模块待验证项，继续适用原PROTOCOL_CONTRACT.md。

## 默认配置与快采候选

|顺序/period打包位|命令|兼容默认周期|快采候选周期|
|---|---|---|---|
|0 / 31:0|30|125000us / 8Hz|20000us / 50Hz|
|1 / 63:32|33|500000us / 2Hz|100000us / 10Hz|
|2 / 95:64|39|125000us / 8Hz|20000us / 50Hz|
|3 / 127:96|3A|1000000us / 1Hz|200000us / 5Hz|
|4 / 159:128|3E|1000000us / 1Hz|200000us / 5Hz|

三轴E0/E1/E2、115200/8N1、100MHz；五周期所有节点共用。默认NORMAL_CYCLES/ERROR_CYCLES均1000000（10ms），POLL_CYCLES也10ms；快采**仿真编译候选**设置NORMAL_CYCLES=POLL_CYCLES=100000（1ms），ERROR_CYCLES仍10ms。总超时10ms、字节间2ms、DE提前/后保持/释放屏蔽各10us；最多一次重试。BACKOFF_US=500000。节点数量及低字节先的SLAVE_ADDRS为编译参数，最多10个合法、唯一E0..E9地址，改变数量需同时配置地址并重新验算带宽，M4未定不加入。

复位先禁用调度，再将DEFAULT_PERIODS和默认mask自动送入同一RTL配置检查；成功产生首次cfg_applied、revision=1，才启用配置。超载默认同样拒绝且保持禁用。初始收发器仍完成异常隔离后才能发包。手工提交需等cfg_ready；不需要另建初始化epoch。默认配置频率是独立交付的工程profile，不等同于固件承诺的实际数据更新率。

## 配置接口与准入

|接口|语义|
|---|---|
|clk/rst_n/enable/time_us/rx/tx/de|同原域与统一时间输入；rx两级同步；复位取消事务，DE=0、TX=1，不修改外部time_us|
|cfg_period_us[159:0] / cfg_mask[4:0]|低位到高位30/33/39/3A/3E；period=0或mask位0禁用；周期单位us，非零范围1000..2147483647|
|cfg_valid/cfg_ready|posedge valid&&ready锁存完整shadow；输入保持到握手；最多一个待处理提交|
|cfg_applied/cfg_rejected/cfg_error|单拍结果；成功原子应用，失败保留旧配置。error=1范围、2预算、3revision耗尽，0成功；错误码仅在结果脉冲时解释|
|cfg_revision/cfg_apply_sequence|每成功应用revision加1、不回绕（耗尽拒绝）；apply_sequence是下一新逻辑请求编号。初始化成功也是一次应用|
|active_period_us/active_mask/config_load_ppm|当前已应用配置和保守正常服务占用ppm；未成功初始化前全部0|
|busy|整条逻辑事务及重试/完成隔离期间为1；扫描/配置验证/无事务总线隔离时可为0，不代表总线可立即发包|
|record接口及accepted/errors/ignored_rx/dropped/fifo_level|沿用整记录队首握手、满丢新/饱和统计；accepted计校验有效应答，errors计异常尝试|

period/mask一起锁存，验证可与旧事务重叠；只有旧请求及其重试、必需隔离结束，才原子应用。验证期间暂停选择新请求，不中断旧事务。全零配置也必须走握手。此接口为独立同域输入，不接GP；后续用户界面/PS适配另立任务。

RTL逐项检查周期范围，用64拍除法计算`ceil(SLAVE_COUNT × service_cost_us(q) × 1000000 / period_us(q))`，只对有效项累计，超过750000ppm拒绝。service_cost是帧传输向上取整微秒+DE前后+200us响应开始预算+正常隔离，与最短请求起点间隔取最大。200us是未实测的规划假设，不是协议响应保证；连续应答、无额外字节间隙也是该预算前提。误差/超时/离线情况下不保证设定频率。快采候选RTL准入712740ppm；保守整数取整略高于规划工具71.26%的连续时间估算。10ms默认拒绝同样的50/10/50/5/5Hz组合，不静默降速。

软件/采集运行清单必须保存系统epoch、revision、active配置和apply_sequence范围。256bit记录无配置版本字段，不能将sideband“当前配置”误关联到FIFO中的历史记录。模块软复位后序号/revision归零，消费者必须取消旧事务并记录复位事件；外部时间继续运行。

## 调度、退避和统计

每(地址,查询)一个64bit next_due；配置应用后首次设为应用时间。最多50任务，逐拍扫描，理想到期起点最早的任务先发，同时间按游标轮转。空扫描最多每个系统微秒重扫一次；有到期任务仍只发一条，不广播、不并行。扫描和64拍除法开销包含在实测lateness中。暂停/配置更新后按当前时间重建到期点，关闭期间不突发补发。

实际DE上升时锁存请求时间，计算missed=floor((now-next_due)/period)，再用余数得到`next_due=now-remainder+period`，保持相位并一次合并漏采。重试保留sequence/request_us，不新增采样任务；不能把目标50Hz解释为每20ms必有有效数据。比较与加减使用64bit模差，要求时间单调推进（自然回绕允许），同epoch内不向后跳时钟；本模块不生成自己的epoch。

每节点连续3个最终无有效应答的逻辑请求触发500ms退避；初次失败重试成功清连续失败。保护状态=1、使能状态、未知业务枚举以及FIFO丢记录均不算通信失败。退避期间普通任务不发，其他节点继续。到期后仅选择启用查询中周期最短者探测，等周期轮转；成功清离线并重基该节点各任务到当前时间，失败再次500ms，不补发旧积压。全零不探测，配置切换保留离线/失败状态，避免用改频率绕过退避。

BUS_BUSY计总线级事件，不增加某节点失败次数；中断重试时可发布status=6异常尝试，完成后的隔离被持续噪声占用则通过bus_busy_events报告，已通过校验的记录保持有效。无在途请求时持续噪声仅计总线事件、不生成假请求记录，始终保持接收态，不能用“bus忙”把所有节点判离线。

|统计接口|定义|
|---|---|
|debug_task[5:0]|task=节点索引×5+查询索引；越界读0|
|stat_sent|已发送新逻辑请求数，探测也算，重试不重复计|
|stat_scheduled|已发送+在dispatch合并的漏掉周期数；不是未来排队长度|
|stat_valid|逻辑事务最终有效完成数，即使FIFO丢弃也计入；比accepted的事件时刻晚完成隔离|
|stat_missed|dispatch时合并的漏采周期数；离线期间被取消的普通周期不计入该数|
|stat_max_lateness_us|实际DE上升相对所选理想到期点的最大延迟，超过32bit饱和|
|debug_node[3:0]|节点索引；越界读0|
|node_offline[9:0]|离线退避位图，未配置节点为0|
|node_failure_streak / node_cooldown_until_us|8bit饱和连续逻辑失败数/64bit退避截止时间|
|node_backoff_entries / bus_busy_events|32bit饱和退避启动次数（含失败探测续期）/总线隔离期限事件|

任务计数均32bit饱和，复位清零，配置更新保留累计统计。以offline位、退避次数与时间估计离线缺采，不提供“离线取消了多少个理想采样点”的独立计数（该设计建议本版未实现）。debug组合读输出要求索引和消费者同域，在同一posedge快照；无跨域/GP读取原子性承诺。

## 验证与复现

多速率种子20261013，日志evidence/sim_mr_release/：64拍divider随机算术、混合周期逐节点计数、全部31个mask/全零/周期0、范围/超预算拒绝、在途含重试原子配置、错checksum/UART framing/无响应/错地址/迟到/重复/截断/回显、保护有效、节点三次最终失败/500ms退避/启用查询探测/失败续期/恢复、健康节点继续、FIFO满不影响调度、不将总线忙归因节点、漏采合并、64bit自然回绕、复位中断及独立STP参考逐拍一致。退避测试将**注入的系统时间**推进到真实500000us截止点以免等待长仿真，不改变RTL时间单位；串口用加速profile覆盖异常。正式profile独立使用100MHz/115200和1ms正常/10ms异常时间。

旧单速率测试evidence/sim_mr_legacy_r3/通过，旧master/UART/FIFO与原身份字节一致。失败及修正见evidence/MULTIRATE_FAILURES.md和各r1..r4目录，失败非零退出，不自动重试/隐藏。最终文本日志、源码/规范/fixture哈希入Git，VVP/VCD和TD数据库不入Git。

从dev目录运行：

```powershell
python pl_rs485/tools/generate.py
python pl_rs485/tools/generate_rates.py
python pl_rs485/tests/run_sim.py --tag legacy_verify --seed 20261013
python pl_rs485/tests/run_multirate.py --tag mr_release --seed 20261013
python pl_rs485/build_td.py --multirate --tag release
python pl_rs485/build_td.py --multirate --fast --tag release
python pl_rs485/tools/freeze_multirate.py
```

Python3.10、Icarus12.0 devel、TD2026.1 SP2/build6.2.2.200067，DR1M90GEG400参考speed2。本机Icarus在Windows沙箱内可能access violation；同一本地命令需在允许工具执行的终端运行，崩溃不能视为通过。TD使用独立scan观测封装，不指定板球位、不生成bitstream，不代表外部IO/CDC/电气或系统集成验收。

最终资源/时序及模拟频率统计在本文附录和evidence/td_multirate*_release/。板上固件身份、STP并发、转换模块末停止位释放/最早应答、迟到重复边界与真实带宽必须按原清单实测；只有验证后才可部署1ms快采profile。模型训练按实际请求/应答时间、有效性和离线/丢弃统计处理异步采样，不作为最终急停链路。本批完成独立RTL交付后停止。

## 最终证据附录

种子20261013：divider、multirate及115200 profile三个bench全部通过。多速率异常回归中独立STP模型623146次翻转与参考逐拍相同；这是仿真隔离证据，不是实际驱动器STP并发验收。

混合周期3000/11000/7000/13000/17000us的60ms窗口，各轴对应样本数分别20～21、6、9、5、4，与请求周期及边界样本一致。正式115200快采profile在100ms起点窗口加事务排空期间取得42条有效记录；30/39每轴5～6条、33每轴1～2条、3A/3E每轴各1条。短窗口包含各慢查询的首次立即采样，不能用这100ms样本数推断5Hz的长期平均；长期周期调度逻辑已由跨多个周期的混合测试覆盖。task0最大lateness=15688us、missed=0，启动时所有任务同时到期带来抖动，不能把频率目标称为严格20ms无抖动时限。

|profile/阶段|setup WNS ns|hold WNS ns|
|---|---|---|
|10ms默认 / gate|+2.005|0.000|
|10ms默认 / place|+3.742|0.000|
|10ms默认 / route|+0.803|+0.029|
|1ms快采候选 / gate|+2.241|0.000|
|1ms快采候选 / place|+3.702|0.000|
|1ms快采候选 / route|+1.271|+0.037|

两组均10ns、双corner OOC，内部setup/hold通过；未使用放宽时钟或多周期例外。总资源（含较宽的输入/输出scan观测封装）：默认6030 LUT6、7136寄存器、6893slice；快采6060 LUT6、7146寄存器、6942slice。两者均120 DRAM LUT、1 DSP、0 ERAM/PLL。详见各route.area的层级行区分核心与封装，不将不同TD分类简单加总。

诊断：STA覆盖默认92.13%、快采92.08%；两者0无时钟节点、0非法约束、0组合环。保留SYN-5025默认置零提示、SYN-6021未指定8个IO球位、scan观测结构SLATR-1038属性诊断、1个工具物理LSLICE unused ofb dummy节点；4输入/3输出没有外部delay。自动球位只用于OOC实现，不是L17/N16/N15板级约束；未生成bitstream。详细路径、route_status检查和工具日志全部保留，外部IO时序/异步复位释放与CDC/板级电气需在后续真实顶层验证。
