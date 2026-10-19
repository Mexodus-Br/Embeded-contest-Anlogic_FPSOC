# 485 / PS心跳合并任务：实现前评审

> 历史准备记录：下文“待确认”描述的是实现前状态。用户已在本会话确认全部行为，
> 最终规则见INTERLOCK_CONTRACT.md；500ms报活、两类期限1～3s/默认2s、故障当拍
> 撤销三轴valid、原OFF延迟失能、完整HOME恢复。实现/验证进度见INTERLOCK_HANDOFF.md。

2026-10-18，Asia/Taipei。状态：待用户确认行为。本文是接口盘点与测试准备，
不是冻结规范、完成交接或发布签核。未增加生产RTL、未选择生产参数、未修改旧ABI。
已有未提交的INTERLOCK_PLAN.md、preflight脚本及两个RS485生成器修改保留原样。

## 已核实基线

HEAD为249f3c3；实现基线eccab43，上一轮封存88af6ee。较早的
SAFETY_HANDOFF.md暂停条目不代表当前最终时序状态；以
optimization/timing_20261017/HANDOFF.md、WORKLOG.md及
comparison_closure_cofactor_route5.json为准。

新preflight证据interlock_preflight_20261018_r4.json通过：3170个旧schema叶值保持，
12份关键RTL与最终时序源码一致，且与实际完整工程缓存逐字比较通过（仅允许
CRLF/LF及已知生成头展开）。旧GP/遥测C/Verilog共四份头文件数值逐项匹配。
未执行历史全量哈希封存脚本，未计算文件哈希。

原完整顶层system_wrapper及safety_rs485_gp_ps_top链使用真实PS、GP0、HP0/HP1、
原厂受保护转换器与两个DMA，100MHz、参考speed2。route setup/hold为
+1.133/+0.020ns，gate -1.439/0.000ns，place +2.786/0.000ns。
LUT6等效28185、Slice35919、Slice FF36403另PAD FF9、ERAM58、DSP6、IO17、
GCLK1、SCLK6，其他已报告时钟资源为0。16线程读回已核实。
这些是本任务前的参考值，不能作为新增联锁的功能或时序结果。
a222f0d实验未替换产品IP，SYN-5066仍未关闭。

## 必须由用户决定

下表全部待确认。没有回复、仿真通过、经过时间或此前建议均不构成确认。

|项|待确认内容|当前建议（未批准）|
|---|---|---|
|D1|485期限单位、具体值、默认、最小/最大，统一或逐轴阈值|复用us；三轴独立计时，共用一个阈值；无批准值时禁止生产启动|
|D2|PS正常报活周期、超时默认及最小/最大|由用户给定，不从Linux平均调度或仿真夹具推导|
|D3|所有者、序号及重启交接|PL发放非零递增u64所有者；u64序号严格递增，两者同epoch均不回绕复用|
|D4|保护/反馈超时/PS超时各自的EN、valid、清错条件及强制HOME|485两类撤销三轴valid并必须HOME；PS超时保留EN/valid仍待决定；任一类中断HOME完整重做|
|D5|首次资格、轮询关闭时HOME/使能权限、到期边界和同拍优先级|全部监测轴首次健康反馈后才允许HOME/真实使能；轮询关闭禁止这两项；age>=期限且到期优先同拍报活|
|D6|HOME/暂停/空闲持有者、local reset、应用配置、服务重启|持续监测；STOP/DMA reset不解除；local reset仅停稳失能无队列/所有权且RUN=0；重置/应用撤销旧资格；重启不接管旧所有者|
|D7|逐轴多原因、首因顺序、首时与显式清错|原因OR锁存，首时不覆盖；首次同拍急停>限位>485保护>反馈超时>PS超时；清IRQ不清错|

补充需要在D4确认的细节：清错是否要求本轮全部健康0x3E、看门狗新所有者首次报活，
以及故障期间是否允许这两种资格重新建立。必须避免“必须先清错才能建资格、
必须先建资格才能清错”的恢复死锁。若EN保留，关闭/交接所有者前须允许显式DISABLE。
这不授权新485写命令或自动解除驱动保护。

现有0x3E目标周期：兼容1000000us，快采候选200000us（未实物资格确认）；
仍有最多一次重试、10ms异常隔离及500000us节点退避。期限选择需考虑整个调度，
不是任一帧10ms超时。小于2^63是u64模差数学条件，不是已批准的生产配置范围。

## 工程接入，不新增外部通路

