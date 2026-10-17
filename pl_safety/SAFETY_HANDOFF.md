# PL 安全链路 / 并行 HOME 独立交接

## 2026-10-17 暂停检查点

用户要求“先到这，以后进行专门优化”，本轮优化已停止。当前RTL冻结在5ccd875，未追加其他RTL改动；十组功能/等价性证据见下表。当前源码的完整16线程综合、布局、布线predecode_top7已结束：100MHz最终setup WNS为+0.016ns、hold为+0.020ns，**未达到WNS>1ns目标**。报告归档于evidence/predecode_top7_paused/，生产配置继续禁启，未上板。

closure_top8在布线后物理优化阶段按用户要求停止，未生成恢复原约束后的最终报告，不作为时序通过证据。大型数据库与中间日志保留在build/；失败和中断见FAILURES.md。最终CDC审计cdc_final1尚未执行，SAFETY_RELEASE.json尚未封存。本组件以可接续的开发检查点交接，不代表安全链路发布门禁全部完成。

本交付实现用户于2026-10-16确认的三限位、并行 HOME、启动前受控退离、固定距离退离、急停动作反馈、故障锁存和独立控制/快照接口。生产配置禁止启动。**RTL仿真、完整工程资源/STA、实板验证为三种不同结论；未进行实板验证，不能带电机使用。**

源码基线为核验后的 c9f2e05；最初状态/交接输入身份见 BASELINE_AUDIT.json。当前测试源码身份见各result.json的source_sha256与完整工程inputs.json；尚无SAFETY_RELEASE.json。后续封存时由verify_delivery.py记录source_commit、source_git_blob_sha256、files_sha256；raw哈希保留实际测试字节，files_lf_sha256只允许Windows/Git的CRLF/LF检出差异，Git blob也逐项核对。不要将原 round2 身份清单套用到修改后的源码，也不要放宽旧 verifier。

## 入口与行为

- 完整安全候选入口：generated/safety_rs485_gp_ps_top.v。CONFIG_PROFILE 默认0，来自 config/production.json（approved=false、参数未定）；1与2分别是独立仿真/资源夹具，均不得用于电机。生产型号、接线、映射、数值须另行核验后生成新身份。
- 所有 STEP/DIR/EN/命令位置仍由原 motion_executor 持有。HOME 经专用私有接口使用原脉冲定时与安全排空；普通轨迹底座未替换。三轴独立搜索触发，全部停稳后建立参考，再反向固定距离退离；无二次接近。
- HOME开始立即三轴invalid；仅完整成功才原子valid。最终位置是reference加实际带符号退离步数，累计脉冲诊断不清零。普通STOP保留位置；限位/急停取消旧session/队列/半包并撤销valid。
- 闭合限位下可以显式清错回NEED，再HOME/PRE受限退离，普通运动权限不开放。急停稳定释放后须人工确认、显式清错、再显式HOME。旧运动窗口STOP同样终止HOME。无公开HOME_ARM；HOME_START明确授权专用EN/运动，HMI预览不能产生副作用。
- 两级同步、快速触发、独立稳定释放；release参数未配置仍锁存已采样急停。NO反馈不测12V，也不能检测断线。NC外部切电、NO独立性与实际器件尚待核验。

详细状态、原因、资格/优先级、时间溢出与位置所有权见 CONTRACT.md。

## 接口与迁移

唯一机器源为 pl_interface/schema.json 的 safety_profiles.gp_safety_home_v1。新生成定义见 generated/safety_defs.h/vh；候选0x80A00000/4KiB、IRQ7/SPI89/INTID121高有效level，BSP最终核验。A33译码、AW/W独立捕获、B/R背压保持、独立STOP、接受/完成分离、原因/首时锁存、逐轴进度和64word原子快照均有自检。CONFIG_ID_0..7读回规范化配置JSON的SHA256；完整驱动参数/原厂IP/约束身份见完整工程inputs.json。

