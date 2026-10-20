# SAF2 / R5S2合并任务交接（时序优化进行中）

最新运行状态（2026-10-20 13:43，Asia/Taipei）：用户要求重启布局布线。
从原候选16 gate.db恢复，没有改RTL、原约束、受保护IP或重新跑已通过的三个真实场景；
当前源码/头文件及原工程逐字节核对通过。发现直接分离的恢复进程仍附于受管作业后，
注册零触发器的一次性Windows按需任务Codex-PL16-PnR-20261020-R2，成功注册后才
停止本任务旧恢复进程，保留launch_r2及resume_pnr_r1日志/失败摘要并记明主动迁移原因。
当前由任务服务启动pythonw驱动PID15336（父svchost.exe），已确认实际place阶段及
16线程读回，任务状态Running，触发器数0；不会按周期/开机自动重跑，结束后自行删定义。
当前日志build/interlock_route16/resume_pnr_r2.log，摘要resume_pnr_r2_summary.json；
总体结果optimization/interlock_candidate16/launch_r3/workflow_result.json。
status.ps1已通过active_run.json指向本轮，保留launch_r1的三个真实IP已通过结果。
用户可用同一status.ps1查询；按其要求确认启动后结束本轮，等待完成通知再审计/分析。
下面旧PID/原启动状态为历史；不能据原run.log无摘要判断当前恢复任务是否结束。

2026-10-20 10:30从中断恢复：确认候选15 TD及Questa均已退出，TD停在preplace，
仅有gate -2.964/0ns，没有完成place/route或summary；看门狗场景亦没有结果，不能计通过。
当前产品源码已推进候选16：在候选15上新增active/off两个当前资格投影FF，使用源端
精确下一reset/config-change/config-apply及完整下一代际计算，而不是延迟旧资格。
目标切断reset_count→restart→反馈超时→停止控制11级路径；原检测/禁止STEP沿不变。
隔离全624bit输出/资格关系16384次比较、实际源预测3936453拍及配置应用257拍通过，
原GP e2e302项和寄存器91项全部保留通过。375项联锁集成回归及33项原回归全部通过。
生成顶层及3170/3898旧ABI检查通过；新增声明状态2472bit，实际FF代价待物理报告。
用户要求：确认布局布线真正开始后交付检查方法并结束本轮，不等待route完成。
已于2026-10-20 10:50（Asia/Taipei）通过Start-Process隐藏窗口启动独立后台驱动PID2764，
启动时间身份见optimization/interlock_candidate16/launch_r1/process.json。TD与三个串行
真实IP场景并行工作，Questa场景之间不并发。10:59已确认日志start command "place"及
PrePlace Optimize Design，16线程读回、驱动和TD独立存活；当前处于实际place流程，
尚无最终place/route报告。gate为-2.507/0ns，不作为最终验收。
真实保护场景已通过30112867检查/HP0读18/HP1写8/双端同拍接受2，当前源码/编译副本/
TD副本、受保护IP和原约束字节核对通过（interlock_source_identity16_protection）。
状态方法见同目录BACKGROUND_README.md及status.ps1。按用户要求本轮在此结束，后台
继续运行；之后不自动发送消息或继续审计，等用户通知。检查summary.passed与timing_pass
必须分开；launch_r1/workflow_result.json结束后记录TD和三个真实场景总体状态，
仍不构成资源/最终物理数据库审计、Git提交或发布签核完成。

以下候选15检查点为中断前历史状态，运行状态已由上段核实替代：

2026-10-20当前工作：候选15已接入完整32位下一值相等关系缓存（1bit）、LOCAL_RESET
预译码（2bit）和transaction原EMIT沿保护/轴译码（6bit）。不增加反馈检测/禁止STEP
延迟，无PS窗口/格式/针脚变化。源码9个明确路径的候选13备份保留在
optimization/interlock_candidate15/before。新增声明状态2470bit，实际成本待新报告。
隔离源EMIT 67360组差分及全624bit监测输出16384次比较通过，375项联锁集成回归
通过；旧33项回归及三个真实受保护IP场景串行运行中。完整实际顶层interlock_route15
已启动16线程流程。生成/ABI检查3170旧schema叶值和3898旧数值定义均不变。
当前不能把候选13失败报告或候选14独立模型当作候选15时序通过证据。
候选15跨模块原因、位置和验证边界见INTERLOCK_TIMING_CHANGES.md。

以下是候选13已完成的历史检查点，后续当前状态以本段为起点：

