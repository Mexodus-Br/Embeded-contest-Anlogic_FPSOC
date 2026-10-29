# 当前执行检查点（2026-10-20，任务未完成）

用户要求本轮尽可能减少异步复位、消除长路径、完整综合布局布线；继承原目标原10ns
约束route setup严格>1ns、hold>=0，最终功能/资源/扇出/CDC报告及Git提交。
不要以本文代替最终报告，不结束为“已启动”等待用户。无板卡/BSP/部署操作授权。

当前根目录7份RTL改动见WORKLOG.md，当前候选20，基线07745a8。
原工作区其他修改（AGENT.md/.gitignore/BACKUP.md/两份485生成器）未碰、不得提交。
原分支codex/pl-safety-home-v1未切换；尚未Git交付本轮。

关键发现：初次取消planner数据异步复位后，raw FIFO从53 DRAM LUT推导11 ERAM，
NORMAL模式满同址pop/push返回新数据。真实原厂ERAM模型验证失败，所以17/18/19
三个候选已拒绝并主动停止TD，所有源/日志/数据库保留，不能交付这些候选。
20使用逻辑64×421bit/物理65槽的spare slot避免所有有效同址读写。原准备队列8条保持。
原source reset去除7581bit，17 gate实际异步SR负载26100→21483、FF−423、ERAM+11；
但这些只能当失败候选的中间数据，最终必须实测20。

当前native exec会话（需要write_stdin轮询，不是functions.wait cell）：
- 完整TD reset_path20：session_id=76284，build/reset_path20/run.log，summary.json。
- interlock_suite reset20_r1：session_id=34892（375项）。
- 原33项回归 reset20_r1：session_id=24034。
- 串行真实vendor IP三个场景 real20_r1：session_id=68555，E/real20_r1/result.json。
  E=pl_safety/optimization/reset_path_20261020。Questa唯一许可证，只能串行；等待三个
  完成后才跑最终RAM模型。TD仍可与Icarus/Questa并行。所有TD必须显式16线程并读回。
旧39338/88234/69382为被拒绝的17/18/19，已被停止，Python写failed summary，不再恢复。

已通过：33项(reset17_r2)、375项17/18/19；20必须看新结果。17/18三个真实DMA系统
场景均通过但仅RTL系统，映射RAM失败所以总体不能通过。20新的真实系统全部重跑。
独立diff equivalence_r4（planner26547/service66799/regs10409拍），stop布尔65536；
OFF投影off_candidate_r2共70317拍含65536组归纳边界；最终服务stop_equivalence_r2
66799拍；spare_equivalence_r1连续内核993拍、spare_service_r1服务66799拍。
spare_fifo_r1六容量全过，spare_ram_model_r1厂商模型5201 checks，full_dual520、
single_dual396、0同址。该模型参数来自17导出，最终必须绑定20实际参数再跑。

下一步必须做：
1. 等待20 gate报告，定位真实最差链，若仍有明确瓶颈继续优化；不要仅凭gate判最终。
2. 20 gate.db生成后运行（本机工具在沙箱崩溃，需require_escalated）
   python E/reset_inventory.py --build reset_path20 --tag reset20_gate_r1
   python E/ram_audit.py --build reset_path20 --tag ram20_gate_r1 --export-netlist
   核对11真实ERAM、容量/端口/地址宽度（65槽应7bit地址、addra常量高2位）、RST0。
   real20三场景完成后：
   python E/ram_model_test.py --tag spare_ram20_model_r1 --spare-slot --netlist E/ram20_gate_r1/mapped.v
   用实际最终模型参数验证5201项，保留原同址FAIL，不修改/屏蔽厂商模型。
3. 完整TD最终原约束时序/route.db完成后：
   python pl_safety/audit_interlock.py --build reset_path20 --tag reset20_final_r1
   该wrapper保留旧物理/pin/CDC全部断言，以直接字节比对替代旧日志/DB哈希，符合新AGENT。
   python pl_safety/verify_interlock_build.py --build reset_path20 --real reset20_real_protection_r1 --tag reset20_identity_r1
   最好三场景各核对；只在real场景passed后执行。current source与TD/compiled copies严格字节相同。
