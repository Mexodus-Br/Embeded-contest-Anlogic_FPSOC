# PS 真实执行后端与 BSP 接入

2026-10-23，基于 `e7fcbc3`。这是**离线实现候选**：真实 Linux 用户态适配、受控 BSP 执行源码、假板卡测试已提供；没有实板执行资格。未连接板卡/串口/VM、写存储或运行机械运动，未改 Golden、冻结协议、frozen、PL RTL、DT 或镜像。工作开始时存在的其他任务修改保持原样。

## 实现与调用边界

`ps_hardware_backend.cpp` 实现 ExecutionBackend，`ps_linux_board.cpp` 将类型化调用接到 `/dev/bsp-saf2-exec` 和 `/dev/bsp-motion`。模拟与真实模式必须明确选择；Windows 或 Linux 缺设备时退出，不回退模拟。Web 的 Service 与 `ps_control` 行式适配器使用同一 Service/后端。`ps_control` 仅 stdin/stdout，不打开 UART；接线、串口权限和外部认证由未来本地串口 supervisor 承担。行式请求为method/path/body及可选request_id；普通队列上限8，接收线程单独处理完整STOP行，EOF丢弃未开始请求并请求STOP。输出仍受supervisor读取速度约束，真实UART/背压资格须另验。不要同时启动两个设备所有者。

既有 HTTP 认证/CSRF/控制会话门保留。新增 `POST /api/v1/hardware/action`，body 为 `boot_id` 与 `action`（open/close/recover/clear/home），只有当前控制会话可入队，重启 boot 不匹配拒绝。返回 queued 不是执行成功；观察 `/state.backend`、`/telemetry` 与真实 ACK/全局快照。网页明确显示模拟/真实来源，模拟注入在真实模式始终拒绝。新增动作不是自动启动流程。

SAF2 增量 UAPI 和构建限制见 [BSP 说明](../../bsp/safety_execution/README.md)。原诊断 ABI 保留；固定宽度结构在 Linux/AArch64 编译时做尺寸断言。不开放任意 MMIO，不增加设备窗口。

## 健康、身份与重启

服务关键控制循环成功推进 `poll` 才更新单调时钟健康租约。唯一设备执行循环同时核对快照、owner、故障、运输代际、执行期限与服务租约，目标每 500ms 报活；服务循环租约超过 250ms 不再续喂。500ms 来自 SAF2 契约，250ms 是软件保守期限，不替代 PL 的 1..3s 看门狗。设备循环没有无条件喂狗定时器。I/O/STOP 失败或不确定性使软件失去健康资格；迟到成功不重新取得资格。

PL 分配的 owner 与 MOT2 session 是独立身份。只允许显式 OPEN 新 owner；启动仅观察，不续喂旧 owner，不自动 OPEN/REBASE/HOME/ENABLE/START。重启没有重放队列，恢复日志标为 unknown。序号写前递增，耗尽失败，不回绕。软件 close 不关闭 PL owner；退出请求 STOP，旧 owner 到期由 PL 处理。

执行提交携带 boot、command ID、参数 revision、起始位置 ID/步数、运输 generation、取消 epoch。拒绝重复命令 ID、过期快照、旧 boot/位置/代际/取消身份、无资格与资源不足；本轮 ID 账本上限 1024，不淘汰重用。入队与实际开启 session 前各检查一次起始步数/资格。串口/Web 都不能绕过该后端边界。

## 运输、接受、完成和停止

编码复用原 C++ MOT2 codec，四轴记录中仅 Delta 掩码 7，M4 保持 0。每包最多 32 条，属于冻结 1..910 范围；使用已有 MOTION_PACKET，由 BSP 完成 PACKET_ARM、DMA IOC 和 packet_closed 检查。低水位 32 时补包，工作循环 5ms，packet/command 单次软件等待 100ms。上述软件参数只通过假板卡验证，不能声称满足实板最快供给时限；生产须测 underrun、CPU 调度与水位。

queued、PL ACCEPT_VALID/accepted_seq、DMA IOC/packet_closed、实际 DONE_VALID/done_seq 是不同事件。只有当前 session/generation、最终 accepted_seq/done_seq、恰好新增一次 END 及空队列同时匹配才完成。有限/无限重复使用新 session，取消 epoch 不变才允许继续；重复属于一次显式任务授权。IOC 单独不能完成任务，也不会更新真实 XYZ。

