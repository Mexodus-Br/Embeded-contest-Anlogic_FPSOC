# PL 基础运动内核

2026-10-09 后续：四轴单点共同槽调度已实现于 `rtl/four_axis_motion.v`，见 FOUR_AXIS.md；连续 FIFO、并行预规划、同拍边界切换和 END/暂停会话管理新增于 `rtl/continuous_motion.v`，见 [CONTINUOUS.md](CONTINUOUS.md)。下文是保留的单轴阶段说明，其 RTL 和既有接口不变。当前功能仿真通过，TD 100MHz 门级估算未收敛，见 VALIDATION.md；驱动时序、报文布局与产品容量继续待定。

2026-10-09，仿真验收阶段。`rtl/axis_motion.v` 是纯 Verilog-2005、单时钟、单目标执行通道。它从实际输出 STEP 上升沿累计 signed64 命令位置，接受 signed64 绝对目标，以符号扩展后的 signed65 差分决定方向；每次位置更新还检查 signed64 溢出。位置不是编码器反馈。

## 本批范围与参数来源

本模块按参数化最小间隔逐步逼近目标，没有实现 `duration_tick` 点调度、DDA、FIFO、AXI、DMA、时间戳或 HOME 状态机。因此不能直接作为已确认相对 duration 轨迹的完整执行器。点 duration 格式、四轴同步算法和板级引脚不在本次冻结范围。

100MHz `clk` 为默认运动域。H/L、DIR setup/hold、EN setup/disable delay、STEP period、最高频率均为显式 elaboration 参数；驱动参数未批准前默认 0，`config_valid=0`，禁止启用和执行。测试台的数值仅为仿真夹具。后续板级实例参数须来自经手册与实测批准的配置，不得套用测试数值。EN 有效电平也是显式参数；STEP 上升沿有效、闲置低、DIR=1 正向为本轮确认的逻辑约定，物理轴映射另行核对。

参数单位为 cycle，最高频率为 Hz。H/L 和 period 必须大于 0；setup/hold/EN delay 允许 0。检查 `period >= H+L`（65 位加法）及 `MAX_STEP_HZ * period >= CLOCK_HZ`（128 位乘法）。年龄计数饱和、不回绕；高脉宽精确 H 拍，其他最小约束保守满足。实现按寄存器旧值判断，持续同向连续脉冲实际间隔为 `max(period+1, H+L+1)` 拍；该节流策略不作为将来 duration 调度算法冻结。

## 模块接口契约

所有输入在 `clk` 域；`rst_n` 异步断言、由上游同步释放。此模块不承担异步安全输入同步/去抖。

| 请求 | 接受条件与行为 |
| --- | --- |
| REBASE | EN 禁用、非 busy、无会话、无锁存故障；提交位置并置 valid。上游还必须确认队列空且完成维护授权；HOME 日后从相同提交口接入 |
| ENABLE | 参数/位置有效、空闲、无故障；显式拉起 EN 并等待 setup；重复 enable 不重置已启用计时 |
| OPEN | 非零、与最近会话 ID 不同、空闲、位置/参数有效、无旧会话/故障；不自行启用 EN |
| COMMAND | `cmd_ready` 且 ID 等于当前会话；锁存目标，依实际位置执行；零差分不改 STEP/DIR/EN，返回 done |
| STOP / underflow / fault | 本拍禁止新上升沿、取消会话及当前目标，保留已输出计数；完成 H/L 与 DIR hold 后返回 stopped；EN 保持 |
| DISABLE | 同样停止，并立即撤销 position_valid；pulse-safe 后额外等待 EN_DISABLE_CYCLES 再释放 EN |
| CLEAR_FAULT | 故障源解除且非 busy；只清锁存，不恢复会话或 EN |
| reset | 立即 STEP=0、EN 禁用、position=0/invalid、会话清除；允许截短脉冲，不属于正常停止 |

控制请求为一拍 strobe；`fault` 可持续为电平。`cmd_valid` 是单拍提交尝试，非 AXI-stream 背压接口；`cmd_ready` 为前置门，不含 ID 校验。accepted/rejected/event/done/stopped/cancelled 均一拍输出。非安全的维护/控制/命令请求同拍冲突时整体拒绝。STOP/欠流/故障/DISABLE 的优先级覆盖接受和新 STEP；已输出边沿不会回滚。已接受目标期间新的 command 被拒绝，目标不会被覆盖。

`busy` 包含执行、完成脉冲排空、停止排空及失能延迟。`done` 是目标计数到达且脉冲安全；`stopped` 是脉冲安全停止，不表示失能延迟已经结束。正常 done 保留会话；END/会话正常关闭在未来调度层实现。安全停止清 session_valid，并发出 cancelled；上游必须据此 flush 队列/部分记录、拒绝迟到旧记录。通道无队列，只存最近 ID；全历史 ID 唯一性、记录序号和防重播由上游负责。

DISABLE 后重新执行需显式 REBASE/HOME、ENABLE 和新会话。普通故障与 STOP 保留命令位置有效性；外部硬急停/人工移位需系统层撤销有效性，不能把本模块计数当机械位置证明。

## 运行

在普通 PowerShell 进程、工作区根运行：

```powershell
python pl_motion/tests/run_sim.py --environment-check
python pl_motion/tests/run_sim.py
python pl_interface/tests/check_verilog.py
python pl_interface/tests/test_interface.py
python pl_interface/generate.py --check
python golden_model/tests/test_regression.py
```

默认用 PATH 中的 iverilog/vvp；可设置 `PL_MOTION_IVERILOG_BIN` 指向同一发行版的 bin。工具为进程局部 PATH/TMP，未更改全局安装。本机 Windows Codex 沙箱会导致 Icarus 访问冲突，需在经授权的普通进程环境运行这些本地仿真；失败即退出，无自动重试、替换或跳过。环境调查与结果见 VALIDATION.md。

## 单轴通过后的四轴扩展提案（四轴单点部分本轮已确认并实现）

1. 保留每轴实际边沿计数、脉冲整形和停止排空，新增由调度器提供的边沿请求/ready 接口；不直接并排复制本批自由节流通道来宣称同步 duration 已实现。
2. 四轴 signed65 差分一起计算/预检；duration_tick checked-multiply 100 转 cycle。采用共同 DIR/EN/低电平预算 D，全部参与轴可行才原子启动。
3. 比较并审查共同槽 DDA/余数分配方案，逐轴在同一 duration 内输出准确 N，末脉冲高低/hold 不超预算；零步轴参加区间完成屏障。对应 STEP 边沿的标记规则及 PL 引脚/驱动输入测量位置需要确认。
4. 建立共同 session 取消线：任一轴或队列欠流停止全部轴，逐轴完成当前脉冲；全部 pulse-safe 后汇总 cancelled/stopped 与实际位置。FIFO/正常 END/暂停/重播语义另行审查。
5. 四轴 self-checking 台覆盖不同脉冲数、反向/零步、可行性边界、不同脉冲相位故障和对应边沿偏差；通过后再接 FIFO/GP/DMA。四轴 <50μs 指标尚未验收。

以上为初始提案记录。最新四轴单点实现采用独立共同调度 RTL，保留单轴模块；同槽对应边沿在 PL 逻辑输出的仿真偏差为 0 拍。驱动输入与实板 <50μs 验收仍未完成，FIFO/GP/DMA 未接入。完整测试结果见 VALIDATION.md 的四轴追加节。