4. 原约束setup>1、hold>=0，coverage/check_timing/警告及CDC无新未解释问题。若不达继续
   查route实际路径，不能放宽约束或增加停止周期。最终audit replay数值必须同route。
5. 最终比较baseline13完整route（-2.173/.020，Slice37984/FF37863）与20；当前基线16
   只有gate（-2.507，LUT29459/FF37386/ERAM58），没有完整route，明确不同证据边界。
   也可给原封存SAF1 cofactor5 +1.133/.020（Slice35919/FF36403）作集成前参考。
   pl_safety/report_interlock.py能生成相对cofactor5完整资源/时序/扇出/拥塞/诊断表，
   注意其声明新状态总量未包含本轮OFF+1/指针+2，需在本轮独立最终报告说明，不伪改原证据。
6. 更新独立HANDOFF/FINAL_REPORT及最小关键交付/直接源码身份。新AGENT禁止日志/DB/
   目录哈希，不打包这些文件。只给7份最终直接RTL及必要关键约束/IP身份；旧门禁/断言保留。
7. 明确Git提交7个RTL+本轮工具/报告/必要JSON，排除owner文件、失败大中间网表、vvp/work
   与原大量日志。前序Git发布不动，不切分支，不删除任何旧文件。最后核实状态/commit。

工具注意：一次私有停止差分auto-review超时拒绝，按规则重试一次成功；不是安全拒绝。
当前没有待审批或functions.wait cell。write_stdin可每次等≤60秒，工作期间定期中文简短更新。
不使用子agent（开发者禁止未显式授权的delegation）。

长期阻塞保留：SYN-5066受保护S2MM、真实安全引脚/电气/async_reg识别/MTBF、外部RS485
时序、机械HOME/停止/复电、BSP DMA/DDR quarantine/板测；生产PROFILE0禁启。
最终数字功能/时序通过也不等于部署授权。无bit/镜像/板卡/COM4操作。

## 18:40 后续检查点（以本段为最新）

产品源现为候选21（8份RTL，新增motion_executor.v），完整P&R session84916。
候选20已完整完成并明确拒绝为时序通过：gate−2.537/0、place+1.104/0、
最终route−1.570/+0.020ns；Slice37291/LUT29138/FF37831另PAD9/ERAM69/DSP6/IO17。
不能以布局正slack代替最终失败。其physical/pins/CDC全审计reset20_final_r1通过，
但物理MTBF仍未资格化；check_timing既有dummy2、no_input5/no_output2仍开放。

21所有功能证据已通过：最终375项reset21_r1（session26470）、33项reset21_r1
（15553）、real21_r1三个串行真实IP（78058）、software21_r1 C/RTL/IRQ/错误完成/
旧ABI（47112）。实际21 RAM模型spare_ram21_model_r1通过5201次；ram21_banks_r1
验证11银行共同模式/地址/有效使能且421位输出全部保留（metadata101+duration64+
target256）。门级异步SR实际20457，对照26100减少5643（21.62%）。
21 gate LUT29340/FF36966/PAD9/ERAM69/DSP6；gate setup−2.274，11级、maxFO545。
21 place+1.293/0仍只是布局估计，当前在详细布线，不宣布通过。

baseline_route.py独立复制保留的gate16及源项目，44份RTL/header核验与07745a8相同
（仅行尾规范化），同器件speed2/原10ns/16线程完成优化前完整P&R，session64633，
build/reset_baseline16_r1。旧16所有文件/中断不动。最终必须使用这组实际基线对比；
旧13全route只作历史补充（-2.173/.020，Slice37984），不要混充16基线。

隔离memory_candidate_r1（准备FIFO私有推测存储）已通过原12种FIFO独立scoreboard、
wholecontinuous993/service66799以及375项安全/HOME。仅gate综合reset_gate22完成：
LUT29251（相对21−89）、FF36966、ERAM69/DSP6，setup−2.715、11级、maxFO509；
未见明确长路径收益，不提升为产品，也没有最终route可声称物理时序必然更差。

