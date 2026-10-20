# SAF2 / R5S2实现记录

2026-10-18，Asia/Taipei。保留全部失败/中断与历史工具日志，不覆盖旧tag。

1. 完整基线核验：HEAD249f3c3，实际优化RTL eccab43、证据封存88af6ee；
   完整顶层参考closure_cofactor_route5。a222f0d未替换产品IP，SYN-5066保持开放。
   用户AGENT.md、两个既有RS485生成器及其他任务文件保持原样。
2. 接口盘点后集中询问行为；用户确认1～3s/默认2s、500ms健康报活、u64身份/序号、
   到期优先、故障当拍撤销valid、原OFF延迟、完整HOME恢复及复位/所有者交接条件。
3. 采用独立SAF2/R5S2 profile；原窗口扩展，无新AXI从设备/外部通路。
   schema唯一生成C/Verilog定义、位表与快照；3170旧叶值及3898旧数值定义逐项保持。
4. 实际EMIT提交旁路接安全解析；每轴本轮时基，独立反馈年龄；FIFO/HP1/PS解耦。
   watchdog独立shadow/commit，不经HOME mailbox；故障直接接现有唯一执行器私有停机/
   invalidate/disable及transport取消，不增加STEP输出门或公共复位。
5. 新模块自检、实际安全AXI AW/W错开和B/R背压、自检引脚边沿oracle、恢复/迟到数据/
   多原因/回绕/旧profile回归；C模型覆盖部分写和结果未知。真实系统保留原保护IP、
   GP转换器、两个DMA、HP0/HP1，注入坏校验、未知枚举、满FIFO和HP1背压。
6. 完整顶层route5在物理优化阶段中断，gate -3.857ns；定位为planner idle经配置
   应用/restart进入执行器组合锥。安全配置改为整组捕获，下一拍应用，增加accepted/
   applied及pending状态；空闲资格保守寄存，不流水检测和STEP禁止。
7. route6新增即时fence误引用受联锁控制的home_enable/private_disable，综合发现组合环，
   停止并保留失败；route7只用寄存器中的所有权/命令/AXI状态作即时fence，重新全流程。
   后续构建runner显式拒绝TMR-2507/TMR-2509，不接受工具切环后的STA。
8. route7最终功能回归：interlock_suite_route7_final共371项全部通过（3模块/AXI/GP，
   32旧安全模式，14场景×24运动相位）；interlock_regressions_pipeline_final6
   共33项原运动/接收/RS485/缓存/遥测测试全部通过。软件模型及example.c严格C11编译通过。
   完整资源/时序、真实系统最终复跑与DB审计以INTERLOCK_HANDOFF.md最终条目为准。
9. 边界复核发现RUN仍开启时，安全配置接受可能与新查询启动同拍。安全轴/期限提交
   增加RUN=0且在途结束门，明确文档；运动系统夹具新增RUN1拒绝、RUN0仍busy拒绝、
   停轮询排空后原子配置及accepted/applied读回检查。route7布局中停止并保留。
   同时删除冗余的公共复位经collector_reset进入restart组合路径：两模块已共享rst_n，
   输出实际local-reset计数器hold；旧profile输出原样。route8完整构建/功能复跑。
10. route8 gate setup改善至-3.063ns/hold0；最差路径为安全txn[31]经HOME提交比较、
    配置空闲门、restart进入执行器，11级/FO1064。新增1bit HOME opcode预译码，
    在AW捕获SUBMIT后保守阻止配置，实际HOME/CLEAR仍完整原校验和原生效沿，
    独立STOP不受影响。端点91项检查和运动先验通过，route8布局中停止保留；
    route9完整构建、374项功能回归及真实受保护IP系统复跑。
11. route9功能374项、真实双DMA及精确源码副本核对通过；gate -3.401ns/hold0，
    路径转至485 BVALID经RUN关闭译码、restart到plan FIFO（12级/FO263）。
    将精确RUN地址和字节strobes/零值关闭条件预译码到原AW/W捕获沿，仍仅在原fire
    拍关闭监测。16种WSTRB×8类数据差分核对旧完整merge语义，416项GP检查通过。
    route9布局中停止保留；route10完整构建、374项及真实IP复跑。
