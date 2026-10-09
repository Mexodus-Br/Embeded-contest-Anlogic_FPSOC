# 连续轨迹执行层 — 2026-10-09

用户已答复“接受以上最小契约”。新增 `continuous_motion.v`，保留已验收的 `axis_motion.v` 和 `four_axis_motion.v` 源码及接口。新层从独立逻辑记录口接收点；421 位原始 FIFO 元组和 1197 位预规划元组只是模块内部连接，不是线报文 ABI。80/128B 布局、CRC、寄存器/错误码数值、产品容量和板级驱动参数继续 Draft/TBD。

迁移：既有单轴/四轴单点调用不变；连续调用者须另行实例化新顶层，显式 OPEN、提供连续 sequence 的记录、等待 start_ready 再 START，使用 END 或显式停止。将来 DMA 解包与 GP 控制适配本逻辑口，需要独立冻结传输接口；当前没有 AXI/DMA/BSP 接入。

## 已确认契约

| 操作/事件 | 行为 |
| --- | --- |
| OPEN | 空闲、缓存清空、无锁存故障，接受非零且不同于最近 ID；上游保证全历史 ID 唯一。从实际命令位置快照规划起点，不自行 ENABLE |
| 点接收 | point_valid/point_ready 在上升沿握手；背压时上游保持所有字段稳定。u32 sequence 从 0 严格连续、不回绕。当前会话重复、缺号、乱序或已接收 END 后再入点取消会话；不同/已关闭会话握手丢弃并发 stale，不影响当前会话 |
| START | 首点已预检；未执行缓存点数达到 START_MIN_POINTS，或已收到完整 END 的短轨迹；参与轴配置/位置/EN 延迟满足且脉冲安全。请求为一拍 strobe，未 ready 时 rejected，不排队自动启动 |
| END | 最后一点完整 duration 和末脉冲安全完成，session_done 正常关闭，保留实际位置和 EN，不报欠流 |
| PAUSE | 完成当前点后暂停，保留会话、原始/预规划队列、EN；边界同拍请求生效。暂停墙钟不计执行 duration |
| RESUME | 显式请求且下一点已预检/安全门满足，从下一点重新计算相对时间。未 ready 请求拒绝，保留暂停，不自动重试 |
| 欠流 | 非 END、未暂停的区间边界没有已预检下一点，即取消；该拍迟到点不能补救；原始 FIFO、预取、预规划全清空，不延长当前 duration |
| STOP/故障/DISABLE | 同拍优先禁止新 STEP，取消会话并清全部缓存/预测状态；保留已输出计数，完成 H/L/DIR hold 才 stopped。普通停止保留 EN；DISABLE 撤销指定轴 valid 并安全排空/延迟释放 EN |
| reset/清错 | reset 可截短脉冲，立即 STEP 低、EN 禁用、位置 0/invalid，清会话/缓存。清错不恢复 EN 或旧会话 |

优先级为 STOP/故障/取消 > END 完成 > PAUSE。边界暂停允许下一点尚不存在；RESUME 仍要求准备完成。预规划发现不可执行点会取消整个会话，正在执行点按照普通安全停止契约排空。

控制是同步 strobe，fault 是同步电平。上游串行提交非安全控制、维护请求，按 ready/状态判断是否可执行；安全输入覆盖其他请求。异步安全输入同步、维护授权、HOME、软限位以及外部硬急停由后续系统层实现。

## 预规划与边界提交

数据路径：`motion_fifo(原始点) -> motion_planner -> motion_fifo(准备完成点) -> motion_executor`。三个子模块分别通过隔离自检后集成。

非零点预检仍使用 64 拍恢复除法和 CHECK（请求捕获后 65 拍）；运算与当前点执行并行，不在边界重新算差分/除法。驻留点无除法。planner 的 base 是预测端点，只有准备元组入队才推进，未参与轴沿用上一预测位置；它从不更新 STEP 命令计数。STOP/故障/复位/END 关闭清预测链，新 OPEN 重新取实际位置，绝不从取消目标恢复。

executor 在当前 duration 的结束上升沿同时提交下一准备元组，point_done 和下一 point_start 可同拍。提交检查完整四轴 base 等于实际已输出 STEP 位置、脉冲安全、参与轴有效配置/位置/EN、会话匹配；不符则拒绝并排空取消。实际位置仅由 REBASE 或真实 STEP 上升沿更新，仍是 signed64；预规划差分 signed65、幅值 u64，duration×100 和频率乘法检查 u128 溢出。

每段复用共同 Nmax 槽调度：`D=max(Q+S,E,L)+2`（非零运动轴最大值），`C=duration_tick*100`，`M=C-D`，非零轴首槽同时出边沿，槽时刻 `D+floor(k*M/Nmax)`；尾部 H/L/Q 在 C 内。详见 FOUR_AXIS.md。每个非零运动点都含共同保守前置预算；边界没有额外 65 拍等待，但两个脉冲之间仍有满足驱动时序的前置/尾部间隔。零位移保持 DIR/STEP/EN，仍精确消耗 C。

缓存中的完整记录不等于已经准备好；发送者必须给预检留足提前量。START_MIN_POINTS 约束缓存点数且首点 ready，不承诺任意迟到流都可持续执行。边界缺准备元组时停机而非拉长 duration。连续 testbench 用独立闭式调度和真实引脚计数核对零额外段间间隙及累计 C，不读取内部累加器当参考。

## 参数、状态与运行

FIFO_DEPTH=4、PLAN_DEPTH=2、START_MIN_POINTS=2 是可覆写的实现默认值，不是冻结产品容量。FIFO 支持非 2 次幂深度、满时同拍 pop/push、显式背压；两队列最小深度 2。buffered_points 统计所有尚未执行点（原始队列、planner、准备队列），fifo_level/prepared_level 分别统计两队列。busy 还包含暂停、规划和停止/失能排空。所有事件输出是一拍；active_sequence/done_sequence 区分同拍完成和启动。

四轴 H/L/S/Q/EN setup/disable/max_rate 按每轴 64 位打包，axis0 在最低位；默认 0 禁止未配置轴输出。EN 极性显式参数。所有测试/综合参数仅为夹具。

```powershell
python pl_motion/tests/run_continuous.py
python pl_motion/tests/run_sim.py --environment-check
python pl_motion/tests/run_sim.py
python pl_motion/tests/run_four_axis.py
python pl_motion/build_td.py
python pl_motion/build_td.py --top four_axis_motion
```

Windows Icarus 采用已验证的普通进程环境，具体见 VALIDATION.md。runner 不重试或跳过失败组；完整结果和工具输出保存于忽略的 build。build_td.py 使用 PATH 当前 TD，DR1M90GEG400 speed=2 是摸底参考配置，可显式覆写 speed；串行输入/观察包装保留实际逻辑而避免虚构板级引脚映射。实际读入 10 ns SDC 后检查报告中的 100 MHz。门级估算不生成/下载 bitstream，也不是布局布线签核。

当前功能仿真通过，100 MHz 门级估算未收敛，不能按 100 MHz 上板验收。下一步优先将 FIFO 输出捕获与 signed65 差分/abs/max/预算预检分级，并缩短执行层宽算术/控制路径；增加的规划延迟须重新核定提前量和连续/欠流测试。随后进行真实器件/封装确认、布局布线、CDC/复位约束与板级时序验收，再接 BSP/AXI/DMA。
