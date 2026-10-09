# 单轴仿真验收 — 2026-10-09

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