2026-10-19，Asia/Taipei。用户已恢复任务并授权必要的缓存FF/长路径/高扇出优化。
当前源码为candidate13，新增同拍HOME owner缓存，完整374项功能及20480项owner归纳关系
自检通过；包含固定保护译码68728项差分及79项监测行为。真实候选13保护、WD超时和
单轴反馈超时三个场景均通过，全部HP0读18/HP1写8/实际重叠18。
candidate13已从同一place.db完成16线程恢复布线，保留原中断run.log及独立r1日志。
最终原100MHz gate -2.820/0ns、place +1.193/0ns、route **-2.173/+0.020ns**。
布线流程完成但时序未达标；setup相对原基线+1.133ns下降3.306ns。
LUT6等效29873（+1688）、Slice37984（+2065）、Slice FF37863（+1460），另PAD FF9；
ERAM58、DSP6、IO17和各时钟资源数量不变。physical/pins/cdc审计全部通过、16线程，
原约束和route.db逐字节不变，无新增告警代码；独立物理资格仍开放。
当前实际最差路径为push_data[30]的payload合法性/保护停止路径到a1_dir CE，10级，
cell2.173ns/net9.749ns；不能仅用门级generation比较路径推断下一步一定达标。
完整中文汇总见optimization/interlock_candidate13/ROUND_REPORT_20261019.md，
机器比较见evidence/interlock_comparison_route13_resumed_r1/comparison.json。
跨模块变更原因与位置见INTERLOCK_TIMING_CHANGES.md。
candidate11/12构建已主动中断并保留独立副本及原因；candidate14仍仅为独立原型。
下列暂停检查点保留为历史，不代表当前运行状态。
本文件当前不表示功能、时序或发布签核完成。生产HOME PROFILE0仍禁启。

## 暂停检查点与下次起点

完整实际顶层interlock_route10已完成，16线程；恢复原100MHz约束后的gate setup/hold
为-2.262/0ns，place为+1.158/0ns，route为-1.960/+0.020ns。工具流程完成，但
setup不满足原约束及严格大于1ns目标。见build/interlock_route10/summary.json及
最终route.timing；不能以功能通过或place估计代替最终时序验收。

真实并发补测interlock_real_concurrent10通过30112868项检查，11采集事件，HP0读18、
HP1写8；HP1背压期间实际接受18个HP0读beat。独立WD/反馈超时证据见下表。

下次先定位route最差controller/state及edge_age经空闲资格、有效RUN关闭、restart到
DIR CE的组合路径（最差10级，cell 2.409ns/net 9.286ns）。候选11拟把pulse_safe纳入
既有寄存空闲资格，并把采集器实际RUN与合法关闭提交事件分开，避免即时宽组合反馈；
必须保持关闭当拍抑制新反馈超时、在途保护有效、原故障检测/禁止STEP边沿不变，并
补充边界自检后重新跑功能、真实系统和完整时序。候选11补丁因匹配失败未应用，
已核对相关源码均未改变；optimization/interlock_candidate11/before仅保存候选10
的13个明确路径备份，不是已实现的新版本。

尚未完成：时序修正、最终资源增量/高扇出/CDC及数据库审计、最终比较报告、最小
关键交付物哈希和本任务Git提交。部分任务文件已暂存，后续修改仍未暂存；保留现状。
用户AGENT.md、其他任务文件和全部失败/中断日志均保留；未部署、未上板。

唯一规范为pl_interface/schema.json的interlock_profiles.gp_safety_interlock_v2；
行为及恢复流程见INTERLOCK_CONTRACT.md。旧schema的3170个叶值、旧生成物3898个
数值定义已逐项验证不变；生成常量新增SAF2/R5S2能力，未重新解释旧能力位。

|用户已冻结项|最终决定|
|---|---|
|485反馈期限|us，三轴共用阈值独立计时；1,000,000～3,000,000，默认2,000,000|
|PS心跳|健康控制循环正常每500,000us；超时范围及默认同上|
|身份|PL分配非零递增u64 owner，严格递增非零u64 sequence；同epoch不回绕复用|
|故障输出与位置|检测当拍禁止新STEP、撤销三轴valid；脉宽/DIR保持排空后原OFF延迟失能；保留已输出计数|
|恢复|排除原因，停稳失能，本轮全轴健康、新owner首次报活、显式清错；完整HOME成功恢复valid|
|到期边界|age>=期限，到期优先于同拍正常应答或心跳；保护1始终触发|
|资格|本轮全部受监测轴健康且首次心跳后允许HOME/真实使能；RUN关闭不具资格|
|衔接|HOME/暂停/空闲owner持续监测；STOP/DMA-only reset/清IRQ不解除；服务重启不接管旧owner|
|首因|原因逐轴OR锁存，首时保持；首次同拍急停>限位>保护>反馈超时>PS超时|

安全GP扩展复用现有AXI端点；485仍只有采集器RUN一份有效状态。实际事务提交直接
旁路到安全解析，与FIFO、PS读取、DDR完成解耦。执行器仍唯一拥有STEP/DIR/EN/位置。
配置多字shadow捕获后下一拍原子应用；CONFIG_ACCEPTED与CONFIG_APPLIED分别可读，
pending阻止新HOME/使能。空闲配置资格可在排空后保守等待一拍；故障检测、STEP禁止
及原急停/限位/STOP路径没有增加流水拍。

