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