12. route10 374项、真实保护事件系统、416项GP差分及实际源码/厂商IP逐字核对通过；
    gate -2.262ns/hold0，完整布局布线继续。增加真实双DMA系统的独立WD/反馈超时
    场景，明确使用非生产统一epoch时间跳转，不改产品参数或私有deadline。
    watchdog10首次只跳转GP计数器，触发原有运动ABI同步时间副本一致性断言；失败
    完整保留。watchdog10b同步注入两个既有epoch计数副本，保留原断言重新验证。

13. 2026-10-19按用户要求暂停。route10完整流程已结束，显式16线程，原100MHz约束
    下gate setup/hold -2.262/0ns、place +1.158/0ns、route -1.960/+0.020ns；
    时序失败，不能发布签核。真实并发concurrent10通过30112868项检查，HP0读18、
    HP1写8，其中18个HP0读beat与HP1背压实际重叠。独立watchdog10b通过28558287
    项、feedback10通过34335647项，均仅锁存预期超时原因；owner耗尽模块68项通过。
    最差route路径10级，经空闲资格/有效RUN/restart到DIR CE，候选11拟拆分此组合锥。
    候选11补丁匹配失败且原子未应用，已核对源码仍为candidate10；明确路径备份保存于
    optimization/interlock_candidate11/before。暂停期间不继续RTL、仿真或TD运行。
    最终时序优化、资源/CDC/高扇出数据库审计、比较报告、最小关键哈希及Git提交待续；
    已暂存和未暂存任务修改均保留，未提交、未部署或上板。

14. 2026-10-19恢复，候选11根据route10实际10级长路径作以下跨模块修改：
    - pl_motion/rtl/motion_service.v，safety_idle_q采样处：将原pulse-safe排空条件
      与full_safety_idle一起寄存，仍由即时session/命令/AXI/HOME所有权fence撤销许可。
      原因是edge_age宽比较经即时配置门绕回DIR CE；仅SAF2使用寄存许可，legacy输出不变。
    - pl_safety/rtl/safety_motion_service.v，interlock_idle及monitor连接：SAF2不再
      重复组合pulse_safe；此条件已在上述寄存资格中。增加内部collector_stop_commit。
    - pl_rs485/rtl/rs485_gp_regs.v，interlock_run输出：直接导出唯一实际RUN寄存器；
      原合法关闭fire谓词改为独立interlock_stop_commit，不再通过RUN进入restart解析。
      rs485_gp_bridge.v及generate_top.py仅传递这个内部事件，无新AXI/PS端口或存储状态。
    - pl_safety/rtl/safety_interlock.v，monitoring/feedback_seen：关闭提交当拍仍禁止
      新反馈超时、撤销资格；restart及在途保护校验只使用实际RUN。WD到期独立有效。
    不寄存故障检测/禁止STEP，不改变原ESTOP/限位/STOP边沿，不增加第二输出控制源。
    新模块79项（含关闭与到期/保护同拍）、GP全部416项及运动模式0先验通过；运动
    夹具增加每拍断言：寄存空闲许可不得早于真实pulse-safe、core idle及全部所有权释放。
    首次受限环境三项Icarus均0xC0000005崩溃，保留失败证据；沙箱外原断言重跑通过。
    interlock_suite_route11_complete完整374项全部通过（含上述79/416项），生成定义
    检查通过；3170个旧schema叶值及3898个旧数值宏保持不变。
    interlock_regressions_route11_final原33项全部通过。interlock_real_route11真实保护
    场景30112868检查通过，11事件、HP0读18/HP1写8，18个读beat与HP1背压实际重叠。
    interlock_source_identity11核对实际仿真/TD源码、头文件和原厂IP完全一致。
    独立WD/反馈超时与完整原约束TD结果待后续记录。另对route10执行只读物理/高扇出/
    CDC诊断，显式16线程、直接字节核对通过，不计算中间数据库或日志哈希。
    interlock_comparison_route10_diagnostic_r2比较显示旧候选LUT6等效+1339、Slice+1679、
    Slice FF+1430，ERAM/DSP/IO/时钟资源不增加；仅为失败候选诊断，不是最终交付时序。

