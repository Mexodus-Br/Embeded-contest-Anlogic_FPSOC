# 失败、修复与证据边界

本轮所有已产生的 evidence/ 记录均保留，失败结果不改写为成功。最终判定只引用 SAFETY_HANDOFF.md 列出的冻结版 tag；先前 tag 是开发轨迹，不是当前源码的通过证据。

已发现并修正的问题包括：输入测试在采样边沿同时改变信号导致仿真竞争（改为独立相位与同步参考模型）；HOME 脉冲事件观测晚一拍导致固定距离误差；旧 STOP 与私有所有权的排空；持续急停重复产生完成事件；清错对执行器故障的延迟；HOME 候选轴位置溢出时同拍其他轴仍可能发出 STEP（改为整组预检）；生产 RELEASE_CYCLES=0 时误屏蔽急停断言（将已采样与释放资格分离）。冻结版增加了相应负面测试。

完整工程首次接入还发现：派生 include 目录缺失；原 .al 含非 XML 的 UsedInP&R 字段，不能直接交给 XML parser；RX 错误通知与取消形成组合反馈（仅寄存 HOME 通知，保留原 RX 检测当拍停止）；异步寄存器属性改用厂商既有源码中的小写 async_reg。上述问题处理后才冻结当前 RTL；但当前综合QoR的#async_reg仍为0，不能声称属性已正确识别。实际寄存器/例外命中另作审计，物理CDC/MTBF与同步器放置保持未核验。综合试验日志不删除，归档见最终完整工程 evidence/ 的 prior_build_attempts/。

部分完整工程试验在后续源码修正或会话中断前停止，缺少 route.timing/完成标记的目录不代表资源或时序通过；尤其 frozen_top1 在打包后中断，未生成时序结论。首轮完整sealed_top1最终setup=-1.355ns、hold=+0.021ns，未通过100MHz；最差是edge_age→pulse_safe→request_ok→HOME授权→原执行控制链。仅将已接受的HOME专用EN授权寄存一拍，立即失效/输入快停不延迟，重新通过32/168/真实IP/500周期夹具后在timing_top2重建。首轮.d引脚例外未命中也已记录，改为只约束四个raw pad起点，源码只驱动meta，meta→sync不被例外。

timing_top2综合setup=-3.878ns，暴露阶段时间比较到宽执行控制的长路径；保留gate.db/gate.timing及中间布局日志后停止该自有进程。继续将HOME内部失败的宽队列取消通知寄存一拍，HOME当拍禁止边沿/撤销valid，限位、急停及两个STOP窗口仍直接快停；split_top3使用该实现。split_real1还发现Questa不接受stop_request使用在声明之前，移动声明后split_units2/split_phases2/split_real2/split_resource2全部重新通过，不依赖Icarus允许的前向引用。

sealed_top1首轮归档因工具没有产生独立route.drc文件而中断，该部分目录保留；修正归档器后使用sealed_top1_complete完整归档，DRC原文从run.log的report_route_status段提取，没有制造通过结果。cdc_first1、cdc_replay2的查询未正确匹配打包后寄存器，cdc_replay3证明4+4逻辑集合和内部时序路径，但仍带旧数据库的无效约束，不是最终约束通过证据。build/ 中的大型数据库未纳入Git，输入身份、脚本、约束和最终报告独立归档。

Windows 受限进程环境曾阻止 Python/仿真工具正常启动；普通本地工具进程下执行自检。仿真编译及厂商模型的原始 warning 保留，未通过忽略失败或自动重试得到 PASS。

resource_fixture1/2 为追加的500周期驱动夹具测试：沿用快速夹具的启动等待导致 HOME 正确被资格/停稳门拒绝。只调整测试台等待到650周期；resource_fixture3 两组均通过，未变更冻结 RTL。该测试按引脚逐拍核验500周期H/L/DIR/EN与固定距离，保留前两次失败。

既有受保护 S2MM IP 的 SYN-5066 多驱动诊断仍是发布阻塞项。本轮没有修改或掩盖 IP 内部问题，也不将一般资源/时序运行完成视为硬件发布许可。

2026-10-17追加16线程要求后检查发现split_top3已中断，停在布局Stage6.1，无最终route报告；默认22线程，不能用于本次最终门禁。线程探针确认`flow threads`是wild参数、实际仍22，正确属性为`flow thread`。threads16_top4在默认multi-run工程作用域的读回仍auto，启动保护立即拒绝，未进入elaborate/综合/布局；改为官方single_run模式后参数及实际线程数均16，threads16_top5从完整输入重新运行。上述失败与中断日志均保留。

随后按用户新增授权重构motion_stream_rx的包尾比较：将completed+1==count等价替换为completed==预存(count-1)，通过独立逐周期原版对照后，停止尚在综合中的threads16_top5旧源码候选，保留日志并启动rxcarry_top6当前源码完整工程。threads16_top5不是完整时序通过证据。选择timing_units1/timing_resource1旧目录时脚本正确拒绝覆盖；改用全新rxcarry_*目录，历史结果未改写。

串行18项timing_regress1全部通过后，原排队命令尝试使用已存在的timing_real1目录而被拒绝；没有运行或覆盖其旧结果。随后用新rxcarry_real1目录独立执行真实IP测试。所有测试目录都禁止覆写。