隔离management_candidate_r2为下一候选（还未集成）：从原进程完整分支/优先级机械
导出NEXT packet/session/mailbox值，寄存组合成CURRENT管理空闲资格，不延迟任何
当前资格/停止/生命周期。仅1bit新控制FF，原快停路径仍直接。每拍新增恒等式断言
验证其严格等于旧!session&&!packet&&!ah&&!wh&&!command_busy。
management_service_r1原全部输出66799拍等价及原断言通过；management_suite_r1
375项通过。reset_gate23正在完整实际顶层仅门级综合，session83327，未集成。
生成器r1的<=匹配把if比较符误认为NBA，未测试/未集成；r2以括号深度选择真正NBA，
状态赋值站点RX10/session4/AH3/WH3/command_busy9。原r1产物保留。

接下来：看21最终实际route，再看23gate能否切断邮箱到OFF/反馈超时到DIR的长链。
如果23有效，整理投影源码可读性、重复功能差分后推进完整P&R；不要把候选22或23
门级结果当验收。当前Questa空闲，未来真实IP只能串行重跑。最后原约束setup>1/hold>=0、
全网Data/CE/reset/clock/CDC、当前编译源身份、报告和Git均仍未完成。
目前无functions.wait cell。其余native exec会话可write_stdin轮询；整个任务未完成。

## 最新：完整基线/21都已完成，当前存在审批阻塞

详见STATUS_20261020.md。baseline16 reset_baseline16_r1全route -1.489/.020、Slice37715、
FF37889、LUT29666、ERAM58。21全route -1.339/.020、Slice37039、FF37815、LUT28920、ERAM69。
真正同基线释放676 Slice（1.29pp），WNS只改善.150ns，仍1206违例端点，不能通过。
候选23gate -1.953、LUT29749/FF36964、10级/2ADDER、maxFO508；尚未集成/无全P&R。
management_candidate_r3为可读的紧凑版本，management_compact_service_r1 66799拍通过；
还未新gate或375项，原r2机械投影375项通过，不能拿旧r2 gate混充r3身份。
当前产品仍8份21 RTL未进一步改变。提出RS485生产者捕获时并行预计算age符号位的
后续方向，仅分析，尚未创建age_cut或改生产者/生成器，不能声称已实现。

启动21最终物理/CDC审计被自动审批拒绝：审批服务账户使用额度用尽，明确提示19:33
后重试；动作没执行且不是安全判断，禁止绕过。不能再尝试不同入口/去提权启动TD。
普通只读身份工具verify_interlock_build --build reset_path21 --real reset21_real_protection_r1
--tag reset21_identity_r1已通过（无需提权），候选21当前RTL/header/保护IP/约束身份核对。
20全physical/pins/CDC已通过，21未审计，不挪用20数字。Git仍未交付，非验收状态。
当前无TD/Questa待完成（20、21、baseline16、gate22/23都结束），可关闭旧exec会话。
用户最新问：现在还有多少async reset和长路径？答门级真实异步SR20457（原26100）、
最终1206违例端点、最差10级RS485 wa[12]→a2_dir.CE，11.091ns（net9.111），WNS-1.339。
说明异步数是门级分类，布局复制后的精确数因audit未执行尚未知。最终审核/Git仍待完成。

## 用户指定单次 HIGH 后台运行（2026-10-20 20:51 Taipei）

用户最新明确要求：只运行 phys_opt -post_route -effort high，确认已开始后给状态脚本，
结束本轮；完成后由用户通知。不要自动启动其他候选、持续监控或新一轮优化。

已启动独立Windows Task Scheduler零触发器隐藏一次性任务：
Codex-PL21-PhysOptHigh-20261020-R1；worker PID2224（父svchost PID2508），TD PID30600。
这是TaskScheduler服务的job，不依赖聊天进程；worker记录in_windows_job=true不代表
仍挂在本聊天job。显式16线程，导入后重新设置并实际get_num_thread读回16。
日志已确认 start command "phys_opt -post_route -effort high"、PHYSOPT_HIGH_BEGIN、
Start post-route optimization和Reroute critical path nets to improve timing。
原约束before.timing精确 -1.339/.020，与来源21一致。