PS接入仅交付software/interlock.h/c、example.c及模型测试；串口/Web的唯一执行后端
在关键控制循环健康检查通过后报活，不得独立线程/内核定时器/硬件无条件续命。
PL报活不能证明软件所有逻辑正确；PL drained不能证明DMA/DDR静止，沿用quarantine。

## 验证记录与未完成门禁

新增模块、AXI乱序/背压、运动停止相位、旧profile、软件模型和真实双DMA系统的证据
均使用独立tag保留。candidate11完整自检interlock_suite_route11_complete共374项全过，
其中监测器79项、GP差分416项；新增逐拍排空资格断言通过。原33项回归
interlock_regressions_route11_final全过；真实并发保护interlock_real_route11通过
30112868项，HP0读18/HP1写8/重叠18，interlock_source_identity11逐字源码核对通过。
独立超时及完整TD仍在运行；下列保留route10检查点的已完成功能检查。完整资源/时序和
数据库审计尚未完成，功能通过不表示发布签核：

|证据目录（pl_safety/evidence/）|实际结果|
|---|---|
|interlock_suite_route10_complete|374项全过：3项模块/端点（含416项GP检查）、32旧安全模式、14×24停止相位、3项精确同拍冲突|
|interlock_regressions_route10_final|33项原运动/接收/GP/RS485/缓存/遥测回归全过|
|interlock_real_route10|真实原厂受保护GP转换器和两DMA，30112877检查，11采集事件，HP0读18、HP1写8|
|interlock_real_watchdog10b|独立WD超时：28558287检查，12实际采集事件，反馈健康，仅WD原因；非生产共同epoch跳转|
|interlock_real_feedback10|独立反馈超时：34335647检查，13实际采集事件，其他轴/心跳健康，仅A0反馈超时；非生产共同epoch跳转|
|interlock_owner_exhaustion10|68项模块检查，含u64所有者/序号耗尽、不回绕复用及重放拒绝|
|interlock_source_identity10|当前全部实际编译RTL/头与真实系统副本逐字相同；授权RTL/头与完整TD工程逐字相同；真实系统/TD/原厂IP逐字一致；约束未替换|
|interlock_interlock_inputs_route7_final|解析资格基线4204检查全过（只证明数字解析）|
|interlock_software_pipeline6|严格C11软件模型通过；调用示例编译通过|

真实系统含坏校验重试、未知保护枚举、未消费的诊断FIFO满/丢弃、HP1背压时实际保护
响应和检测当拍禁止STEP、MOT2经HP0与遥测经HP1完整传输。仿真62项宽度警告来自
未修改的原厂受保护IP内部；未修改/替换IP或据此关闭SYN-5066。
完整资源和时序比较待本轮最终构建完成后填入。
工具中断与失败保留，未降低原断言；Questa受保护IP仿真串行运行。

- route5：中断于物理优化；gate setup -3.857ns，不能作为最终时序通过。
- route6：寄存化空闲许可的即时fence误引用home_enable/private_disable，综合发现组合环。
  已保留日志并停止，不接受工具切环后的STA；route7移除这两条组合反馈，重新完整构建。
- route7：无组合环，gate setup -3.697ns/hold0；在布局优化中停止，以纳入最终安全配置
  RUN=0门，避免提交与新查询同拍。监测器与采集器已共享公共复位，新增旁路只导出实际
  local reset hold，删除重复公共复位经过restart进入停机组合锥的路径；不延后本地复位资格。
  route8重新完整构建，未使用route7中间估计冒充最终结果。
- route8：gate setup -3.063ns/hold0；安全txn比较通过HOME request进入restart仍形成
  11级长路径。在布局中停止；route9用1bit HOME opcode预译码与已捕获SUBMIT地址作
  保守配置门，正式HOME/CLEAR校验及停止沿不变，重跑完整顶层。
- route9：功能和真实IP通过，gate setup -3.401ns/hold0；最差路径转至RUN写译码，
  布局中停止保留。route10将RUN地址与精确字节关闭条件预译码到原AW/W捕获沿，
  原fire生效沿不变；416项GP差分检查已通过，完整布局布线仍在运行。
- 最终要求：同完整native PS/真实受保护GP转换器、两DMA、HP0/HP1顶层，100MHz原约束，
  route setup严格>1ns、hold>=0；综合/布局/布线/数据库审计均显式16线程并实际读回。

独立未关闭门禁：原厂S2MM SYN-5066诊断（a222f0d实验未替换产品IP）、安全输入针脚/
电气/同步器资格及IO delay、0x3E实体保护语义/STP期间查询/换向/迟到帧、机械停止/
HOME/复电、BSP DMA/DDR静止及板级验证。数字功能与STA通过不授权上板。
未操作COM4、SD/eMMC/QSPI或板卡，未生成部署镜像，未自动REBASE/ENABLE/START。

AGENT.md与原有两个RS485生成器未提交修改、Wi-Fi/BSP、log/和历史工具日志保持原样。
新runner不计算日志/中间DB/目录哈希；最终只允许最小关键交付与直接源码哈希。
