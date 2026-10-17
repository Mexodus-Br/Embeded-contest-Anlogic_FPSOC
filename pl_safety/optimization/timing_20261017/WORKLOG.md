# 2026-10-17 PL长路径与控制分发专项

起点HEAD 2f09a56；比较RTL 5ccd875、检查点2befa00、完整predecode_top7。AGENT.md有项目方工作区修改，仅记录哈希，不覆盖或提交。原发布和失败证据保持；不操作BSP/板卡，不生成部署镜像。

基线最终100MHz setup+0.016ns、hold+0.020ns，coverage99.96%；LUT6等效27866，Slice35605，Slice寄存器36263另PAD9，ERAM58，DSP6，IO17。原始报告及当前源身份见BASELINE.json；实际网清单由16线程只读恢复原route.db获得。

本文件按实验顺序保留过程与失败；最终完成于2026-10-18，性能专项结论和完整对照以HANDOFF.md、comparison_closure_cofactor_route5.json及TIMING_RELEASE.json为准。正式安全发布仍未签核。

## 候选一：观测计数边界前置

原式observed={0,count}+pulse_event（65bit），在同拍失败/运行资格路径中比较observed>=T。新实现维护当前count对应的at_T=(count>=T)、before_T=(count==T-1)，同拍判断为at_T || (pulse_event && before_T)。阈值0单独保持at_T=1；更新before_T只需比较旧count==T-2，不做加法后的比较。饱和计数保持64bit，另维护count_full，对原65bit溢出条件使用count_full && pulse_event。

状态位增加21bit（3个阈值×at/before×3轴，加3个full），实际完整映射代价须以最终报告为准。count/travel、饱和值、阶段清零边沿以及全部输出周期保持；没有新增停止延迟或缩位宽。失败仍同拍禁止home_run/STEP，快停和唯一执行器所有权不改。

counter_eq1：对冻结原模块全部公开输出逐拍/组合比较，8个阈值（0/1/2/5、u32边界及u64最大附近），各33416次检查，并断言flags与当前count的数学不变量。边界注入时只建立一致的起始count/flag状态，随后全部更新由实现驱动；计数器无人工自动修正。closure_counter_units1、phases1、overflow1、resource1已通过，32功能、168停止相位与500周期参数保持。真实IP和旧回归结果另行绑定源码身份。

## 当前物理高扇出基线

对所有网取得flat_pins/drivers/clock属性，对负载>=64的356个网逐个report_nets，核对报告负载个数与每一条实际load pin一致。分类保留混合负载计数，不能只凭实例名。

普通数据网69条，最大168；CE网188条，最大531；reset网92条，最大618；合法clock6条，最大6035；另常量网1条负载860。以上是>=64负载范围，低负载不据此重新归类；完整DataNet分布另取route.area。旧3392 CE/1523复位不是当前物理数值。clock按CLOCK属性及实际clock pin核对，不能因扇出大就当作普通数据信号处理。

## 探针失败/保留范围

baseline_physical首次定点实例路径误多写一层core，工具拒绝选择；正确物理实例从原路径报告重新取出，后续审计修正，不以空集合声称成功。baseline_nets1获取所有网属性成功，但工具filter没有选出高负载集合；该空文件不是引脚清单。baseline_pins1的get_pins -of net全部为空，断言拒绝，原日志及failure.json保留。baseline_pins2改为report_nets完整物理load pin清单并逐项计数，356条全部通过；没有放宽负载完整性要求。

## 验收和发布边界

最终必须同一完整安全/GPIO/RS485/双HP顶层、10ns、原有效约束，route WNS严格>1ns、hold>=0；中间综合/布局不替代最终结论。原SYN-5066、四个安全输入未分配核验引脚、RS485外部delay、物理speed与CDC/电气/上板/BSP资格仍独立处理。生产PROFILE=0禁启，未上板。

## 接收器校验前置的独立研究（尚未安装到生产RTL）

closure_crc_probe_eq1因候选生成文本把end/else拼接而编译拒绝，失败源码crc_check_candidate_syntax_failure.v与结果保留。修正空格后closure_crc_probe_eq2对c9f2e05原版全部公开输出10498周期、30个计数边界及87个损坏场景通过。

研究候选在原最后一个CRC计算边沿锁存bad_format || (~next_crc != transmitted_crc)，随原state进入CHECK，因此CHECK检测/停止拍不增加。它是利用既有CRC状态计算的前置寄存，不在错误检测后再延迟通知。该文件当前只用于研究，没有拷贝到pl_motion/rtl或正在运行的完整工程；若完整最终路径仍由CRC校验至执行控制限制，才推进该候选并重新跑模块/集成和完整P&R。未综合/布线的研究方案不宣称资源或时序收益。

