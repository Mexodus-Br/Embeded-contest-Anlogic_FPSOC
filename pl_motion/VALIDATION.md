# 单轴仿真验收 — 2026-10-09

2026-10-12 GP追加：独立寄存器Icarus3,822检查、真实TD受保护AXI3→Lite转换器Questa7,216检查通过；实际PS无WID写适配器3,167检查通过，两个顶层各7,216集成检查；最终PS封装参考speed2 OOC门级SWNS+3.013ns、route+3.533ns/hold+0.025ns。单轴/四轴/连续组件及22组/接口全量回归再次通过。完整证据、历史工具失败与系统/板级未验收项见 [GP_VALIDATION.md](GP_VALIDATION.md)，PS接线/共同复位见 [GP_INTEGRATION.md](GP_INTEGRATION.md)。既有运动RTL/Golden基线不改。

实际环境：Windows / Python 3.10.11；默认 D:/iverilog 的 Icarus 12.0 devel；另对官方 MSYS2 Icarus 13.0 stable 做了独立对照。100MHz 为 testbench 时钟，全部时序值为仿真夹具；未综合、未接电机。

## Icarus 异常与解决路径

先运行原 `python pl_interface/tests/check_verilog.py`，复现 3221225477（0xC0000005），无 HDL 诊断。最小程序/分块/完整常量在沙箱中时而通过；隔离 PATH/TMP 后连续 50 次编译通过，但正式入口再次崩溃，因此没有把这一步当修复成功。