输入21 route.db独立复制为build/reset21_physopt_high_r1/route_input.db，原库/约束未改。
输出run.log、route.timing/area/check/drc、route.db、result.json/state.json均在这个新目录。
完成后result会有flow_completed、timing_target_met、before/after、资源增量及失败原因；
flow完成不等于验收/发布通过。worker自动只删本次任务定义，不删证据。

查询脚本：pl_safety/optimization/reset_path_20261020/physopt_high_r1/status.ps1，
可加-Watch（Ctrl+C只退出查询），普通完整Windows PowerShell可读取Task和进程。
工具沙箱内普通Get-Process/TaskScheduler不可见外部job，因此会显示可见性受限；
提权只读查询已确认RUNNING，HIGH命令进入true、16线程true，查询脚本本身已验证。
相关worker.py/launch.ps1/README.md同目录。此次不改RTL、不综合、不生成镜像/部署。
先前审批额度阻塞已在20:49本次启动时恢复；这轮启动及只读确认均审批成功。
原优化任务整体仍未验收/Git交付，等待用户完成通知再继续读取结果与最终审计。

## 最新收尾：用户宣告HIGH轮失败（2026-10-20 21:58 Taipei）

用户明确宣告本轮失败，补充运行一小时仍为负几百ps。已按失败收尾，核实PID/父进程/
命令行/创建时间后仅停止本轮TD30600；worker2224自行写出result与failed状态并退出，
一次性Task定义自行清理，已通过宿主进程与Task只读查询确认。全部日志/输入库保留。
证据：build/reset21_physopt_high_r1/user_failure.json、result.json、state.json、task_cleanup.json。
约69分钟后最后日志中间SWNS−0.524ns，未生成最终route.timing/area/db；不能将中间值
作为最终WNS或完整P&R结果。result中4294967295退出断言源于此次主动停止，不是自然崩溃证据。
最后完整候选21仍route−1.339/.020、Slice37039，专项setup>1ns目标未达成。
本轮不再启动候选/审计/新优化，不自动回退RTL；原文件、历史证据及他人修改保留。
没有活动TD/worker等待完成；整体未验收、未Git交付、未部署。

## 再次恢复：用户要求动RTL并尽可能减异步复位（2026-10-20晚）

用户在HIGH轮失败后明确要求继续RTL优化。本轮详细状态见同目录RTL_NEXT_ROUND.md。
勿把上一节失败收尾当作当前任务停止指令；现在正在继续，不能提前验收/结束。

当前产品仍21，未覆盖他人文件；隔离候选28完整真实顶层gate在执行：
build/rtl_path28，exec session90598（16线程，尚无gate最终报告）。
其模块：rtl28_service_r1 66799拍、rtl28_control_r1 10593483拍、rtl28_suite_r1原375项、
rtl28_cache3_r1/1_r1各128344、rtl28_stats_r1 32800拍/全部480word均通过。
接收器与27逐字节相同，rtl27_rx_reset_r2 96短复位/26183拍通过。
原33回归rtl28_r1正在执行（session6095）；27的原33项已通过（session88814已结束）。

27门级已判退，不启动P&R：gate−3.652ns、LUT31777（比21gate29340增2437）、FF37000、
ERAM69/DSP6。宽数据补零导致LUT开销，28将cache/统计复位屏蔽移到窄32bit读口，
并新增cancel_transport精确OR cofactor与opcode-local恢复控制以断开串联链。
27门级async实测20457→14122（减6335），证据rtl27_gate_reset_r1，不能因此忽略其资源/时序退化。

真实原厂Questa单会话仍为session3975：rtl27_real_r1，保护30112867与watchdog28558277
项通过，正在feedback_timeout；结束前不能启动下一Questa。27不能冒充28/29源身份。
下一完整候选若合入29，真实系统应直接对最终29串行跑三场景，避免无谓跑28再跑29。