## 既有发布校验器的基线边界

直接执行原pl_safety/verify_delivery.py时，因它从c9f2e05比较全工作树、没有把后来授权提交2f09a56修改的PHASE0_CONSTRAINTS.md列入允许范围而拒绝。该文档不是本轮修改，HEAD与文档均保持原样；不删除断言、不跳过旧门禁。本专项建立以实际授权提交2f09a56为起点的独立身份门禁，并继续逐项核对c9f2e05旧schema的3068个叶值及旧生成定义，仅认可新安全根节点。该旧脚本的拒绝不改写成PASS，也不影响已单独通过的生成器/接口回归。

## 第一完整候选结果与第二候选

closure_flags_top1完整16线程原约束route setup+0.326ns、hold+0.020ns，未达>1ns。Slice36253（较基线+648），原始完整归档在evidence/closure_flags_top1，源版本另存flags_candidate.v。原pulse_event观测加法已移出最差链；新最差来自timestamp[14]经阶段时间差减法与比较到executor high_left CE，data9.497ns（cell2.611/net6.886），9级、4ADDER（报告计数）、fanout37。

第二候选合并前述已独立验证的截止时间和CRC预校验两项；不单独声称二者各自贡献多少最终slack。截止时间在原phase_time装载边沿一并登记65bit {wrap,deadline}=start+limit，判定用并行now>=deadline、now<start。nowrap时timeout=(now>=deadline || now<start)，wrap时timeout=(now>=deadline && now<start)，精确等价unsigned(now-start)>=limit，含时间回绕、反向跳变和零阈值，不新增失败检测周期。新增65bit加上原21bit边界、CRC1bit，源码状态位共增87bit，实际代价看完整映射。

811632项循环域边界/随机数学检查、deadline_probe_eq1及wrap1逐拍对照通过。安装后controller_joint_eq1再以生产路径全部输出对照冻结原模块；closure_joint_equivalence1重新对照原receiver。32功能/168相位/overflow/500cycle夹具以closure_joint_*新tag重新通过，再启动closure_joint_top2完整P&R；真实IP/18项旧回归同样使用全新tag，旧候选和失败不覆盖。

## 第二完整候选结果与同源布线研究

closure_joint_top2完整16线程原约束gate -0.696/0、place +2.904/0、route +0.412/+0.020ns，未达严格目标。最终Slice35552（基线35605，减少53），wire length12285296；综合FF净增76（controller75、receiver1）。完整工程和测试已归档evidence/closure_joint_top2，后续不覆盖。

当前最差是PS HP0 RVALID→原厂DMA组合输出→接收器/停止资格→执行器a2_dir CE，6级，data8.803ns（cell2.447/net6.356）、最大fanout32。下一组RS485 poll_timer→scheduled_reg CE约+0.477ns，不能只顾单一路径。joint_path_audit1用实际物理LUT引脚/方程核对，路径中planner/dir_age实例名由打包而来，不代表执行了规划算法或年龄加法。原厂DMA和原停止边沿保持，不直接将其即时错误后移寄存。

closure_joint_route3保持第二候选全部RTL与同一次完整综合/布局，单独进行较紧setup优化预算下的布线，之后恢复原名义约束再报告和导出数据库；仅最终原约束全路径WNS>1ns和hold>=0可验收，较紧预算的中间slack不作通过证据。父级完整P&R、输入哈希、place DB身份、16线程读回及预算恢复的数学差值均由原route_closure.py门禁核对。不是降低时钟、增加false-path或多周期。

真实IP/运动旧回归closure_joint_real1和regress1、最终源码双HP遥测并发closure_perf2均通过；独立控制器差分267328次检查，最终接收器10498周期/30边界/87损坏对照通过。deadline_math2加强到1111216项小域穷举/64bit边界随机验证，先前数学记录保留。

## DMA即时停止控制链的等价展开候选

对DMA错误D、内核占用B=busy||session_valid、接收器未屏蔽错误R、其他非DMA abort A，有rx_error=!D&&!A&&R（含rst）。原停止项包含rx_error || (D&&B)。按D作Shannon展开，精确改为D ? B : (!A&&R)，其他STOP/故障项保持。这消除了D先经接收器abort屏蔽再反馈到STOP的串行依赖，不在检测后加寄存器，也不改变idle STOP/DRAIN完成语义。

receiver增加私有error_candidate组合输出，仅供service恢复非DMA abort cofactor；原error/stream/packet输出保持。该端口不进入GP/AXI/schema/IRQ，不增加寄存器或容量变化。所有非DMA abort（private stop/disable、home_enable、GP STOP、fault、reset_ok、disable、cancelled、session_done）逐项保留，HOME_SUPPORT=0/1纳入布尔穷举。