下载官方 MSYS2 Icarus 13.0 及依赖到忽略的 pl_motion/build/toolchain，补齐依赖后，沙箱内仍复现访问冲突。未改全局工具。工具来源：[Icarus 官方安装说明](https://github.com/steveicarus/iverilog/blob/master/Documentation/usage/installation.rst)、[MSYS2 官方仓库](https://repo.msys2.org/mingw/mingw64/)。更换版本本身未解决该环境异常。

同样入口在普通进程（Codex exec require_escalated 自动审核允许的本地仿真）中，12.0 和 13.0 各通过 50 次最小编译/运行、772 个接口常量及三组完整单轴测试。最终默认恢复 PATH 原 12.0 并再次通过环境检查和最终测试。当前解决方案是使用已验证的普通进程环境，sim_tools.py 统一 fail-fast 调用并在访问冲突时提示；未证明沙箱中哪个底层进程/安全机制导致异常，也未修复沙箱本身。无自动重试/跳过，任何崩溃均非零退出。

## 最终结果

| 命令/夹具 | 实际结果 |
| --- | --- |
| run_sim.py --environment-check | 772 常量一致；50 次最小编译+vvp 均通过，无重试 |
| 轴夹具 H/L/S/Q/E/OFF/P = 3/2/4/7/5/3/8，EN active=1 | 64,910 次检查；777 个观察到的实际 STEP；320 个安全注入时刻、25 个复位时刻；PASS |
| 轴夹具 1/1/0/0/0/0/2，EN active=0 | 13,207 次检查；306 个 STEP；112 个安全注入时刻、12 个复位时刻；PASS |
| 轴夹具 5/3/8/20/9/6/10，EN active=1 | 158,156 次检查；1,262 个 STEP；512 个安全注入时刻、34 个复位时刻；PASS |
| tb_contract.v | 默认未配置、H=0、period 不足、max_rate 边界、H+L 溢出均判无效；冲突请求整体拒绝；EN setup/disable delay、零步保持输出、持续 fault 与 DISABLE 同拍仅一次停止并释放 EN、异步复位；PASS |
| pl_interface/tests/check_verilog.py | 最终普通进程中 772 常量实际 HDL 编译/vvp/数值比对通过 |
| pl_interface/tests/test_interface.py | 7 方法通过，无失败/错误/跳过 |
| pl_interface/generate.py --check | 4 派生产物逐字节一致 |
| golden_model/tests/test_regression.py | 10 方法通过，1,272 基线向量、201 轨迹点、2,388 几何检查；baseline/算法/参数/期望未改 |

轴检查共 236,273 次、2,345 个 STEP，覆盖 944 个安全注入时刻、71 个复位时刻。STOP/欠流/故障/DISABLE 各逐拍扫过多步和单步命令：接受后等待、DIR setup、上升槽、高脉宽、下降槽、低脉宽、最后脉冲、正常完成后空闲。监视器按引脚实际转变独立累计位置，核查 H 精确、L/setup/hold/EN/rate 最小时间、故障同拍无新边沿、停止计数保留、旧 session 不恢复、新 session 显式执行、源未解除不能清错。

边界覆盖 INT64_MAX/MIN 相邻一步与零步、两极之间 ±(2^64−1) signed65 差分及方向；极大目标只输出少量边沿后停止，不声称穷举 2^64−1 个 STEP。复位覆盖各相位，允许截短，并核查不自动恢复。

Golden 原始 RampsStepper.cpp 的 statement-has-no-effect 编译 warning 保留，未为消除 warning 修改基线。没有隐藏初期工具失败；早期环境失败和解决路径见上文。

## 尚未验收

相对 duration 点执行/可行性预算、四轴 DDA/同步、FIFO 与完整 session/序号生命周期、正常 END/暂停、HOME/维护授权上游门、CDC/板级同步复位、AXI/DMA/Linux 驱动、综合资源/时序、外部急停、电气/实际驱动时序及重新使能恢复。测试不能替代实板或驱动到位验收。下一步提案见 README，未直接集成四轴。

## 四轴单点追加验收 — 2026-10-09

上节为单轴阶段快照。随后用户确认四轴共同 Nmax 槽/余数分配、PL 逻辑输出对应边沿规则和单点阶段范围，新增 four_axis_motion.v，不修改已验收的 axis_motion.v。实际环境仍为原 PATH Icarus 12.0 devel、普通 Windows 进程；先复核 50 次环境编译/运行与 772 常量通过。未接电机或厂商 IP，未综合。

首轮完整四轴 bench 超过原单次 45 秒 wall timeout，按失败退出，没有计为通过。诊断子集证明时间正常推进，后将完整覆盖拆为 12 个独立自检进程，最多四个并行、每组 180 秒上限及 HDL 仿真时间 watchdog；未删减扫描时刻/自动重试。运行输出和全部编译诊断保存在忽略的 build/four_axis_results.json。Icarus 正常报告 @* 敏感于全部数组元素，runner 按数量汇报；其他诊断逐条显示。配置检查实例输入显式固定，无浮空输入警告。

最终 `python pl_motion/tests/run_four_axis.py` 全部 12 组 PASS：

| 夹具 | 参数/测试 | 最终检查数 | 安全扫描 / 复位扫描 |
| --- | --- | ---: | ---: |
| SCALE=1，EN polarity=1111 | A0..A3 H=3/4/1/5，L=2/1/3/2，S=4/0/8/3，Q=7/10/2/12，E=5/3/7/0，OFF=3/4/1/6；rate=10/5/25/12.5MHz；定向+100 个伪随机点及五个逐拍扫描组 | 2,105,044 | 1,120 / 280 |
| SCALE=2，EN polarity=1010 | 上述 cycle 参数×2、rate÷2，六组相同完整责任 | 7,604,997 | 2,240 / 560 |
| 合计 | 3,739 次原子 point_start、12,702 个主槽、30,266 个真实 STEP | 9,710,041 | 3,360 / 840 |

安全扫描每组从命令捕获后偏移 0..279（SCALE=1）或 0..559（SCALE=2）逐拍注入，覆盖 64 拍预检除法、CHECK、共同前置预算、首槽、异轴不同高/低相位、末槽/尾部及已正常完成后。STOP/欠流/任意一个 fault/DISABLE 均整组禁止新边沿并取消，已输出位置保留；故障源保持时不能清错，DISABLE 各轴独立等待 EN delay 且不自动恢复。复位每个同样偏移均异步断言，允许截短并禁止自动恢复。

参考监视器不读 DUT 规划/累加器状态，使用闭式 `D+floor(k*M/Nmax)` 核对槽时刻，`1+floor(k*Ni/Nmax)` 的累计差核对轴脉冲集合；按实际 STEP 引脚转变独立累计 signed64 位置。对应槽实际边沿偏差为 0 cycle（本 testbench 100MHz，逻辑输出），精确 H、最小 L/DIR/EN/rate、尾部 Q 和 point_start 后精确 duration 的 done 都断言通过。这不证明 FPGA 引脚或驱动 STP 输入的实板 <50μs 指标。

额外定向覆盖：不同轴数量/反向/零位移与 mask=0 驻留、部分轴运动、Nmax 容量边界、默认未配置/zero rate/H+L 溢出/Q+S+2 溢出/EN guard 溢出拒绝；INT64 两端相邻一步以及 ±(2^64−1) 差分整组不可执行拒绝、零 duration、duration×100 的精确 u64 边界（最大合法驻留接受后立即停止，下一值拒绝）；请求字段在预检期间改变不能污染已捕获点；部分 DISABLE/REBASE/ENABLE 和显式新会话恢复、迟到旧 ID 拒绝、持续故障与部分失能同拍仅一次 stopped、不自动 EN 恢复。

审查时发现 Q+S+2 极端参数需要 66 位，已修正并由上述非法配置实例证明拒绝；最终全量测试在修正后再次全部通过。没有通过参数截断/饱和执行非法运动。

最终复核原单轴三夹具和 tb_contract 全通过（236,273 检查、944 安全/71 复位）；接口 7 项、重生成 4 文件一致、772 常量实际 HDL 编译/vvp、Golden Model 10 项/1,272 基线向量全部通过。原始基线 warning 保留，Golden/单轴源与期望均未修改。

本批新增验收只覆盖四轴单点逻辑。仍未验收连续 FIFO/预取及无缝点边界、完整 session/sequence、正常 END/暂停、HOME、时间戳、软限位、CDC、GP/DMA/驱动、电气与板级时序/资源。计划下一步先确定 FIFO 生命周期、END/暂停/取消/预缓存规则，再实现连续调度；参数实物值仍 TBD。细节见 FOUR_AXIS.md。
## 连续执行追加验收 — 2026-10-09

新增独立 motion_fifo、motion_planner、motion_executor、continuous_motion；既有 axis_motion/four_axis_motion 源码与 Golden Model 保持。先隔离验证三子模块，再执行集成与既有回归。Icarus 12.0 devel，普通 Windows 进程；100MHz 是仿真时钟，不代表硬件时序通过。

| 实际执行 | 结果 |
| --- | --- |
| FIFO 隔离深度 2/3/8 | 7,610 / 7,739 / 7,972 检查 PASS；非 2 次幂、满/空、满时同时出入、背压和 flush/reset |
| planner 隔离 | 159 检查 PASS，70 个 cancel 偏移；signed65 正负/极端差分、duration 溢出、零位移、输出保持、取消不残留 |
| executor 隔离 | 1,665 检查 PASS，100+200=300 cycle 两段同拍切换；实际 base 不匹配拒绝、STOP 优先 |
| run_continuous.py，10 模式×2 timing scale | 全部 20 组 PASS；5,390,016 检查，3,400 point_start、1,596 point_done、338 END、2 欠流、2,526 stale、2,520 STOP/fault/reset 扫描偏移 |
| 原单轴环境检查和回归 | 50 次编译/vvp 与 772 常量 PASS；三组 236,273 检查、944 安全/71 reset 时刻及 tb_contract PASS |
| 原四轴单点 12 组回归 | 9,710,041 检查 PASS；3,360 安全/840 reset 时刻，30,266 真实 STEP |
| 接口/生成源/Golden | 7 接口方法 PASS；4 生成物逐字节匹配、772 常量 HDL 校验 PASS；Golden 10 方法、1,272 向量 PASS，基线未改 |

集成模式 0..9 分别覆盖多点正反向/掩码/驻留/短 END；边界暂停/恢复/END 优先；缺准备下一点且同拍迟到不能补救；满队列背压连续生产；重复/缺号/END 后错误与旧会话隔离；STOP 逐拍扫描；持续 fault 扫描；reset 扫描；不可执行预取点取消及以实际部分计数建立新会话；空下一点边界暂停及未 ready RESUME 拒绝。SCALE=1/2 的 H/L/S/Q/E/OFF 分别 3/2/4/7/5/3 和两倍，rate=10/5MHz，FIFO=3、prepared=2、START_MIN_POINTS=2，仅是夹具。

引脚监视器独立闭式计算每槽时间/边沿集合，并按真实 STEP 更新 signed64 参考位置。每拍核对实际位置未被预规划提前改写、H 精确和 L/setup/hold/EN/rate 安全；每点精确 duration、连续下一 point_start 与前 point_done 同拍、累计 duration（排除暂停）均通过。不是把 planner 内部输出用作 golden reference。

开发失败按失败处理：executor 初版解包漏 plan_mask 导致仿真超时，修正后重跑隔离测试；planner bench 在 cancel 撤销同 delta 采样 ready，补采样延迟；满队列 bench 源仍呈现已握手 sequence 时 ready 判断错误，调整为等待稳定的下一记录。集成持续 fault 暴露 busy 把“禁止接收”当成“正在规划”，已改用 planner 状态。早期 TD 指出 flush/out_valid/ready 组合环，拆为注册 occupancy 判欠流和直接元数据错误判取消后，重新综合无组合环错误。最终 runner 检查所有组，失败不重试或跳过。

### TD 100MHz 综合摸底（未收敛）

当前 PATH TD Release_2026.1_SP2，6.2.2.200067；参考 DR1M90GEG400、speed=2（实物速度等级未核实）。真实读入 `create_clock -period 10` SDC，在门级报告核实 motion_clk=100.000MHz。没有 false/multicycle timing exception。串行输入/观察包装保留核心全部输入/输出逻辑，不指定真实板脚；该包装开销在表中独立列出。完整 gate.area/gate.timing/run.log 在 build/td_continuous_motion，摘要入库 TD_RESULTS.json。尚未布局布线、加入真实 IO/CDC/复位约束或生成下载 bitstream。

| 范围 | logic LUT | 1-bit ripple adder | 寄存器 | DSP | DRAM | ERAM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| continuous_motion 核心 | 3,462 | 5,056 | 4,481 | 24 | 82 | 0 |
| 含观察包装 | 3,727 | 5,056 | 5,810 | 24 | 82 | 0 |

TD 的 unit LUT（含 ripple）=8,783/52,480，16.74%；寄存器 5.54%，DSP 10%。DRAM 是工具资源单位，不等同 82 个 ERAM 块。门级 area 仍可能随布局变化。

100MHz SWNS **−9.414ns**，STNS −15432.420ns，报告最小周期 19.414ns / Fmax **51.509MHz**，STA coverage 94.17%。最差路径 `raw_fifo/rd_reg[1] -> planner/dividend_reg[63]`：FIFO DRAM 读、signed65 差分/幅值/最大值及预算选择、除法输入捕获，20 逻辑级，数据延迟 19.344ns（cell 6.504 + net 12.840）。因此综合成功但 100MHz 时序未通过，不允许据此宣称硬件连续执行验收完成。

早期原四轴单点参考摸底为 WNS −11.343ns、最小周期 21.343ns/Fmax 46.854MHz；这说明原宽算术也存在时序缺口，不证明新连续层已解决硬件闭合。后续优先 FIFO 输入捕获及预检分级，并复核执行层宽算术/控制路径；增加规划延迟后必须回归连续段边界和提前量/欠流规则。布局布线与实际 100MHz 收敛仍为剩余工作。

### 本批验收边界

功能仿真和可重复 TD 门级综合通过；100MHz 时序摸底结论为不通过。线报文/CRC/容量/板级驱动时序未冻结；HOME、软限位、时间戳、异步安全同步、BSP/AXI/DMA、电机/驱动输入实测未开展。sequence 全 2^32 记录未穷举，33 位 next_sequence 的显式越界比较禁止回绕。保留精确 relative duration 与安全停止，不用增加段间等待掩盖预检或时序问题。

## 100MHz 收敛追加验收 — 2026-10-11

以上为历史快照。本轮保留单轴/四轴单点模块和 Golden 基线，只改连续层 planner/executor 内部路径。先隔离组件，再集成测试；全部已确认 STEP、signed64/signed65、精确 duration、同拍边界、END/暂停、取消和 EN 行为保持。新性能和迁移说明见 TIMING.md、CONTINUOUS.md。

| 最终实际执行 | 结果 |
| --- | --- |
| 连续组件 | FIFO 深度 2/3/8：7,610/7,739/7,972；planner：753 检查、76 cancel 偏移、120 个非整除 rate/掩码/元数据随机向量；executor：1,665；全部 PASS |
| 连续集成 11 模式×2 scale | 全部 22 组 PASS；6,065,980 检查、3,708 start、1,900 done、488 END、4 underflow、2,706 stale；2,700 STOP/fault/reset 扫描偏移 |
| 延迟与吞吐实测 | 非零 plan_valid=71 拍、请求间隔=73 拍；驻留=6/8 拍；100 拍最短 duration 连续边界同拍 |
| 新预检截止模式 | 空闲 planner 下提前 73 拍入点不能补救，边界欠流并清空；74/75 拍按时准备并提交；C=100/200 夹具全部 PASS |
| 原单轴/四轴 | 50 次工具环境检查、单轴 236,273 检查和 tb_contract；四轴 12 组 9,710,041 检查/3,360 安全/840 reset；全部 PASS |
| 接口/Golden | 7 接口方法、4 生成物一致、772 常量 HDL 校验；Golden 10 方法/1,272 向量 PASS，原基线 warning 保留 |

首轮集成有一项 FAIL，未计为通过：旧不可执行预取夹具要求停止时当前 3 步尚未全部输出，但新增 6 拍规划延迟使该 SCALE=1 场景恰已完成 3 个边沿、仍未完成 duration。最终保留原 3 步输入并精确断言实际位置为 3，同时新增 6 步输入验证部分计数恢复；两者都必须取消、不正常 END、不提交旧预测目标。未放宽脉宽、duration 或段间时刻断言。STOP/fault/reset 扫描从 280/560 增加到 300/600 拍，不缩减旧扫描范围。

实际 TD 三轮门级 SWNS 为 −1.823 / −1.350 / +0.497ns；最终布局 +3.098ns、布线 +0.688ns，STNS=0，布线 hold WNS=+0.020ns、HTNS=0。10ns 时钟在各实际报告中核实，参考 speed=2，未加入 timing exception。详细资源、关键路径、默认 hold 修复过程与可复现命令见 TIMING.md；最终完整报告留在 build/td_continuous_motion_r3_elapsed_compare，资源/首关键路径/检查输出入库 reports/timing_20261011。

本轮完成连续顶层参考夹具的门级及布线后 100MHz 检查，不宣称整块板卡签核。check_timing 保留 1 个物理 LSLICE 悬空输出、3 input delay/1 output delay 未设，STA coverage=94.26%；实际速度等级、板级 IO/jitter/CDC/复位释放约束和驱动实测仍未完成。route checker 运行无错误消息，但工具未生成请求的 route.drc 文件，归档真实 route_check.log，不编造 DRC 计数。未生成/下载 bitstream，未进行电机联调。
