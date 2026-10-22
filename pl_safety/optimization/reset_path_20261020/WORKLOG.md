# 2026-10-20 复位负载与长控制路径专项

用户授权：尽可能减少异步复位，同时设法消除长路径，执行完整综合布局布线。
开始提交07745a8，原分支不切换；AGENT.md、.gitignore、BACKUP.md、两份485生成器及
既有未跟踪文件属于原工作区，保持不动。原候选16无完成的place/route/summary，
只读核对无存活TD/Questa；不把其门级结果当作最终物理时序。

## 第一候选 reset_path17

- 仅修改motion_planner、motion_service、safety_regs、safety_interlock_regs四份手写RTL。
- 规划器2461bit数据不再复位，也不再被cancel门控；原state/error/basic_ok异步复位保留。
  每个数据依赖在所属请求内写后才读；取消边沿允许无效数据推测更新，但立即失效state，
  原6/71拍规划延迟、背压和新请求初始化保持。取消不允许旧计划重新有效。
- 三个完整原子快照共5120bit不清数据；原valid/非零snapshot ID异步复位并掩蔽读出。
  reset后公开读仍为0；捕获沿、重复ID、背压及读取内容不变。不是逐行捕获或缩减容量。
- command_busy覆盖execute/dispatch/request脉冲的全部所有权周期，删除空闲fence内的
  重复脉冲判断，避免它们经合法RUN关闭、monitoring、超时和停止控制再反馈到执行器。
- 源码层面移除7581bit异步清零，不等于实际映射FF/物理复位负载；后者用TD核实。
- 保留启动/整域复位、外部复位同步释放、安全/执行器输出、有效位、session/generation
  和厂商IP复位。没有将异步GPIO改成直接采样，没有增加安全停止拍或放宽约束。
- 内部可变内容：无效plan_data、物理快照存储在复位后允许X/旧值；所有有效输出、
  命令、状态和公开零值语义保持。正常有效接口周期变化为0。

## 自检和工具异常记录

- regressions_reset17_r1：沙箱内Icarus编译进程0xC0000005，无诊断，不能算功能失败或通过。
  正常本机权限重新运行reset17_r2，33项原回归通过；保留r1。
- equivalence_r1：工具把注释的module识别为模块名，参考模块重命名不完整；修正解析，保留失败。
- equivalence_r2：规划器26547拍、服务66799拍、寄存器257拍逐拍差分通过。
- equivalence_r3：新增快照全word测试的期望值错误；既有read任务会在背压期间修改live低字。
  改为捕获前保存完整live作为oracle，不修改产品RTL、既有断言或跳过检查。
- equivalence_r4：规划器26547拍（78个阶段短复位）、服务66799拍、寄存器10409拍通过；
  包括8次epoch复位、所有96个快照word初始化掩蔽/原子捕获/长R背压。
- interlock_suite_reset17_r1：375项通过，含336个停止相位及同拍碰撞。
- verify_interlock.py：3170个旧schema叶值、3898个旧生成数值及新profile常量核对通过。
- reset_baseline_gate_r1：TD脚本参数反斜线被Tcl解释，未执行审计；改为as_posix路径，保留失败。
- reset_baseline_gate_r2：16线程只读审计通过。37381个AL_MAP_SEQ中26100个有实际
  SIG/INV异步SR连接；仅SRMODE=ASYNC但SRMUX=0的8746个不计入负载。其余FF类型/PAD
  不混入该子集；综合总Slice FF为37386，不能把两种口径混同。

## 进行中的验证

实际完整native PS、安全/GPIO、RS485、原厂GP转换器、双DMA/HP0/HP1顶层reset_path17，
DR1M90GEG400/reference speed2、原10ns约束；显式16线程并读回。优化阶段沿用额外
1.25ns setup预算，最终必须清除预算、重载原约束后独立报告；不以中间预算slack验收。
真实原厂IP三个场景通过real_checks.py串行执行，Questa唯一许可证不并发。
当前尚无最终资源、route时序和物理/CDC审计结论，不能标为时序通过或发布通过。