|接入点|实际源码事实及后续必要修改|
|---|---|
|唯一轮询状态|rs485_gp_regs.run是实际唯一RUN，0x010；从桥显式导出到安全层，不在安全窗口复制可写开关|
|旧485写入口|RUN当前只检查值/局部复位；CFG_SUBMIT原子捕获五周期/掩码；LOCAL_RESET当前只检查采集器状态。新opt-in profile须增加运动空闲和联锁配置资格，并保留legacy路径原行为|
|485配置|0x040..0x050周期shadow，0x054掩码，0x05c提交；需同时审核提交和实际应用，禁止pending配置跨越使能边界绕过监测|
|安全窗口空闲|已用0x000..0x03b、0x040..0x063及快照0x200..0x2ff；0x100..0x1ff和>=0x300可扩展，尚未赋予新ABI偏移|
|能力版本|保留gp_safety_home_v1/SAF1全部值及CAPS=0x3f语义，显式新profile复用同一物理端点/IRQ7；新增常量从pl_interface/schema.json生成|
|完成事件|rs485_transaction在最后校验字节成功拍记录event_time、进入EMIT；下一沿登记push/raw，之后下游采样。completed_valid/raw是该事件旁路，不受FIFO满/消费影响；检测延迟必须按此源事件逐拍说明|
|解析资格|rs485_light_parse的enum_known可能在非法长度时仍为1，必须与well_formed/data_valid、0x3E、节点、真实提交事件、本轮generation/revision共同检查；cache读不能触发刷新|
|快速停止|从安全服务直接接原motion_service私有stop/inhibit/invalidate/disable；同时抑制HOME run/reference/complete。不能沿用stop_notify一拍通知作为唯一新故障禁止STEP路径|
|唯一执行器|原motion_executor继续拥有STEP/DIR/EN及命令位置；不增加输出与门、第二脉冲源或公共复位停机|
|AXI心跳|safety_regs.fire=held_AW && held_W && !BVALID；独立心跳commit不得经HOME mailbox busy。副作用在fire采样沿发生一次；已有未完成B响应仍会背压共享端点，不能宣称无条件无阻塞|
|空闲判断|motion_service.safety_idle包含maintenance_ok、command_busy、held AW/W和packet_busy；还须结合HOME owner、pulse_safe、EN及pending配置。它不证明DDR静止|
|取消与恢复|沿用session/FIFO/planner/held record/transport半包取消和link generation门；DMA-only reset不复位共同时间或看门狗，迟到数据不得恢复旧任务|

配置采用shadow/提交/应用，状态明确区分accepted、applied、qualified、detected、
drained及软件ack；跨32位的期限、所有者/序号不可撕裂使用。合法时钟、复位、CE、
普通数据的物理扇出须分别报告，新增状态位及实际FF代价以完整综合/布线为准。

PS唯一执行后端在关键控制循环健康检查通过后喂狗，串口/Web共用；不得由独立线程、
内核定时器或硬件无条件续命。PL报活不能证明软件所有逻辑正确。浏览器断线不直接
等同PS失联。软件交付仅接口、C调用例子和模型测试，不扩展Linux/Web部署。

## 本轮实际验证与限制

|检查|结果|
|---|---|
|基线preflight r4|通过；数值/逐字比较，无文件哈希；非新增联锁验收|
|RS485 wire与rate生成器--check|通过，使用工作区已有的只读check实现，未改动它们|
|safety generate_top.py --check|通过|
|新增tb_interlock_feedback_inputs|普通本地进程环境4204项通过；逐轴枚举、全部错误status/长度/版本/其他query、payload多余位和全部地址|
|首次Icarus沙箱执行|编译进程0xC0000005退出，空编译日志与失败JSON保留在interlock_inputs_review_20261018_1；未当作通过|
|新联锁/看门狗RTL、真实系统集成、新全顶层P&R|未实施，待行为确认；不能以解析器测试替代|

解析测试只校验现有parser提供的资格输入，未模拟UART帧、当前轮资格、联锁计时
或停止，不证明实际驱动器堵转保护。成功证据在
evidence/interlock_inputs_review_20261018_2/result.json。
复现（每次新tag）：

```powershell
python pl_safety/tests/interlock_feedback_inputs.py --tag NEW_TAG
```

实现后的阶段顺序为模块自检、全部停止相位、真实GP/双controller/HP0/HP1/UART
并发、原有回归，最后同一完整顶层原100MHz约束的资源/STA/物理审计。
Questa唯一许可证串行使用；所有新TD阶段及DB审计显式16线程并实际读回。
最终route setup严格>1ns、hold>=0；额外预算只能引导优化，必须清空/重载原约束、
核对实际有效SDC后验收。失败/中断保留，断言不降低。

旧build_td.py、regressions.py、verify_delivery.py及历史seal/identity入口有扩大
哈希范围的代码，未经专项修改不得用于新交付；不删除或改写旧证据。
最终哈希仅最小必要的最终关键交付及直接源码，不哈希日志、中间DB、全部工程输入
或打包产物。当前准备测试与预检不计算哈希。

生产PROFILE0继续禁启。板卡/COM4/存储/部署镜像未操作；SYN-5066、针脚/电气/
同步器资格、RS485实体时序和机械验证、BSP缓冲生命周期/quarantine继续独立保留。
全部行为和数值确认、功能与时序实际通过后，才提交完整任务变更；准备文件不冒充完成提交。
