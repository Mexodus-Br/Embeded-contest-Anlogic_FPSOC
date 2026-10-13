# PL RS485 驱动器状态采集独立交付

后续扩展：用户于2026-10-13确认多速率设计并要求完成RTL，新增独立rs485_multirate顶层。多速率接口、配置、退避、源码身份和新验证证据见[MULTIRATE_HANDOFF.md](MULTIRATE_HANDOFF.md)。下文是75a2080的原单速率交付基线，原master/UART/FIFO源码未修改；原identity.json与TD证据对应该历史交付，新的工具和多速率文件采用独立identity_multirate.json。

交付日期2026-10-13，协议身份`servo42c-readonly-v1`。本目录与运动PL、BSP、Golden、GPIO和启动镜像独立。未下载板卡，未创建bitstream/启动镜像，未连接运动FIFO、GP或DMA。交付提交以Git中引入本文件及本目录的提交为准；固定文件SHA-256见`evidence/identity.json`，资料身份见`evidence/sources.json`。AGENT.md已有修改和无关日志不纳入提交。

## 已确认与待验证

用户接受集中协议和256bit/8条FIFO契约，将baud改为115200，并要求加快轮询和可选择查询。实现100MHz、115200、8N1，三从机E0/E1/E2、M4禁用；最短槽间隔10ms；总超时10ms、字节间2ms、最多一次重试；DE前后各10us，释放后屏蔽10us，连续安静隔离10ms。参数均为**独立验证profile**，不是已验证的驱动器/转换模块参数。支持1..10个可配置地址列表，地址打包低字节先；M4协议不明不加入白名单。

唯一规范`schema.json`，派生`generated/parameters.vh`、`rs485_defs.vh`、`rs485_defs.h`和查询表由`tools/generate.py`生成，禁止分别维护常量。协议/FIFO完整约定见`PROTOCOL_CONTRACT.md`。当前时钟、reset、mask、enable、ready和time_us都要求同域；rx使用两级同步。系统提供异步置位、同步释放rst_n和共同64bit/1MHz time_us；本模块无自己的时间epoch。

只读查询白名单：

|mask位|命令|原始返回数据|响应长度|
|---|---|---|---|
|0|30|carry signed32 + value unsigned16，大端，需已校准|8|
|1|33|接收脉冲signed32，大端|6|
|2|39|角度误差signed16，大端，65536计数/圈|4|
|3|3A|1使能，2失能|3|
|4|3E|1保护，2未保护|3|

所有请求3字节：[地址,命令,地址+命令的低8bit]；应答：[地址,数据,地址+所有数据的低8bit]，UART LSB先传，数据大端。没有应答命令码、事务号、通用帧头/帧尾。36不在本地手册5.1表内，不纳入；3D是解除保护，不纳入；CR_UART章节运动和使能命令均不发送。