cofactor_probe_eq1对65536个16变量组合和原运动service场景全部36个输出逐拍比较通过；独立receiver closure_cofactor_probe_rx1全部公开输出对原版10498周期/30边界/87损坏通过。之后安装到motion_stream_rx.v和motion_service.v；cofactor_production_eq1在生产路径再跑并通过66799周期/36输出和全部布尔组合。完整top收益未测前不宣称消除物理瓶颈。身份允许项只增加这一个手写service文件，原SHA门禁/174输入集/受保护IP和其他源文件检查仍保留。

## 路由后预算恢复失败与纠正

closure_joint_route3的TD综合/布局继承及完整route完成，但Python恢复校验拒绝：route后的set_clock_uncertainty -setup 0没有清除仍生效的1.25ns用户SDC。旧margin_semantics4只验证了不经过route的内存STA调整，不能证明经过route后仍可恢复。两份原始报告同为-0.681ns，且路径明确显示sdc uncertainty=1.250ns；不能把旧文件名route.timing当名义结果。

constraint_restore_probe1以16线程只读导入该route DB，clear_user_sdc后重新读取原gp.sdc和ps-generated-properties.tcl；导出有效命令与原gp.sdc逐行一致，全部报告路径sdc uncertainty=0.000。原约束setup+0.569ns、hold+0.020ns，仍未达目标。no clock/invalid/loop/no-path/ignored等均0，原dummy2、input delay5、output delay2保留。失败在budget_restore_failure1，恢复证据在constraint_restore_probe1，不覆盖旧失败/假名义报告。

新完整候选closure_cofactor_top4开始前已使用相同原始逻辑，但运行中发现上述工具问题，其原始run.tcl保持未改；它的较紧预算place/route物理结果可研究，最终须通过restore_full_top.py独立认证、清空/重载原用户约束，并分别重新报告原place几何和route几何、导出新DB和实际有效SDC，才可判断严格目标。build_closure.py后续版本也已采用清空/重载，而不是仅设0；最终seal新增直接检查所有报告路径的实际uncertainty以及导出有效命令。

最终源码真实HP0/HP1并发closure_perf3再次通过23044562检查、HP0 288读、HP1 16写、STEP32；closure_cofactor_real1和18项regress1均通过。其后未修改生产RTL。

## 未安装的RS485后备研究

poll_zero_candidate.v只在原poll_timer递减/装载边沿同步维护当前timer==0，不延迟request_ready；poll_zero_probe1对冻结transaction全部12个公开输出、7个POLL参数（含0/1/32bit边界）各39993周期差分通过，含一致边界注入/真实UART/复位。生产RS485源文件未改、未综合/布线，不计最终资源和时序收益；仅在后续真实最终路径仍限制于该计时资格时评估安装。

## 第四完整候选及第五次布线

closure_cofactor_top4完成真实全顶层P&R：gate-1.439/0、place+2.786/0、route+0.523/+0.020ns（均此处列原约束值），仍未达严格目标。Slice35919（+314）、Slice寄存器36403（+140）、LUT6等效28185（+319），PAD9/ERAM58/DSP6保持。相较joint_top2只有整体布局/控制逻辑合并后的结果，不能把+0.111ns单独归给cofactor。全档已封存evidence/closure_cofactor_top4。

cofactor在相同原约束、同一综合参数的完整顶层gate.area上，平面top logic LUT从18641降到18598（-43），ripple8426、seq35489保持；receiver logic LUT373→367、service层级5513→5518。层级统计含子模块且优化可跨层移动逻辑，不能把这些层级差值相加。该项有真实综合逻辑收益、无FF代价；其独立route slack贡献未隔离，最终只报告整套候选真实资源/时序。

本轮还发现第二种预算生命周期问题：place的1.25ns确实生效并可恢复，但随后再次read同一optimization_margin.sdc没有保证route重新生效。route_closure_margin.timing全部路径实际uncertainty为0.000，和原route.timing同为+0.523ns；恢复差值断言拒绝，budget_reapplication_failure1保留。文件名和意图不代替实际工具字段。

当前最差仍HP0 RVALID→a2_dir CE：6级、fanout34、data8.692ns（cell2.497/net6.195）；下一条motion snapshot→GP读数据FF +0.532ns，7级、fanout33、data9.056ns（cell1.706/net7.350）。原观测计数/时间差瓶颈已移走，但全局>1ns目标尚未实现，不能称DMA整条物理长路径已消除。

