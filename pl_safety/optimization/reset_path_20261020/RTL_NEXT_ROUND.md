# 2026-10-20 RTL续轮（进行中，未验收）

用户在宣告HIGH后布线优化失败后明确要求继续动RTL，并尽可能减少复位、尤其异步复位。
当前HEAD仍07745a8，分支codex/pl-safety-home-v1。保留原未跟踪文件和owner对AGENT.md、
.gitignore、BACKUP.md、pl_rs485/tools/generate.py/generate_rates.py的修改。未上板、未生成镜像。

本轮比较起点是保留的候选21源码和完整实际顶层reset_path21：最终−1.339/+0.020ns，
Slice37039、LUT28920、SliceFF37815另PAD9、ERAM69、DSP6、IO17。门级真实连接异步SR20457。
HIGH运行约69分钟后按用户决定停止，最后中间−0.524ns不是最终报告；原库/日志全部保留。

## 隔离候选

rtl24：沿用已验证的紧凑NEXT管理空闲投影（当前资格，不是延迟一拍）；配置地址和full-one
分别在原AW/W捕获沿预译码；私有命令捕获449位、重放载荷448位及接收数据640位不复位。
所有状态/所有权/有效位/STEP/DIR/EN/位置/停止仍保留原异步安全复位。

rtl25：采集器15组5×32bit统计与64bit私有due去掉异步复位，共3360位。原initialized
位立即屏蔽统计读视图为零，原初始化边沿同步清零统计、初始化调度时间；无新增查询周期。

rtl26：配置pending拆为原存储状态与当拍admission分量，通过显式内部端口传递。
admission要求interlock_idle，而idle要求!HOME owner；所有HOME执行阶段都持有owner。
仅HOME-run使用admission=0的等价分支；原始存储pending/reset/apply、raw permit和detect
全部保留。HOME接受、普通命令、状态查询仍使用原完整许可。无安全动作流水或周期改变。
实际生成链由隔离generate_top.py渲染，不手改生成文件；legacy默认不启用新控制分支。

rtl27：cache四份generation/revision字段共1920位不复位。原since-reset written位继续
异步复位；首次写入前冻结身份为原零值，generation变化仍保留完整旧raw/身份，失败不改good。
合计源码层6817位数据移出异步复位；这不是实际映射FF/Slice节省数字，等TD报告。

内部周期清单：无新增接口/安全检测周期。仅无效且未被所有权发布的RX/私有命令载荷
在复位/取消后可保留旧值；新记录覆盖全部字段后才能有效。统计读视图和cache快照字段
仍与旧值逐拍一致，未初始化数据不会对外发布。

## 已通过的模块证据

- rtl24_service_r1：原07745a8服务66799拍逐拍等价。
- rtl24_suite_r1、rtl26_suite_r1：各原375项安全/HOME（含14×24停止相位）通过；
  后者仅补齐新内部输入连线，不修改断言或预期。包括HOME owner/cofactor实时断言。
- rtl25_control_r1：GP1973拍、采集器10593483拍逐拍相等；含全部统计视图、原UART
  线级从机、重试/故障/配置/回绕/饱和和复位。
- rtl27_cache3_r1、rtl27_cache1_r1：各128344项原全物化快照oracle差分通过，包括
  全512word、signed/未知enum/失败、原子快照/配置/generation/wrap/连续竞争。
- rtl27_rx_reset_r2：原72字节损坏与背压断言、96个接收/CRC阶段的子周期复位，
  26183拍逐拍差分通过。r1失败保留：新增短复位没有被原同步scoreboard观察，导致
  夹具的旧blocked标记未失效；r2补齐scoreboard异步epoch清除，未放宽原背压断言。

## 当前运行/后续

产品RTL暂仍为候选21，所有新源码位于rtl27_candidate_r1隔离目录；未宣称完成。
完整同器件/实际安全GPIO/RS485/双HP顶层rtl_path27已开始16线程gate（exec session6908）。
rtl_candidate_build.py保留完整flow，可用同一tag --resume-route从原gate副本继续完整P&R；
最终恢复原10ns/零额外uncertainty约束报告，目标仍setup严格>1ns、hold非负。
此脚本先检查上述六组模块结果通过，旧基线/门禁未删除。

原33项回归正在用隔离源码运行：evidence/interlock_regressions_rtl27_r1（session88814）。
真实原厂GP/双DMA/HP系统三场景正在串行运行：rtl27_real_r1（session3975），
每个编译副本保留候选源字节身份，不使用stub；Questa只有这一会话。