15. 候选11 gate setup/hold -2.617/0ns，最差源为engine/push_data[235]，经通用
    parser的task_index编码（177负载）再译码feedback_axis，随后进入receiver abort及
    motion_service observed_end CE：11级，cell 2.783/net 9.775ns，最大扇出234。
    候选11继续独立布局布线，不能把gate估计当最终route结果。
    候选12只改pl_safety/rtl/safety_interlock.v的保护字段译码：从既有唯一生成
    rs485_defs.vh取得版本、地址、query_code(4)/query_length(4)、status，固定检查
    0x3E长度/高payload零/已知枚举，直接生成三轴onehot，去除通用task编码再解码。
    原采集器、通用rs485_light_parse及事务/retry/FIFO均未修改；无新增寄存级、状态位、
    新端口或检测拍变化。optimization/interlock_candidate12/before保存修改前两文件。
    tb_interlock.v以未修改通用解析器作差分oracle，全部256×256地址/命令组合、逐轴
    全部枚举/版本/status/长度字节及40个非法payload高位，68728项等价检查通过；
    原79项监测行为及运动模式0先验通过。interlock_suite_route12_complete完整374项
    全部通过，含全部68728项解析差分、停止相位与排空资格逐拍断言。候选11独立真实
    WD场景interlock_real_watchdog11通过28558278检查、12事件、HP0读18/HP1写8/
    实际重叠18；该证据只属于候选11。候选12真实系统与完整实际顶层结果待记录。

16. 候选12 gate setup/hold -1.964/0ns；最差路径已转为controller/state[2]经
    HOME owner/空闲资格、monitoring、receiver abort进入executor/state[2]：11级，
    cell 2.859/net 9.035ns，最大扇出790。固定保护译码已离开最差起点。
    候选13修改pl_safety/rtl/safety_controller.v的home_owner：仅SAF2使用新增1bit
    home_owner_q，直接与每个改变所有权的state赋值同拍更新（复位NEED=0、进入PRE或
    DRAIN=1、显式CLEAR进入NEED=0、FINISH进入READY=0、最后优先的DRAIN排空=0）。
    不把当前state译码延迟一拍；其他HOME内部阶段保持原所有权。legacy仍使用原表达式。
    原因是状态多位译码进入关闭提交/监测/停止组合锥；保持原停止、限位、急停与失效边沿。
    interlock_motion_fixture.py增加每拍owner与原state范围/DRAIN表达式严格等价断言。
    运动保护模式0及HOME完成精确同拍冲突模式15先验通过。新增owner projection模块
    自检穷举10个合法状态×全部11bit有效控制谓词，20480项归纳关系检查通过；仿真
    每例只预置合法state及匹配缓存，不复制下一状态实现，检查真实RTL采样后的原译码
    等价，覆盖矛盾谓词组合及最后DRAIN覆盖优先级。所有层次注入仅在该测试中。
    interlock_suite_route13_complete原374项全部通过；projection单独保留route13_owner_projection，
    后续suite将包含此新增模块，共375项。真实系统夹具也增加采样沿后所有权等价断言。
    interlock_real_route12保护30112868检查、watchdog12独立WD超时28558278检查均通过，
    两场景均HP0读18/HP1写8/实际重叠18；候选13真实保护场景已另起独立tag运行。
    interlock_source_identity12_r2逐字核对候选12实际编译与TD副本，并确认原33项回归的
    全部pl_motion/pl_rs485 DUT及包含头与候选11/12逐字相同，未复用旧SAF2功能证据。
    修改前两文件保存在
    optimization/interlock_candidate13/before。新增声明状态总计2461bit，实际映射代价待报告。
    候选11/12使用独立副本保留；完成上述定位及等价验证后，核实PID/命令行，仅停止
    本任务两个旧TD进程：11在post-pack物理优化中断，12在prepack物理优化中断。
    其summary均为passed=false，另存interruption.json说明主动替代原因；日志、gate
    DB和全部中间产物保留，未以任何中间估计作为最终route验收。集中资源完成候选13。