另隔离rtl29_candidate_r1=28+rs485_telemetry私有frame512/CRC32去复位，VALID/包/credit/
generation/控制均保留原复位、无新增接口周期。rtl29_transport_r4已通过41330拍逐拍差分、
339帧/24包、满FIFO256同拍pop/push/单条刷新/长背压/IRQ/错误完成/60个CRC子周期复位。
rtl29_transport_r1脚本找实例空白失败；r2虽原功能87项通过，但新miter因原wrapper无timescale
比较0拍，**不得作为差分通过证据**；r3明确timescale+拍数门禁2689拍通过，r4再加完整边界通过。
均保留旧日志。29尚无gate，尚未集成；是否纳入最终以实际映射资源/时序为准。

下一步读取28 gate路径/资源（90598），若有收益从同tag --resume-route完整P&R，或先对
已模块通过的29做新完整gate（rtl_candidate_build.py仍须加入29要求及未变源码的精确字节复用门禁）。
最终目标原约束setup>1ns/hold>=0仍未达到；若未达继续实际瓶颈，不用中间slack凑数。
需要最终真实IP、CDC/全网/复位/RAM/约束审计、身份、交接和Git。无板卡/BSP/镜像操作。

## 2026-10-20 23:49 Taipei: user requests current candidate P&R and query script
Latest isolated candidate is rtl36_candidate_r1 (33 queue-local cleanup,34 executor
VALID cofactor,35 deadline wrap flags,36 original EMIT-edge freshness flags).
rtl36_suite_r1 PASS all375; rtl36_emit_r1 PASS65,536 Python modulo-time vectors.
rtl35_monitor_r2 and unchanged34/30/28/29 module tests gate the independent build.
No external cycle added;36 not integrated into product. Main RTL remains29.

Candidate29 full route completed: rtl_path29/route_summary.json, gate−1.371,
place+1.229, nominal route−1.459/+0.020ns; LUT29308 Slice37309 sliceFF37488 PAD9,
ERAM69 DSP6 IO17. No timing pass. Candidate31 clocked FIFO gate rejected:
ERAM unchanged69, FF38711, gate−1.664; no ERAM savings claimed.
Candidate33 gate−1.281, LUT29287 FF37833 ERAM69 DSP6. Worst path moved to
engine.push_data_reg[48] -> executor.dir_age_reg[64].CE,10levels including2ADDER,
11.222ns=2.791cell+8.431net,maxFO211;36 targets its time-qualification chain.

CURRENT BACKGROUND RUN: full prepared actual top rtl_path36, no gate-only.
Scripts: reset_path_20261020/pnr36_r1/{worker.py,launch.ps1,status.ps1,README.md}.
Launch verified23:48:47+08:00, task Codex-PL36-PnR-20261020-R1 state4;
worker8896 parent2508, builder25408, TD11300,16threads actual readback true.
Task has zero triggers; survives chat; worker removes only its task definition
when done. Do not re-launch this tag; do not stop unrelated processes.
Query: & 'D:\Works\Embedded_contest\dev\pl_safety\optimization\reset_path_20261020\pnr36_r1\status.ps1' -Watch
Logs/results: pl_safety/build/rtl_path36/{run.log,route_summary.json,gate/place/route.timing},
worker state/result in pnr36_r1. Builder --run-prepared rechecks source bytes and
constraints, rejects existing log. Final nominal10ns reports restore originalSDC;
1.25ns internal optimization budget is intermediate only. Target >1ns unchanged.
Questa idle;36 real-IP and final CDC/reset/full-net audit not yet done.
No Git commit yet; avoid staging entire E (large untracked logs/vvp/DB).
Preserve owner AGENT/.gitignore/BACKUP/generate.py/generate_rates.py edits.
Latest user asked launch plus query then return; do not claim project accepted.


## 2026-10-21 RTL37r5 / full build38 launch handoff
# RTL37r5 full actual top build rtl_path38

2026-10-21 user requested: once build starts, provide query script and end turn.
Isolated candidate rtl37_candidate_r5; main product RTL still29. Task
Codex-PL38-PnR-20261021-R1 is a one-shot hidden normal-user worker, zero triggers.
Confirmed10:42:08+08:00: worker9108, builder2512, TD12824; task state4,
16threads readback true; complete synthesis/place/route, currently synthesis.