STOP 先原子发布取消代际，再独立尝试安全 STOP 与 MOTION_STOP，即使一条失败也尝试另一条，不等待计划/packet锁。只有写返回之后开始取得的快照中，运动 STOP_COMPLETE、安全 DRAINED 与 pulse_safe 一致才报告停止；2s 等待失败或写失败报告故障，停止健康续喂。请求接收、停止确认和 DMA 静止分别报告。新的 STOP 会作废旧停止/完成反馈。

STOP 后丢弃旧计划/待执行动作；迟到 ACCEPT/DONE/IOC 不能产生 START 或完成。只有显式 recover 调用原 MOTION_RECOVER；不自行 realloc/release，不设置 validated drain 属性。原 BSP terminate/reset/双队列静止证明失败则 buffer/通道/module 保持 quarantine，PL drained 不替代 DDR/DMA 静止。后端不提供解除 quarantine 的快捷路径。

安全 mailbox 另有 BSP 取消门：STOP 后旧 owner 的 HOME/CLEAR 返回 ECANCELED，须显式 CLOSE/OPEN 新 owner 再做恢复。控制会话可在硬件 fault 状态重新取得控制权用于显式恢复，运动入口的资格检查不放宽。

## 真实只读发布

设备 owner 发布有界 JSON 副本，HTTP/SSE/日志消费者不读 GP、不抢 DMA。`GET /api/v1/telemetry` 在真实模式返回：simulation=false、单调观察时间、1MHz PL 源时间、运输代际、安全/联锁/运动原始快照及其 ID、config ID、命令位置/脉冲累计的 source/valid/position_id。快照窗口之间分别原子，不声称三个窗口在同一采样沿捕获。250ms 无更新标 stale；失败不补零、不把目标改成测量。

主机模式的冻结 17 帧回放和真实快照采用 schema 分支；日志/跨启动快照保留各启动的 simulation 来源。真实 `xyz_estimate` 和 `driver_feedback` 当前为 null。命令位置只表示已发 STEP 的累计，不等于编码器或机械 XYZ。

## 集中接入缺口与方案

1. **真实 XYZ/方向控制尚未实现。** 现有 Golden 是 IK，主机 Service 只有模拟端点位置注入；没有批准的 FK/标定位置估计器、驱动内部旧目标一致性恢复及生产参数。不能从最新目标或 HOME 状态编造 XYZ。本候选真实坐标预览不可执行，jog/示教拒绝；C++ 后端的有身份绝对步数计划可通过真实运输路径执行，但产品坐标入口需补齐获准的只读位置估计来源，再以回读命令步数/参数 revision 绑定预览。未增加伪参考位置 API。
2. **真实 RS485 32B/64B 原始流尚未接到服务发布器。** 当前发布的是实际安全/运动快照；未另开 RX/FIFO 消费者冒领既有采集 owner。现有受控 R5S2 UAPI 只有独占 owner 与破坏性 DIAG/RX 消费，无跨 owner 只读帧发布；CONFIG 在 RUN=1 时 EBUSY，也无独立 RUN-off 操作。下一步应在非 frozen 的 BSP 工作副本增加类型化 RUN 管理与 owner 内有界原始帧副本/身份发布，再接现有 decoder，保留32B/64B、缺采、revision/generation 与时间；RX 取消仍受 HP1/DDR 静止证明限制。不能以安全层 feedback_qualified 代替服务已接收每轴反馈。R5S2 实时身份/配置/健康仍须由既有采集 owner 与板端步骤独立核对。
3. **目标内核模块与匹配系统运行未验。** 本机可用 Linaro 为 7.4.1，用户态 Linux 分支可编译；没有本轮可用的匹配 Buildroot7.5 内核输出、Module.symvers/SDK sysroot，新增 .ko 尚未构建。须在现有目标 BSP 构建环境编译新模块、核对 kernel ABI/运行库/低权限启动，再生成新的受控 DT/软件候选。没有改旧已验收镜像。

这些缺口仍是交付限制，不能登记“真实坐标产品接入全部完成”。无电机板端步骤及停止点见 [验收清单](NO_MOTOR_ACCEPTANCE.md)，本轮证据见 [测试登记](BACKEND_VALIDATION_20261023.md)。