不计算日志、中间DB或整棵目录哈希；原失败/中断及工具日志保留，不打包规避限制。
SYN-5066、实体输入/同步器MTBF、电气/外部时序、机械HOME/恢复、BSP/DDR/板测门禁保留。

## 综合反馈及后续候选（尚无最终route结论）

- reset_path17实际gate：LUT6等效29459→29122，Slice FF37386→36963，ERAM58→69，DSP6。
  AL_MAP_SEQ实际有连接的异步SR 26100→21483（减少4617）。gate setup -2.507→-2.311ns。
  这些是综合映射结果，不是最终Slice或route收益。
- 新增11个ERAM位于原raw_fifo，原53个DRAM LUT被替代；实际wrapper仍FIFO64×421bit、
  PLAN_DEPTH8、START_MIN32、原实际GPIO/驱动参数。ram17_gate_r1保留全部11个实际单元
  属性及连接；WRITEMODE_A/B=NORMAL，RSTAMUX/RSTBMUX=0。未把ASYNC_RESET_RELEASE默认属性
  误计为有实际复位负载；没有通过缩容量达成映射。
- reset_path17最差gate转到reset_count经OFF资格、monitoring、超时和plan_fifo控制，11级。
- reset_path18增加1bit off_request_q，使用原AH/WH/BVALID/AW/W预译码及next_reset的精确
  D值，当前拍严格等于原本地OFF谓词；当前interlock_idle仍即时fence。OFF/fire和超时
  检测不延迟，不预测错误地址/数据或放宽合法条件。
- off_candidate_r1在原416项GP检查及全部已连接输出的差分基础上共4780拍通过。
  off_candidate_r2新增65536组当前状态归纳起点，真实RTL执行下一拍，无运行后修补，
  共70317拍通过；覆盖独立AW/W、B背压、reset_count和LOCAL_RESET优先级。
- 候选18的375项安全suite及受影响原GP三项回归通过。候选17、18的三个真实原厂IP
  protection/watchdog/feedback_timeout场景均全部通过；各自独立tag及源副本保留。
- 候选18gate setup -2.764ns，最差home_owner_q→安全停止→receiver abort/error→executor
  state，11级，max fanout1026；不能因增加缓存宣称已经改善最终时序。
- reset_path19增加私有停止/失能/HOME enable的精确Shannon分支。私有abort=1时原RX错误
  必定为0，因此直接选择同一停止谓词，避免经过接收器再返回执行器。新增周期/FF为0。
  stop_candidate_r1的65536种布尔组合全等价；stop_equivalence_r1/r2各66799拍服务全输出
  差分及原151597项断言通过。r2使用最终产品源码，移除两条已无使用者的旧中间线。
- 首次stop_equivalence启动被自动权限审批超时拒绝，进程未启动；按工具规则仅重试
  一次成功。不是RTL测试失败或安全性判定；所有现有TD/Questa工作未受影响。
- 候选19恢复GP源文件原Git LF行尾，只改换行格式；候选18历史编译副本保持原CRLF，
  不修改旧证据冒充新身份。最终候选需重新做当前源码/TD/真实IP编译副本逐字节核对。
- 当前仅产品5份RTL变更；所有生成物保持原字节，generate_top --check通过。
  未触及所有者AGENT.md及其他并发修改。

## 映射功能门禁拒绝候选17～19，候选20修复

ram_model_r1使用未编辑的厂商DR1_PHY_ERAM/GSR模型及真实完整顶层导出参数。
NORMAL模式同地址读写实际返回新数据（8000000000），独立旧队头oracle期望1234500000。
Questa遇到fatal仍返回0，但runner缺失PASS标记而正确拒绝；后续同时显式检查Fatal/Error。
这是实际映射兼容性失败，不能用前面RTL/真实DMA模型通过覆盖它。旧三份候选不交付为通过。
其RAM端口直接连规划器捕获数据，没有旧队头旁路。保留原FAIL及54MB临时功能网表，
不计算其哈希、不打包或提交该中间网表。