旧接口3068个值保持，旧schema仅增加独立根节点；旧四份生成文件仅schema hash banner改变。pl_interface/.gitattributes新增schema.json -text：生成器散列原始字节，Git须保留当前schema字节，避免检出时改变哈希；其他原生成定义仍固定LF，无寄存器/数值变化。pl_safety生成物固定LF，evidence保留原字节。72B MOT2和原采集记录未变。motion_executor、continuous_motion、motion_service增加HOME_SUPPORT（缺省0）及私有接口；另有用户新增授权的motion_stream_rx性能重构，详见下表。原生成顶层不改，旧行为经18项回归验证。原入口的.fault(4'd0)不是本轮安全入口，不能沿用旧入口声称已接入安全。

## 冻结版自检

| 证据tag | 覆盖与结果 |
|---|---|
| predecode_units1 | 32组功能/负面场景通过：正常/闭合启动、每种触发顺序、超时/上限、重闭合、STOP、急停、旧任务取消、恢复及正常轨迹衔接 |
| predecode_phases1 | 7种停止场景×24相位=168组通过；在执行器采样边沿断言不产生新STEP |
| inputs_freeze1 | 两级同步、极性、独立释放资格和10种亚周期相位，1532检查通过 |
| overflow_frozen1 | signed64候选位置溢出同拍整组禁止边沿通过 |
| router_final1 | 七窗口A33译码/响应所有权与背压，460检查通过 |
| predecode_real1 | 真实厂商GP转换器/DMA、HP0/HP1模型、共享时间/IRQ7、HOME和真实MOT2后触限位取消；3612检查，HP0读取18beats，HP1写0 |
| timing_regress1 | 接收器重构后18项接口/单轴/四轴/连续/Golden/服务/GP/DMA回归通过；旧结果文件原样恢复 |
| predecode_resource1 | 与完整工程相同500周期驱动定时，直接HOME与闭合启动两组通过，205282/321322检查 |
| rxcarry_equivalence1 | 对原接收器所有公开输出10498周期逐拍等价通过，包含30组计数边界 |
| predecode_equivalence1 | 新控制窗口对优化前所有输出62048次等价检查通过，含3036写/750读及背压/非法访问 |

上述结果中的source_sha256与当前源码逐项核对。旧输入/overflow/router涉及的源码未改变，保留其原通过证据；接收器性能重构后18项旧回归重新通过，安全寄存器预译码后完整安全服务/真实IP/500周期夹具和全部停止相位再次重新运行。16/17/18模式向阶段时间接口注入加速时间，只验证超时优先，不作为1MHz物理时间证明。真实IP测试使用原共享1MHz基准。仿真warning、失败与中断均保留，说明见 FAILURES.md；完整工程结果须以 VALIDATION.md 的最终布线报告为准，predecode_top7已完成但WNS>1ns目标未达成，现按用户要求暂停。

## 接续与发布门禁

2026-10-17追加要求：所有新TD综合、布局、布线及数据库审计启动脚本固定threads=16；最终100MHz布线setup WNS必须严格大于1ns、hold非负。build_td.py与audit_cdc.py使用TD 6.2真实属性`set_param flow thread 16`（单数），输出参数读回和`get_num_thread`实际值；完整工程使用`open_project -single_run`，避免多run作用域将读回留在auto。verify_delivery.py拒绝缺少16线程证据或WNS≤1ns的候选。此前默认22线程试验仅为历史证据。

本组件内部的后续定点性能修正：safety_regs.v把SUBMIT/STOP地址资格及全strobe、data==1判断提前到各自AW/W捕获边沿，SUBMIT事务ID/重复/忙碌资格继续在原fire拍检查。命令及STOP生效拍不变，通用B响应译码保留。predecode_equivalence1对4e75142原模块所有公开输出62048次逐拍/组合检查通过，含3036次写、750次读、AW/W错开、背压、非法写和重复事务；完整安全功能/停止相位/真实IP/500周期夹具以predecode_*重新运行。新候选启用TD官方place hfn_opt_effort=high、max_fanout=128、opt_timing=high、logic_level_opt=on，保留10ns与原例外，实际参数脚本随证据归档。

用户已授权为消除长路径/高扇出修改其他RTL。以下集中记录本组件目录以外的全部RTL改动，包含前期HOME接口扩展和本次性能重构；未修改其他RTL或原厂受保护IP。最终时序结果须补齐后才能封存。AGENT.md由项目方追加16线程规则，保留其工作区修改，不纳入组件提交。

| 其他RTL路径 | 原因与修改 | 接口/行为影响与验证 |
|---|---|---|
| pl_motion/rtl/motion_executor.v | 增加缺省关闭的HOME_SUPPORT及专用HOME运动/参考/原子valid接口、逐轴固定周期计数和整组signed64溢出预检；沿用唯一STEP/DIR/EN/位置所有者和原脉宽排空。 | 新参数缺省0，旧调用保留；HOME检测拍禁止新STEP，已有高脉冲独立完成。原底座回归、overflow_frozen1、32功能/168相位、500周期夹具及真实IP测试覆盖。 |
| pl_motion/rtl/continuous_motion.v | 透传专用HOME接口、暴露pulse_safe，HOME所有权禁止普通plan launch；仍用原FIFO/planner/executor。 | HOME_SUPPORT缺省0，旧端口行为保留；普通STOP/会话取消继续走原路径。18项旧回归及完整安全集成自检覆盖。 |
| pl_motion/rtl/motion_service.v | 接入私有抑制/停止/失能/清错与HOME权限；安全入口禁止公开REBASE，普通命令需READY；取消session/队列/半包。持续私有STOP只产生一次完成，RX错误仅向HOME的通知寄存以断组合反馈。 | HOME_SUPPORT缺省0，原接口/错误检测当拍停止保留；新入口HOME_START才授权HOME运动。18项旧回归、恢复/旧任务取消负面测试及真实GP/DMA测试覆盖。 |
| pl_motion/rtl/motion_stream_rx.v | split_top3综合最差路径由completed[0]经32位加法、包尾错误及宽停止控制到执行器state，13级、最大扇出1064、setup=-2.254ns。ARM时保存count-1，接收时以completed==last_index比较，移走检测拍的加法进位链。 | 端口/握手/错误检测拍/取消优先级不变，32位模运算也保留count=0边界；rxcarry_equivalence1对c9f2e05原接收器全部公开输出10498周期逐拍等价，含原有效包/72字节逐一损坏/背压/abort和30组计数边界。rxcarry_units1、rxcarry_phases1、rxcarry_resource1、timing_regress1的18项旧回归及rxcarry_real1真实IP测试均通过；完整工程时序继续验证。 |

本批未做BSP驱动、设备树、启动镜像、物理接线或上板，未操作COM4、SD/eMMC/QSPI，未生成bitstream或自动执行REBASE/ENABLE/START。Watchdog与RS485自动停机策略保持另批。

项目方需核验：急停实际器件与触点独立性、NC切电/NO反馈电气及上拉保护；A0/A1/A2实体映射与方向；搜索/预退离/退离频率、距离、参考及每轴步数/时间上限；释放稳定时间与物理最大响应；驱动复电行为；GPIO针脚与BSP地址/GIC。上述占位上限不是机械保护。

原受保护S2MM DMA的SYN-5066、RS485 IO时序资格、实物speed未确认、DMA/DDR在途buffer隔离等原门禁继续存在。PL任务取消不证明总线/DDR已经静止，BSP须继续处理原生命周期及quarantine。完整资源/时序运行完成也不解除这些发布阻塞项。

复现命令见README.md。每次使用新tag保留原证据；本地Windows仿真器使用普通工具进程环境。源码和证据通过verify_delivery.py独立核验，不修改原身份门禁。
