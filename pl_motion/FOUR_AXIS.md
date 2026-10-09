# 四轴单点执行器 — 2026-10-09

用户已集中确认共同主槽/余数分配、对应边沿规则、duration 内完成脉冲时序、整组预检/取消及本批单点范围。实现 `rtl/four_axis_motion.v`，保留原 `axis_motion.v` 及其接口/行为不变。RTL 使用 Verilog-2005；100MHz 单时钟、异步断言/上游同步释放复位。

## 调度与时间契约

对参与轴，以已实际输出的 signed64 命令位置计算 signed65 差分，`Ni=abs(delta_i)` 为 unsigned64，`Nmax=max(Ni)`。各轴正向 DIR=1；有效 STEP 上升沿与位置计数同拍。未参与轴的目标在本逻辑口被忽略；本模块不读取/冻结候选 80B 记录。

请求先捕获四轴 counts/sign/mask、共同预算及 duration。`C=duration_tick*100` 用 unsigned128 计算，0 或超 unsigned64 拒绝。非零运动用 64 拍 restoring unsigned divider 计算槽间隔/余数，再用一拍 CHECK 整组预检。由请求捕获至 `point_start/cmd_accepted` 为 65 拍；零位移/纯驻留直接在捕获拍启动。duration 从 `point_start` 起算，预检延迟不占 C。

本批采用保守共同预算（只取非零运动轴）：

```text
D = max_i(max(Q_hold_i + S_setup_i, E_setup_i, L_i) + 2)
M = C - D
slot_min = floor(M / Nmax)
```

Q+S+2 用 66 位，H+L 用 65 位；预算超 unsigned64 即非法参数/请求。所有非零轴必须同时满足：`C>D`、`slot_min >= H_i+L_i`、`slot_min >= Q_i`、`slot_min*MAX_STEP_HZ_i >= 100000000`（unsigned128）。对慢轴也按共同最快槽检查，是有意的保守容量限制，不声称达到每轴极限性能。

第 k 槽时刻相对 point_start 为 `D+floor(k*M/Nmax)`，k=0..Nmax−1。RTL 以 quotient/remainder 累加，运行阶段不再做除法。每轴 accumulator 初始化 `Nmax−Ni`，各槽加 Ni，满 Nmax 发一个边沿并减 Nmax；所有非零轴在首槽发边沿，完整 Nmax 槽恰好 Ni 个脉冲。槽间隔至少 slot_min，最后一槽至 C 的尾时长也至少 slot_min，因而 H/L/Q 均包含在 duration 内。

“对应边沿”指同一 slot_id 内实际发出的各轴 STEP 上升沿；它们由同一时钟寄存输出，仿真测得偏差 0 拍。不同槽/不同轴第几个脉冲不默认一一对应。验收位置为 PL 逻辑输出；驱动 STP 输入、电缆及转换延迟另行实测，本次没有板级 <50μs 结论。

正常 done 必须在 point_start 后精确 C 拍，全部槽完成且所有轴 STEP inactive、L/hold 满足。Ni=0 的轴不改 DIR/STEP/EN，参与组完成屏障；mask=0 为纯 duration 驻留。正常 done 保留会话。

## 端口与维护/安全

目标、位置、REBASE 数值及每轴参数以 256 位打包：lane A0 在 `[63:0]`，A1/A2/A3 依次往高位。mask/输出 bit0 对应 A0，物理 M1–M4 映射未冻结。每轴 H/L、DIR setup/hold、EN setup/disable delay、max_rate、EN 有效电平为 elaboration 参数；默认时序/频率 0、config_valid=0，不能启用该轴。仿真夹具不能作为驱动配置。

控制和 `cmd_valid` 为一拍 strobe；fault 为四位持续电平。所有输入在运动域，上游负责 CDC/同步/去抖。`cmd_ready` 仅表示可捕获请求，不代表其内容预检通过；上游提交后观察 cmd_accepted/point_start 或 rejected。busy 覆盖预检、运行、统一停止和逐轴失能延迟。accepted/rejected/start/done/stopped/cancelled/slot_event/pulse_event 均一拍。