closure_cofactor_route5保持第四候选全部RTL/完整综合/同一place.db，独立16线程重新布线。route_closure_safe.py保留原route_closure.py全部身份/时序断言，再增加经实际route验证的清空/重载门禁：开始前clear_user_sdc→原两份约束→唯一新margin文件；结束后clear_user_sdc→原两份约束→导出生效SDC→名义报告/DB。只接受最终原约束WNS严格>1ns和hold>=0，额外预算报告不作通过证据。后续完整build_closure.py采用同样生命周期，旧run.tcl/失败不改写。

新增PHY-5010仅指优化产生的四个collector state复制/别名网在QoR时无输入/输出，须在最终DB核对是否已删除/无消费者，残存有效网必须有唯一driver；原告警保留。DB import的RUN-6001线程覆盖提示须核对parent DB及读回仍16，不等同于实际变回默认线程。final warning review及对照报告同时列新/旧诊断代码，不默认忽略。

## 最终原约束验收（2026-10-18）

closure_cofactor_route5完成：全局setup+1.133ns、hold+0.020ns、STNS/HTNS=0、所有路径组违例端点0、覆盖率99.96%。全部报告路径SDC uncertainty=0.000，导出的生效命令与原gp.sdc逐行一致；器件、speed2、全部100MHz时钟、原GPIO/双HP/参数不变。额外1.25ns预算下中间SWNS=-0.117ns不作为通过依据。final_nets2与final_cdc1独立只读重放最终DB均精确得到+1.133/+0.020，16线程实际读回。

原pulse_event→DIR检测锥对三个DIR CE和数据输入查询，最差+1.841ns、7级、0ADDER、fanout59、data7.892ns（cell1.602/net6.290），首条真实源net为controller/pulse_event[1]；原10级2ADDER链已移走。全局当前最差仍HP0 RVALID→a2_dir PAD数据输入，6级、0ADDER、fanout36、data8.066ns（cell2.111/net5.955）。不称整个HP0物理长路径消失。

最终LUT6等效28185（+319）、Slice35919（+314，+0.5983个百分点）、Slice寄存器36403（+140）另PAD9不变，ERAM58/DSP6/IO17、GCLK1/SCLK6保持。源码新增87bit状态，gate净增76FF；最终其余64个净寄存器变化来自物理复制/合并及映射变化。没有释放Slice，明确以314 Slice和140实际寄存器换取+1.117ns全局setup余量。

高负载>=64物理网全部核对363条，每条完整load pin个数与flat-driver一致，全部79514网另存CSV。Data 69→79条、最大168→189；CE188→181、最大531→645；reset92→96、最大618→421；clock6→6、最大6035→5969；constant1/860保持。数据和CE最大扇出仍增加，不能称全类扇出下降。局部拥塞同阶段top1从90.385135%降到85.087838%，工具从存在拥塞改为无局部拥塞；最终总wire length12476080→12872576上升，分别报告不混淆。

check_timing全部14项计数相对基线变化0：关键clock/invalid/loop/no-path/ignored均0；原dummy2、input delay5、output delay2保留为已知资格边界。meta→sync四条路径仍参与时序，实际8个FF的连接/打包/属性均留存；工具async_reg识别0及器件MTBF资格仍未关闭。

首次final_nets1和final_warnings1因零引脚占位网不支持FLAT_CELL_PIN_COUNT属性而拒绝。final_nets2先按driver=0收集候选，再以完整report_nets逐项验证Pins/Drivers/Loads/InOuts均0后才接受CSV中的0；没有将缺失属性默认为0。final_warnings2确认四个占位网无真实消费者，线程覆盖告警仍实际16；原错误和告警保留。新诊断PHY-5010/RUN-6001已解释，没有新增约束/CDC/功能问题。

严格timing/full-top/functional/CDC/ABI封存预检通过。32功能/168停止相位/overflow/500cycle实际参数、31输出267328次控制器差分、14输出10498周期接收器差分、65536布尔组合及36输出66799周期service差分、真实七窗口/双controller、18项旧回归及最终源码23044562项HP0/HP1并发均通过。全部公开接口周期变化0，不延后任何停止检测。

第四轮确认place名义报告已正确恢复，因此最终采用安全route重建流程重用其同一SHA的完整place DB，而不是原计划的restore_full_top独立几何重报方案；该未采用脚本保留作研究/恢复工具，不计交付收益。最终route独立重放两次，所有报告和断言均使用实际生效的原约束。

原SYN-5066、四个安全输入实际针脚/电气/资格、RS485外部delay、实际speed/同步器属性/MTBF及BSP/DDR静止和板测门禁均继续保留；生产PROFILE0仍禁启。性能验收通过不是部署许可，不生成SAFETY_RELEASE.json或镜像，不上板。