尚需：gate实际资源/路径→完整P&R→最终全网/复位/CDC/约束审计，确认ERAM容量与连通性，
最终源码/编译/保护IP/约束身份、报告及Git。若gate/route暴露新瓶颈继续定位，不凭门级
或中间slack验收。SYN-5066、实际IO/电气/速度/输入/机械及BSP/板测门禁仍独立开放。

## 更新：27门级判退，28修正候选正在验证

rtl_path27完整gate结束：−3.652ns、LUT6等效31777（21 gate为29340，增加2437）、
SliceFF37000（21 gate36966，增加34）、ERAM69、DSP6。门级变差，不启动其P&R。
其门级真实连接异步SR已实测14122（相对21的20457减少6335）；这不能掩盖资源/时序退化。
async层级变化：collector4746→1386、cache2614→694、receiver763→123、motion服务1747→1331、
485regs1036→1037；其他层级相同。审计rtl27_gate_reset_r1，显式16线程，原库字节未变。
新最差为home_owner_q→monitoring→feedback_expired→safety_stop→rx_error→executor_ready→
link_generation.CE，12级、最大FO326，门级cell3.023/net10.570ns。不是最终物理路径。

rtl28_candidate_r1保留全部异步复位减少和HOME-run cofactor，修复宽零值屏蔽开销：
- cache身份先原子冻结原字段及written位，在32bit选中字读口按冻结written补零，不再逐位
  在1920bit捕获入口补零。快照所有字段/时间/ID同拍原语义。
- 统计observe_tasks载荷以新内部observe_stats_ready限定；debug统计读口仍立即补零。
  bridge在实际所有profile启用STATS_VALID_SUPPORT(1)，GP快照同拍冻结stats_ready，
  仅在32bit选中任务快照字读口补零。未初始化载荷不会对外发布。默认0保留旧独立GP夹具。
- cancel_transport用精确OR cofactor：abort || receiver.error = abort || (rst_n && raw_error_candidate)。
  不延迟取消，不改变错误检测。恢复命令有maintenance_ok→receiver.IDLE→error=0，独立实现
  recover_commit并拆出link_ready/link_generation/software_generation唯一控制过程，保持原
  last-assignment优先级，不把START/executor_ready总mux再反馈给generation CE。新增实时等价断言。

28已通过：rtl28_service_r1原服务66799拍；rtl28_suite_r1原375项；rtl28_cache3_r1/1_r1
各128344项；rtl28_stats_r1独立旧GP全零输入oracle32800拍/8个epoch/全部480快照word，
捕获后valid/data变化、原背压/IRQ/配置/复位全部通过。RX与27字节相同，保留96阶段复位证据。
rtl28_control_r1（session41395）正在跑1059万拍UART/统计有效视图差分，检查new valid等于原initialized。
rtl28_r1原33项回归session6095正在执行；27原33项已全部通过。
27真实系统session3975保护与watchdog已通过（30112867/28558277检查），正在第3场景；
Questa仍仅这一会话，结束后才可启动28真实系统，不能拿27编译身份当28。

28 gate尚未开始；rtl_candidate_build.py现在按candidate名检查28的全部模块门禁。
待rtl28_control_r1完成后：
`python .../rtl_candidate_build.py --candidate .../rtl28_candidate_r1 --tag rtl_path28 --gate-only`
成功且有实际收益再同tag --resume-route，完整同GPIO/RS485/安全/双HP顶层P&R。
产品RTL仍21未改变，无当前TD综合运行（27已结束；复位审计亦已结束），没有Git交付。

## 最新：产品已整合29；29完整P&R运行，31门级运行

28 gate完成：setup−2.221ns、LUT29380（比21gate29340仅+40）、FF37001、ERAM69、DSP6。
最差仍HOME owner/安全输入→monitoring→反馈到期→stop→RX error→准备FIFO count，11级、
最大FO308。未对28单独做P&R，因为29仅另加已模块验证的frame/CRC去复位。

29=28+运输frame512/CRC32去复位。rtl29_transport_r4扩展原断言、全部有效输出逐拍比较
41330拍/814检查/339帧24包，满FIFO256同拍pop/push、单条刷新、回绕、长背压、IRQ及
错误完成、60个CRC子周期复位通过。r1准备脚本空白识别失败，r2零拍miter因wrapper
缺timescale不作为通过证据；r3/r4明确timescale并强制比较拍数门禁，旧文件全部保留。

