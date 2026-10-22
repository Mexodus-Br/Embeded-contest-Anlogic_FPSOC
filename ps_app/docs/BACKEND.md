# 真实执行与遥测后端接入契约（待项目复核）

当前可运行的是 SimulationBackend；硬件选择拒绝启动。本说明不代表已交付硬件适配器，也不把模拟接收段估算、10ms STOP或端点坐标当硬件证据。`src/ps_hardware_port.hpp` 是供项目方复核的 C++17 接入边界草案，无设备实现、不改变 PL ABI。

Service 目前的方向 tick、参考位置注入、sample_endpoint_simulation、500ms遥测陈旧值以及模拟日志明确属于主机模拟。hardware 模式接入之前，必须把这些替换为已核准的 owner 数据/策略；不得仅将 `simulation_backend()` 改成另一个构造函数就宣称完成。模拟注入通过单独 SimulationControl 和启动 capability 限制，不属于 ExecutionBackend 的生产能力。

## 单一所有权与状态

既有设备 owner 独占 GP/DMA 的消费和写入，PS服务获取只读快照与有界提交接口。owner 线程保持 SAF2 资格/健康报活，服务或日志线程不得另开设备消费或维持 STEP。启动先核对 SAF2/R5S2/位置/旧执行状态；旧命令进入 unknown，不重放，不自动 HOME/REBASE/ENABLE/START，不接管旧 owner。

状态必须分别携带命令位置/脉冲、经验证的 XYZ 估计、驱动编码器反馈，以及它们的 validity/source、源时间、观察单调时间、参数 revision、collector/transport generation。缺采/代际不匹配不补零，不把命令目标当实测值。时间戳单位继续按现有冻结契约，未定项不从100MHz推断。

## 提交、完成与停止

- 规划库仍纯计算，产生四轴绝对目标和相对 duration；M4保持禁用，Golden和MOT2编码保持不变。
- 提交携带服务 boot、命令/手动段 ID、参数版本、起始位置身份、取消代际和有界计划。owner 非阻塞返回拒绝/已入队/资源不足/资格不足，不在 Service 互斥锁内等待DMA、磁盘或网络。
- owner负责 MOT2 session、PACKET_ARM、每包1..910记录、FIFO/供给水位；入队、PL接受、DMA IOC、运动完成分别反馈。只有实际执行完成身份匹配才终结命令。manual segment 的 duration/提交身份不能丢失，缓冲上限待参数批准。
- STOP 请求应原子发布新的取消代际，优先于普通提交；异步报告 observed_stop_epoch、取消范围、pulse_safe、未知/失败。quarantine及迟到IOC不能恢复旧供给。HTTP成功只表示收到 STOP，不能替代物理急停。
- 提交前后均核对 epoch；取消后迟到接受/反馈仅用于核对，不能使旧任务恢复。停止/失联后位置有效性由后端证据判定。完整HOME、显式清错及驱动内部旧目标一致性恢复仍由现有专项契约确定。

## 遥测发布

提供只读不可变的 decoder 输入或解码快照，保留原32B/64B原始记录和来源身份/缺采统计。历史查询不抢占 owner 消费权。发布和读取均有界，数据源不可用时显示 unknown/stale；真实状态不经 `/simulation/*` 路由输入。日志由事件源明确标注 hardware/unknown，接入前还需扩展并复核当前 host schema 的 simulation-only约束，不能只把 JSON 标志改成 false。

适配器验收至少包括无设备 mock下的容量拒绝/迟到反馈/取消代际/owner丢失/重启unknown，以及另行批准的无电机板端资格、供给/取消/恢复。当前只完成 host SimulationBackend 验收。