17. 候选13真实保护系统interlock_real_route13通过30112868检查，11事件、HP0读18/
    HP1写8/实际重叠18；新增采样沿后HOME owner等价断言通过。source_identity13逐字
    核对实际仿真/TD源、原厂IP和原约束，并核对未变33项原回归DUT相同。
    gate setup/hold -2.820/0ns；最差源由工具命名为rs485/regs/cap_generation[21]，
    经32bit代际比较、restart及取消分发进入executor/state[1]：11级，cell 2.859/
    net 9.891ns，最大扇出1026。此为门级估计，完整原约束place/route仍在运行。
    owner_gate_result_r3.json只读审计确认新增cache为1个实际AL_MAP_SEQ FF，显式16线程
    读回、DB逐字未变。首轮审计因Windows反斜杠脚本路径被TD解析丢失而失败，日志保留；
    r2发现get_regs返回Q网别名，r3改查网络报告中观察到的真实driver cell并验证非空。
    后续如仍不达标，应按实际route路径优化代际校验/取消分发；不得用延迟检测或放宽
    完整反馈身份校验来换取时序。完整修改位置另汇总于INTERLOCK_TIMING_CHANGES.md。
    interlock_real_watchdog13通过28558278检查/12事件，仅WD原因；
    interlock_real_feedback13通过34335638检查/13事件，仅A0反馈超时。两者均HP0读18、
    HP1写8、实际并发重叠18，原有断言及新增owner状态关系断言均通过；按既有说明
    使用非生产共同epoch跳转测试到期边界，不是完整2秒墙钟长度仿真。
    尚未实现的备选：若最终route仍卡代际比较，可从源寄存器精确next-value前置计算
    两个完整u32的匹配结果，寄存后同拍使用；不能直接延迟当前比较或截取低位代际。
    rs485_gp_regs.generation仅合法LOCAL_RESET增加1且MAX拒绝；multirate.cfg_revision
    仅CFG_WAIT且!engine_active时增加1、MAX拒绝，collector local reset清零。预测必须
    覆盖GP reset_action的全部地址/值/strobe/状态门及同拍异步collector reset，原计数器
    更新RHS与预测共用；每拍对照预测与实际源值、缓存与完整比较，并用完整比较参考
    core作前后沿miter。实际服务feedback_generation/revision与当前collector同源直连，
    完整反馈身份检查仍须保留，泛用core默认路径也须保留。此方案目前只是备选分析，
    未改任何生产RTL；先完成candidate13真实原约束route再决定。

18. 新增真实并发补测interlock_real_accepted13：HP1首包仅放行4/8 beat与HP0并行，
    再次施加背压，保留原await_dma无HP1完成IRQ断言及后续故障背压。通过30112867
    检查、11采集事件、HP0读18/HP1写8、背压重叠18；其中2个采样沿两HP端均真正接受
    数据（accepted_overlap=2）。新ready窗口只在下降沿改变，未修改任何DUT RTL。
    同时在独立optimization/interlock_candidate14下准备备选，不改生产candidate13：
    - epoch_cache_probe.py/probe_r1：原完整比较core对lookahead完整u32比较缓存，
      8192周期、16384次前/后沿全624bit输出与round内部状态miter全过，包含任意u32
      跳变/回绕、非当前完整metadata、到期及配置/开关。只证明给定精确next-value时
      的core代数；不截位、不延迟当前比较，不声称真实源预测已接入。
    - counter_predictor_probe.py/counter_probe_r1：独立复制GP regs/multirate/bridge，
      保留原计数器更新分支，仅共用原+1算术并输出next-value；GP reset地址/数据预译码
      新增2bit，完整复用原接收拍，全部原拒绝门/MAX拒绝保留；bridge提前预测同拍
      local reset异步清零revision。原100MHz/115200 GP端到端302检查/11记录/丢弃>=2
      与新增3936453拍实际源预测检查全过；R5S2 416项原守卫及4005拍GEN预测全过。
    以上均为独立目录原型/模型，无生产RTL改动、未启动candidate14 TD、不能代替
    candidate13最终route。若13失败，再决定是否把已验证的完整next-value缓存接入实际
    顶层，并重新跑所有受影响模块、真实系统与完整原约束流程。

19. 2026-10-19 14:21响应状态核对：通过提升权限的Win32_Process查询确认没有本任务
    TD/Python/Questa进程。candidate13原run.log最后更新11:18，停于post-route优化，
    无最终route报告/DB/summary；原因未确定，不冒称完成或持续运行。全部原文件保留。
    新增resume_route.py从同一place.db恢复，独立resume_route_r1日志/摘要，不覆盖
    原run.log；显式16线程且读回，最终恢复原SDC，无哈希、无部署产物。