Original device/speed2/10ns/GPIO/dualHP retained. Post-route command is explicitly
phys_opt -post_route -effort high, with original SDC before/after. It has not yet
entered HIGH during synthesis. Before/after physical optimization reports remain
separate. Flow completion is not target or release approval; final setup>1ns,
hold>=0 remain mandatory. No deployment/BSP/board/bitgen or protected IP edits.

RTL changes:1 atomic active-query qualification bit;586 private GP source payload
bits no longer asynchronously reset (mapped count still pending); timestamp
subtraction sign -> XOR/63bit borrow;65bit saturating add ->33bit + high-bit OR;
separate sole STEP-register process fed by local original-cycle stop cofactor,
existing high pulse drain retained. Original state/receive/management behavior
still exact. No externally added cycles.

Validation:375 original safety cases PASS (rtl37_suite_r3), service66799cycle
miter PASS (rtl37_service_r2), time65536vectors PASS, sat262208vectors PASS,
GP32800cycle oracle PASS, transport41330cycle/fullFIFO/CRC/reset PASS,
control complete collector/GP differential PASS rtl37_control_r1.
All-output safety-service cycle miter and33original regressions still running;
real-IP three serial scenarios rtl37_real_r2 currently protection running.
No final functional signoff; do not mix candidate29 real-IP evidence with37.

Failures preserved:37prepare_r1 ambiguous replacement;37r2/r3 direct stop cofactor
incorrectly treated HOME enable as stop (legacy recovery test9). Fixed r4 and
all375 passed. r1GP test qualifier typo compile failure fixed without relaxed
valid-data assertions. Actual Questa r1 detected an implicit wire followed by
initialized net redeclaration in inherited continuous_motion. r5 only moves that
same scalar net declaration before first use and converts initializer to assign;
exact byte transformation verified in declaration_compatibility.json and builder.
Real-IP r2 compiled and started. No source modifications after these snapshots.

Query PowerShell:
& 'D:\Works\Embedded_contest\dev\pl_safety\optimization\reset_path_20261020\pnr38_r1\status.ps1' -Watch
Ctrl+C ends query only. Logs/reports:pl_safety/build/rtl_path38. Worker result/state
beside this README. Prior gate-only rtl_path37 uses37r4, native exec session90976,
TD23572, and is independent evidence, not the current complete build.
Native ongoing sessions: safety diff23936;33regressions44878; real-IP83777.
No Git commit yet. Preserve owner changes and all old failure/evidence directories.



## 2026-10-21 build38 result review
Complete HIGH actual readback16. Nominal final WNS+0.032/HWNS+0.020, no negative endpoints; >1ns acceptance NOT met. Slice36694 (+2431 vs36), FF37478 (+170), LUT28905, ERAM69/DSP6. HIGH before -0.147 ->after+0.032 (+0.179). Connected async gate FF13301 ->13254 (net-47, not586).375 original and371 cycle-differential safety cases,33regressions,3 real IP scenarios all PASS. Source37r5 isolated, main29 unchanged. Full report pnr38_r1/RESULT.md. No fresh build/RTL changes this turn. CDC/full-net audit and Git not closed.


## 2026-10-22 read-only final routed path analysis
HEAD2edc71d;0a4ca51 removed standalone CDC gate; no longer a blocker. Latest complete build38 still+0.032/+0.020. New 16thread DB audit route38_analysis_20261022_r2 reproduced nominal timing, originalDB bytes unchanged. Nine individually targeted PAD CE endpoints all<1ns (STEP .038/.281/.032, DIR .138/.103/.073, EN .732/.561/.834).480 high>=64 nets classified: data161/max281, CE232/max651, reset80/max440 mixed ASR/SSR/other, clocks6/max6399,constant1/max957. Critical17/23/2load arcs>2ns cross management->execution; owner/idle/OFF-monitor feedback, timestamp/permit, GP transaction qualification are priority chains. Main resource increase executor+planFIFO (planFIFO DRAM0->440). Report ANALYSIS.md and analysis.json in audit folder. No RTL edits/no new synthesis/P&R/no board. r1 audit failed before loading DB due Windows backslash Tcl path; fixed .as_posix in r2; old evidence retained.