| 动作 | 本批逻辑契约 |
| --- | --- |
| REBASE | 整组空闲、无会话/故障，所选轴 EN 禁用；仅载入所选 signed64/valid。队列空、人工授权及 HOME 成功由上游保证 |
| ENABLE | 整组空闲且无故障，所选轴位置/参数有效；显式使能并开始 EN setup，重复 enable 不重置计时 |
| OPEN | 整组空闲/无故障、无现存 session，ID 非零且与最近 ID 不同；不自动 EN，不代表任何轴已经可运动 |
| COMMAND | ID 匹配、参与轴 EN/位置/配置有效及全部通道安全；整组捕获后预检；不可执行/错误 ID/参与失能轴等整组拒绝并取消，不产生该组任何 STEP |
| STOP/欠流/任一 fault | 本拍统一禁止新 start/STEP，取消会话，逐轴完成已有 H/L/Q 后仅一次 stopped；保留计数与 EN |
| DISABLE | 同样统一停止；仅 disable_mask 撤销 valid，停止完成后各自等待 EN disable delay 再释放所选 EN，其他 EN 保持 |
| CLEAR_FAULT | 源解除且非 busy，清锁存；不恢复会话/EN/valid |
| reset | 立即全部 STEP=0/EN 禁用/位置 0-invalid/会话无效，允许截短；不当正常停止 |

非安全的维护/enable/open/command 同拍冲突整体拒绝；忙时的新请求被拒绝，不能覆盖在执行点。任意故障与新边沿同拍优先，已输出边沿计数保留。运行时还检查全体将发边沿的轴时序、符号扩展位置更新和 rate；若内部不变量失败，本槽全体不输出、锁存组故障并排空停止。正常输入故障锁存其四位源；内部不变量失败以全轴 fault_latched 表示，本批没有增加数值错误码或寄存器映射。

通道无 FIFO，只存最近 session ID；旧输入命令不会自动恢复，恢复须显式新 ID。完整 session 唯一性、序号、记录校验、取消后 FIFO/部分记录清空由未来上游负责。DISABLE 后需 HOME/维护 REBASE、ENABLE、新会话；外部急停/人工移位有效性另由整机安全层处理。

## 运行与后续

在工作区根、已验证的普通 PowerShell 环境运行：

```powershell
python pl_motion/tests/run_sim.py --environment-check
python pl_motion/tests/run_four_axis.py
python pl_motion/tests/run_sim.py
python pl_interface/tests/check_verilog.py
python pl_interface/tests/test_interface.py
python pl_interface/generate.py --check
python golden_model/tests/test_regression.py
```

四轴 runner 将两组参数各拆为定向/随机、STOP、欠流、fault、DISABLE、reset 共 12 个独立 self-checking 进程，并行度 4，逐组检查；仿真 wall timeout 180 秒，HDL 内还有限定仿真时间 watchdog。无重试/跳过，结果和完整编译诊断写在忽略的 `build/four_axis_results.json`。原单轴入口的 45 秒默认上限保持。Icarus 的全数组 @* 敏感列表提示按数量汇报，其他诊断逐条输出。

本批完成四轴单点，不自动推断下一点欠流；underflow 由上游显式输入。下一步是连续点 FIFO/预检预取与原子边界切换，需先确定正常 END、暂停、预缓存深度/消费及取消/序号策略。本实现每点预检有 65 拍前置延迟，不能直接宣称连续无缝消费；未来连续调度需预取规划和完成屏障配合。GP/AXI/DMA、完整 HOME、时间戳和软限位集成仍未实现。宽算术/128 位比较的资源与 100MHz 时序必须在后续综合中验证；本次只仿真，不承诺硬件吞吐量。

## 后续状态

连续执行已新增独立 continuous_motion 模块，见 [CONTINUOUS.md](CONTINUOUS.md)。本文单点接口和 RTL 保持原行为；上文“连续 FIFO/END/暂停未实现”等描述属于四轴单点模块的范围，不代表新增连续层状态。