20. 按用户“这一轮布线完后总结资源/布线报告”的指令，candidate13恢复流程完成，
    resume_route_r1_summary.json的passed=true表示流程完成，timing_pass=false，
    signoff_pass=false。原100MHz最终gate -2.820/0、place +1.193/0、route
    -2.173/+0.020ns；route预算报告-3.423ns不用于验收。setup相对基线下降3.306ns。
    最终LUT6eq29873(+1688)、Slice37984(+2065)、Slice FF37863(+1460)、PAD FF9不变，
    ERAM/DSP/IO及各时钟资源数量均不变。新增状态2461bit，实际gate FF增量1892，
    不能用声明位数代替实际成本。最差push_data[30] payload合法性/保护停止路径到
    a1_dir CE，10级，cell2.173/net9.749ns；其Max Fanout28，不把全局最大FO套入此路径。
    physical/pins/cdc审计全部通过，16线程及原约束读回，DB逐字节不变，无新增告警代码。
    所有>=64负载网共481条，data/CE/reset/clock/constant分类保留；最拥塞1% tile
    平均routing util97.560811，最终187090路径全完成、overflow0，时序仍失败。
    report_interlock.py新增显式resume摘要/日志参数，统计完成gate/place及恢复route，
    排除中断route重复告警计数但保留原文件。机器比较为
    evidence/interlock_comparison_route13_resumed_r1；中文最终本轮报告为
    optimization/interlock_candidate13/ROUND_REPORT_20261019.md。未改产品RTL、未采用14，
    未降低断言/约束、未计算日志或中间产物哈希、未部署。后续仍需实际路径优化及完整签核。

21. 2026-10-20用户恢复时序修复。先完整读AGENT.md并核对git；HEAD已前进到b963c21
    （其他NPU/BSP任务提交），保留新增的用户.gitignore/BACKUP.md/AGENT.md脏改及
    原两个RS485生成器等无关改动。候选15只按明确9路径接入新切分点：原EMIT沿
    与push/raw同拍捕获6bit保护/轴译码；完整u32下一generation/revision对下一round
    值计算相等关系1bit；GP LOCAL_RESET地址/数据预译码2bit及精确下一源值输出。
    原计数器更新/拒绝/MAX分支不变，原始记录/查询重试/退避/唯一RUN不变，未新增
    检测/禁止STEP延迟。旧profile默认禁用源译码；generic监测器默认旧直接路径。
    before保存候选13九文件原字节，未计算哈希；产品源码初始逐字节等于route13副本。
    sources_r1的生成器events匹配断言失败保留，修复内部连线插入点后sources_r2完成；
    unit_r1因测试协议头function放在module外编译失败保留，修正作用域后unit_r2通过：
    源EMIT 67360组（256地址×256枚举、command/status/length、高payload位）对旧事务
    全部输出及未改通用解析器差分；监测core 8192周期、16384次前/后沿全624bit
    输出及round状态比较，覆盖任意完整u32跳变/回绕、旧metadata、截止边界。
    375项完整联锁/legacy/停止相位回归通过（interlock_suite_route15_20261020_r1）；
    3170/3898旧ABI及生成顶层检查通过。原33项回归重跑，真实保护/WD/反馈超时用
    单会话Questa串行并加入每拍源预测、完整相等关系和原解析器译码对齐断言。
    完整实际顶层interlock_route15已启动，16线程读回、同100MHz约束与受保护IP；
    当前尚无gate/place/route最终结论，不提前宣称时序通过。

22. 2026-10-20 10:30用户从中断处恢复，提升权限核对所有任务TD/Python/Questa进程
    均不存在。候选15停在preplace，仅有gate -2.964/0ns；最差reset_count经restart、
    feedback_expired/causes进入执行器state，11级、cell2.863/net10.031ns、MaxFO832。
    保护真实场景30112867检查/HP0读18/HP1写8/同拍接受2已通过；WD无完成结果，
    feedback未执行，均不计通过。interruption.json明确记录未知中断原因及缺失最终结果。
    候选16新增active/off两个当前资格投影FF，使用完整下一代际/下一round及精确下一
    reset/config-change/config-apply，截断当前复位/配置译码进入监测停止组合锥；
    当前RUN/OFF、在途保护、时间戳、截止和检测边沿不变。9个明确路径before保存15，
    sources_r1/unit_r1隔离先验通过后才提升产品源码；没有改无关文件。
    单模块验证：全624bit输出/round及新资格表达式16384次前后沿比较，实际GP source
    3936453拍四字段预测检查和原e2e302检查通过，配置apply257拍预测及原91检查通过。
    375项联锁集成与33项原运动/RS485回归全部通过；3170/3898旧ABI及生成物检查通过。
    源码新增声明状态2472bit，实际成本等待16的物理报告，不使用15/13资源拼接。
    用户要求确认布局布线开始后提供检查方法并结束回合，完成后由用户通知。
    10:50使用Start-Process -WindowStyle Hidden启动独立后台Python驱动PID2764；
    TD完整流程与串行Questa三场景并行；TD和场景结果分别写入launch_r1及build/evidence，
    总体workflow_result区分流程完成、timing_pass、功能和signoff_pass=false。
    status.ps1只读检查PID+UTC启动ticks（修正PS7 JSON自动DateTime转换导致的初版字符串
    误判），已实测识别存活。启动工具已退出而驱动/TD独立存活并持续更新日志，等待实际
    place开始再回报；未结束时不宣称已启动布局或时序通过，无部署/镜像/哈希。