仅停止命令行精确匹配本任务reset_path17/18/19/run.tcl的TD进程12984/22612/18016。
各build/summary.json为失败，额外*_interruption.json写明主动停止原因；原日志/DB不删除。
没有把停止前place估计或额外预算slack当最终结果。

候选20在motion_fifo新增默认0的SPARE_SLOT内部参数，仅continuous_motion原始FIFO启用1。
公开容量仍DEPTH=64、421bit/条；物理数组65槽，指针mod65，count仍限制64。
距离不变量(wr-rd) mod65=count，非空时读写指针不同，因此任何有效pop/push均无同址冲突。
无新增接口周期，准备队列8条不变；不依赖修改厂商NORMAL模式或受保护模型。
增加物理421bit和两个指针位，实际ERAM/FF代价待新映射报告；保留默认旧FIFO实例行为。
新增源码仿真断言检查距离、范围、冲突，不修改或放宽既有断言。

- spare_fifo_r1：原独立FIFO模型/断言在DEPTH=2/3/7/8/64/65均通过，覆盖满pop/push、
  长背压、flush、回绕及2000次随机组合；64条用例9209项，65条9231项。
- spare_equivalence_r1：整个旧连续运动内核逐拍等价993拍，原断言保留。
- spare_service_r1：整个旧服务逐拍等价66799拍，原151597项断言保留。
- spare_ram_model_r1：同一未修改厂商模型/NORMAL参数、真实新FIFO指针和握手，5201次
  检查通过；满64条同拍pop/push520次、单条刷新396次，同地址冲突0，含复位/flush。
  此阶段参数来自17的相同RAM模式，仅为修复方案验证；最终必须用20实际导出参数再绑定。
- reset_path20重新跑完整顶层，原器件/参考speed2/100MHz及IO/驱动参数不变、16线程。
  reset20_r1的375项suite、33项原回归及real20_r1三个串行真实IP场景重新执行。

最新源码共7份手写RTL改变：原4份复位/快照、GP的OFF投影、motion_fifo和continuous_motion；
新增控制FF为OFF投影1bit及指针2bit，后两者以实际映射/参数为准。新增原始存储不复位。
尚未得到最终route WNS/hold、Slice及CDC/物理报告，任务仍未完成，不能宣布通过或可部署。

## 候选20映射检查及执行器隔离候选

- reset20_r1：375项安全/HOME及33项原回归均通过；real20_r1三个串行真实GP/双DMA
  系统场景（protection/watchdog/feedback_timeout）均通过。
- reset20_gate_r1：实际连接异步SR负载21486，对照gate16的26100减少4614。
  LUT6等效29198、Slice FF36963另PAD9、ERAM69/DSP6/IO17；对照gate16分别−261、
  −423、+11、0、0。以上为gate，不冒充最终Slice/route。
- spare_ram20_model_r1：绑定20实际导出的原厂ERAM参数，未修改厂商模型，5201次检查
  通过；满64条同拍pop/push520次、单条刷新396次、同址0，逻辑容量64保持。
- executor_candidate_r1生成时赋值站点计数预期29、实际27，生成器自身断言停止，未生成
  候选源、未集成。核对12个reset、3个RUN、12个commit站点后，r2严格断言27。
- executor_candidate_r2仍为隔离源码：保留唯一执行器控制和所有公开输出的原异步复位、
  停止及生命周期；1032bit私有计划数据无reset，不再受安全/commit宽CE门控制，空闲及
  原边界可作推测写入，只有原控制过程可授予RUN。无新增接口周期/停止延迟。
- executor_equivalence_r1：原执行器全部已接输出逐拍等价325拍；executor_service_r1：
  完整服务与07745a8逐拍66799拍等价，原断言保留。
- executor_suite_r1：仅替换编译源路径，原375项安全/HOME测试及相位、优先级、步数
  断言完整保留，全部通过。产品执行器尚未替换。
- executor_stress首次启动因自动审批超时而未启动，工具明确允许仅重试一次，重试已
  成功启动；结果待看。没有以审批超时推断RTL不安全，也没有隐去失败。
- reset_path20完整TD仍处于物理优化；尚无最终route验收结果。