rtl29_promote.py已在模块门禁通过后逐文件核对产品仍等于21输入副本，整合16个源码/生成器/
fixture文件；直接旧源备份在rtl29_integration_r1/before，无覆盖他人AGENT等文件。
当前产品为29，配置仍禁启；generate_top和generate_interlock --check、3170个旧schema叶子/
3898个旧定义数值兼容均通过。原33项29回归已通过；rtl29_software_r1 C/IRQ/错误完成/ABI通过。
真实原厂三场景rtl29_real_r1（原session42788）全部通过：保护30112867、watchdog28558277、
反馈超时34335637，均HP0读18beat/HP1写8beat、两HP同拍accepted_overlap2。
当前Questa空闲，不能把29证据当31/32。

候选脚本write_text曾生成Windows CRLF；生成一致性检查发现此格式差异后，产品4份SAF2
wrapper按原生成器write_bytes再生为规范LF，5份本次修改的RS485 RTL也恢复其原LF规范。
候选/TD/Questa已编译副本仍保留实际测试的CRLF字节，不事后修改冒充编译内容。
独立rtl_verify_identity.py明确只允许这9个具名源码的CRLF→LF比较，严格比较所有其他
RTL/header、IP、约束和wrapper参数，不跳过任何token；旧严格verify_interlock_build.py保持。
rtl29_identity_r1已通过current/TD/real身份，18个明确换行归一化边记录于result.json。

29完整同实际GPIO/RS485/安全/双HP P&R：build/rtl_path29，session54887，16线程。
29 gate−1.371ns、LUT29635/FF37001/ERAM69/DSP6（门级估计不能验收）；当前仍place阶段。
29最终route未出，目标>1ns/hold>=0未关闭，无Git提交。

## 隔离的队列内部局部化候选

30：motion_fifo.v保留原公共模块，追加有独立自检的新私有motion_plan_fifo；当拍flush仍
立即撤销公开valid、在原边沿让level=0。内部invalidate_q标志下一拍清物理指针基准，
在flush边沿允许不可见推测写；新请求在最早原边沿仍可进入，不增加公开ready/valid周期。
独立的planner.plan_pending和executor.plan_available去掉取消门，仅驱动私有存储，public
握手仍走原安全门。私有planning_base256位去复位，OPEN覆盖后才用于新session。
30私有FIFO逻辑8条物理9槽；991/66799拍内核/服务差分、375项安全（rtl30_suite_r2）、
6容量独立scoreboard共68626检查、1197bit/12024拍/1117满双操作通过。r1 suite因fixture
已整合端口后适配器重复添加连接编译失败，适配器幂等修复，无改RTL/预期。30不作完整综合。

31：在30基础上改为真正时钟读RAM、pop预取下一队头、空队列first push/单条pop+push全宽
显式转发，类似已验证运输FIFO。prepared逻辑/物理均8槽，全部1197bit，show-ahead公开周期
不变，碰撞由转发定义，不依赖RAM模式。模块rtl31_fifo_r1六容量68626检查、rtl31_wide_r1
12024拍/1117满双操作、rtl31_service_r1原服务66799拍、rtl31_suite_r1原375项全部通过。
新ERAM属性仅是映射资格，不据此称节省；实际门级build/rtl_path31正在执行（session34117），
显式16线程。**尚无31最终gate资源/时序、更无P&R，产品仍29**。

32：尝试raw64也使用同一时钟队列，receiver.point_pending及planner.req_available作私有
生产/消费cofactor，PUBLIC_RX缺省0保留直接内核调用；服务内部置1，公开握手不变。
rtl32_candidate_r1准备脚本因receiver/kernel相同端口片段匹配两处触发assert，留下部分候选；
其r1服务/连续/安全测试即使通过也不得作完整32证明。没有修改该部分候选。
修正脚本仅修改kernel片段，完整候选为rtl32_candidate_r2，raw_clocked_notes.json存在。
rtl32_service_r2原66799拍差分已通过；rtl32_suite_r2（session27993）原375项正在执行。
通用FIFO文件与31逐字节相同，可复用matrix/wide证明，但最终需完整顶层/真实IP再跑。
32尚未综合/集成；是否使用由31实际映射与29最终P&R瓶颈决定，不盲目叠加。

下一步：完成29P&R和31gate读取实际数字。若31有收益，继续完整P&R并核对全部RAM容量/
银行连通性和真实vendor RAM模型，不把RTL仿真代替映射证明；若实际瓶颈仍raw控制，
再评估完整32。最终仍需目标>1ns/hold>=0、实际全网/复位/CDC/约束审计、身份与Git。