23. 10:59确认独立后台候选16已执行start command "place"并进入PrePlace Optimize
    Design，线程实际读回16；驱动PID2764及TD进程存活，启动工具已退出不依赖本轮。
    gate -2.507/0ns，仍不视为物理目标通过。真实保护场景30112867检查、HP0读18/
    HP1写8/同拍接受2已通过；当前源码/真实编译副本/TD副本及vendor/constraints字节
    核对通过（interlock_source_identity16_protection）。WD/反馈超时由后台顺序执行。
    按用户最新要求交付status.ps1/BACKGROUND_README.md及固定结果路径后结束本轮，
    不等待route、不自动恢复后续工作；用户通知后再做最终资源/时序/数据库审计及提交。
    原失败/中断和全部日志保留，无中间产物或日志哈希；无部署、板卡或其他聊天操作。

24. 13:25用户检查异常中断：原独立驱动/TD均已退出，原run.log停11:47布局优化，
    没有place.db/route.db/summary。三个真实受保护IP场景已在11:08全部通过，保留结果。
    用户要求重新启动：从完整原gate.db恢复，源码/头文件及vendor/原约束字节比较先验
    一致，不重跑功能、不修改RTL。resume_pnr_r1使用显式breakaway标志但实际仍在
    Windows job内，独立性不足；该事实保留started.json。不声称已脱离受管作业。
    为避免聊天异常连带终止，改用Windows Task Scheduler零触发器一次性按需任务：
    注册成功后才核对并停止自己的旧TD子进程，父驱动正常写失败摘要退出；全部旧日志
    保留，并记明主动迁移。新任务Codex-PL16-PnR-20261020-R2由系统服务启动，
    pythonw PID15336父svchost.exe；13:43确认place及16线程实际读回，状态Running，
    triggers=0。任务只显式运行一次，结束自行删定义；无部署/板卡/自动使能或周期任务。
    当前resume_pnr_r2.log及resume_pnr_r2_summary.json、launch_r3总体结果与进程身份
    独立保存，status.ps1由active_run.json选择当前尝试。8小时TD超时写失败摘要，
    Task服务执行上限9小时；无日志/DB哈希。按用户要求确认开始后结束对话，等待通知。

25. 2026-10-20按用户要求结束本轮并提交模块源码检查点，包含候选16 RTL、唯一接口
    定义及生成物、生成/验证支持、软件调用模型、测试和契约。跨模块时序改动原因及
    位置见INTERLOCK_TIMING_CHANGES.md。提交前重新检查顶层生成一致性、3170项旧
    schema叶值及3898项旧数值定义兼容、Git差异空白检查，均通过。
    既有候选16功能证据为375项新测试、33项原回归及三个真实受保护IP集成场景通过；
    本次提交不是最终时序签核。当前后台布局布线不因源码提交而停止，最终route资源、
    setup/hold及数据库审计待完成后另行确认。用户AGENT.md及其他无关改动、日志和
    中间产物不纳入提交；不推送远端，不执行板卡或部署操作，不新增文件哈希清单。

早期失败记录保留：inputs_review_20261018_1为受限环境Icarus崩溃；monitor_20261018_2
为runner误传不存在的MODE/OFFSET参数；combined_r1_motion_4_0为旧模式注入污染新增
场景；added_motion_r1_8为PAUSE夹具缓存门不满足，改用明确单点非END夹具，产品容量不变。
早期真实系统1/2及综合候选存在生成声明/集成夹具修复；real3虽输出PASS但退出被中断，
保留为失败，未作为通过证据。后续不可用PASS文本覆盖非零退出状态。

本轮新runner不计算文件哈希。最终仅最小必要关键交付物及直接源码可计算哈希；
不计算日志、中间DB、整棵目录或所有证据哈希。板卡/存储/镜像/COM4不在本轮范围。