手册p11-13提供协议及实例；本地firmware.txt没有可用固件说明正文；[V1.1发布说明](https://github.com/makerbase-mks/MKS-SERVO42C/releases/tag/MKS-SERVO42C-V1.1)的收发校验、F3串口使能和旧目标回跳描述仅是发布声明，不是实物固件观测。STP并发查询、失能时状态语义、实际字节序/应答长度和转换模块行为仍待实测。手册与发布说明提到的36差异已保留，未据此扩展指令。

## 模块接口和选择轮询内容

顶层`rtl/rs485_master.v`，子模块UART TX/RX和record_fifo均为Verilog2005。

|接口|语义|
|---|---|
|clk/rst_n|100MHz同步域，复位取消事务、DE=0、TX=1、清FIFO/统计，外部时间不重置|
|enable|允许新事务；撤销后已有事务含有界重试仍结束|
|query_mask[4:0]|低到高30/33/39/3A/3E；31五项，9=30+3A，16仅3E，0暂停；下一事务生效，在途长度/命令固定|
|time_us[63:0]|来自系统1MHz统一计数的同域快照输入，unsigned64|
|rx / tx / de|半双工三信号，DE高发送，低接收|
|record_valid/data[255:0]/ready|队首整记录；posedge上valid&&ready消费；data在valid=0无效|
|fifo_level / dropped|队列条数/满时丢新整记录的饱和计数|
|accepted / errors / ignored_rx|有效应答数/异常尝试数/隔离或空闲中收到的丢弃字节及帧错误数；均32bit饱和|
|busy|PRE/SEND/HOLD/TURN/RECEIVE/EMIT为1；IDLE/QUIET为0（QUIET可能在等重试）|

按每地址启用查询从低位到高位轮询，再递增地址。少选项目缩短一轮请求数，提高每项更新率；不自动改变换向或迟到隔离时间。正式115200仿真仅选30时，相邻请求起点1,099,062拍=10.99062ms；三地址一轮约32.97ms/30.33Hz。该数值含模拟从机20us响应延迟和8字节应答，不是实物测量；五项全开约160ms一轮（响应长度不同），故障/重试/噪声延长。

TX done在完整最后停止位结束后产生，随后满足POST_CYCLES才释放DE。正式profile仿真测得DE上升到释放28,046拍，最后停止位末端到释放1,002拍，满足10us保持；释放之后再屏蔽10us。TX/换向期间RX解码器清空，隔离期间字节被丢弃计数。安静计时遇同步低电平或RX事件重启，最多20ms产生BUS_BUSY跳槽；一台无响应最多两次尝试，不无限阻塞其他节点。

## 记录与FIFO语义

|bit范围|字段|
|---|---|
|255:248|VERSION=1|
|247:240 / 239:232|请求地址 / 查询命令|
|231:224 / 223:216 / 215:208|STATUS / ATTEMPT / LENGTH|
|207:176|SEQUENCE|
|175:112 / 111:48|REQUEST_US / EVENT_US|
|47:0|右对齐原始大端PAYLOAD|

STATUS=0唯一代表数据有效；1校验、2串口帧、3超时、4截断、5错误地址、6总线忙。异常LENGTH/PAYLOAD=0，不泄漏部分数据。初次DE上升锁存request_us/分配sequence，重试保留二者，attempt从0到1。有效event_us在最终校验字节停止位中心检查经过同步/寄存后通过的拍锁存；错误在判定拍锁存。BUS_BUSY无发包的新槽request_us=event_us；重试BUS_BUSY保留原请求时间/序号。sequence模32递增，使用系统epoch、请求时间和序号共同识别；模块复位后消费者必须取消旧在途关联。

完整记录一次push。满且同拍无pop则丢弃新整记录、dropped加1；满且同拍pop可以整记录交换。队首及未消费记录不覆盖，ready不阻塞轮询；accepted/errors即使记录因满丢弃仍统计。不会将驱动器串口状态作为实时脉冲反馈或最终急停输入。

**应答关联限制：**线上没有事务号/命令码，同地址同长度的无限迟到或重复帧若进入新接收窗口，无法严格区分。10ms隔离能处理本批模拟的迟到/重复，不是数学上的任意延迟隔离证明；实际驱动必须满足单请求单应答和有界迟到假设，实测最大值后才能提高速率。CHECKSUM-8有碰撞，不能声称拒绝所有噪声。

## 仿真与TD证据

`evidence/sim_release/`：种子20261013，self-checking测试与行为从机，非零退出失败。覆盖三地址五种查询、全部31个非零mask和全零暂停、在途mask变化、校验错误、UART framing、无响应/单节点故障、有界重试、错地址、迟到/重复、截断、回显、短假起始位、持续总线噪声、FIFO满/消费/同拍交换、非2幂FIFO环绕/计数饱和、各事务状态复位。独立持续STP与参考逐拍相等，71,764次翻转；这是隔离RTL仿真证据，**不是实际驱动在STP时查询的验收**。另有正式100MHz/115200线级帧和DE时间验证。

`evidence/FAILURES.md`及各r1/r2/r3/最终日志记录失败与修正，Windows沙箱内Icarus访问异常保留；不自动重试或跳过失败。最终仿真在获自动审批后的本地非沙箱进程运行，不访问板卡。

TD 2026.1 SP2/build6.2.2.200067，DR1M90GEG400参考speed2，10ns独立Tcl工程，已综合、place、route：

|阶段|setup WNS(ns)|hold WNS(ns)|
|---|---|---|
|gate|+3.374|0.000|
|place|+5.226|0.000|
|route|+3.575|+0.030|

最终总资源（含输入/输出scan观测封装）：1180 LUT6、1383寄存器、1326slice、120 DRAM LUT、0 ERAM/DSP/PLL；核心层级925 seq、488 logic LUT、360 ripple、120 DRAM LUT（TD分类不能简单加总为LUT6）。详细资源与setup/hold路径见`evidence/td/route.area`、`route.timing`及summary；源码哈希必须与identity一致。

诊断：STA coverage89.46%，无未驱动时钟/无组合环/无非法约束；OOC有4个输入及3个输出未设外部delay，SYN-6021指出8个IO未指定球位，TD自动位置仅用于OOC实现；无bitgen操作。check_timing有1个工具物理LSLICE的unused ofb dummy节点，SYN-5025为统一阶段undriven默认置零警告，route日志有观测scan shifter的SLATR-1038属性诊断；报告完整保留，不把这些称为板级零诊断验收。route_status检查执行并保留在run.log。外部IO、电气、恢复/去除、CDC亚稳态与系统集成时序未由这次OOC证明，后续必须在真实顶层重新约束/验证。

## 复现

在dev目录、Python3.10、Icarus12.0 devel和上述TD位于PATH时：

```powershell
python pl_rs485/tools/generate.py
python pl_rs485/tests/run_sim.py --tag release --seed 20261013
python pl_rs485/build_td.py
python pl_rs485/tools/source_provenance.py
python pl_rs485/tools/freeze_identity.py --simulation sim_release
```

仿真可加`--wave`生成本地VCD（忽略入Git）；失败日志不覆盖不同tag。Icarus在当前Windows沙箱内可能access violation，需在可运行本地工具的终端复现同一命令；不要将崩溃视作测试通过。build_td将generated include展开到独立build/td快照，生成10ns SDC和Tcl，不读取/修改运动工程。数据库在忽略入Git的build目录，文本证据入Git。freeze_identity检查生成文件不变、仿真与TD源码哈希一致后写固定身份；协议修改必须先更新schema/契约再重生成和验证。

## 后续实测清单（本批停止于独立交付）

1. 记录三驱动实际型号/硬件/固件二进制与版本，逐项核对30/33/39/3A/3E在STP模式、已校准/失能/保护状态下的帧、sum8范围、大端及原始单位；不发送清零/使能/解除保护来“帮助”测试。
2. 独立STEP持续运动下查询，测量运动边沿、驱动处理负载/丢帧/响应延迟，覆盖错误及超时；确认驱动不会因查询改变运动状态。
3. TTL↔RS485模块确定型号、3.3V兼容、自动/显式方向方式、回显路径、启动/掉电失能高阻与最大末停止位到释放时间。
4. 板载候选TX=L17/RX=N16/DE=N15由手册p21、pinlist A3:C5和底板原理图p14互证；SP3485资料为3.3V半双工，DE与低有效RE共线。实测BANK33电压和电平，核对ADC复用IO限制、J11 A/B/GND实物针序、固定R120=120Ω和总线端点/偏置，不能沿用OOC自动分配位置。
5. 示波器/逻辑分析仪测量DE提前/停止位保持/释放后接收窗口及从机最早返回，线长/负载/温度/故障下测最大迟到/重复/截断和转换模块回显时间；按结果调整隔离/超时参数，确认当前10ms假设。
6. 消费端整记录丢弃统计/统一时间CDC/共同reset和epoch告知，后续再设计GP/共享DMA/DDR遥测；与运动工程集成及真实顶层setup/hold另立任务，最终急停仍由外部失能链路完成。
