# 100MHz 时序收敛 — 2026-10-11

本批以当前 TD 2026.1 SP2（6.2.2.200067）和 DR1M90GEG400、参考 speed=2 运行。未核实实物速度等级。固定 motion_clk=10ns，未添加 false/multicycle 例外，也未放宽 duration、脉冲时序或安全测试。仍是参数夹具和串行输入/观察包装；不生成/下载 bitstream。

## 依据实际路径的三轮修改

| 轮次 | 改动 | 实际门级 SWNS | 最差路径 |
| --- | --- | ---: | --- |
| 2026-10-09 基线 | 未分级预检 | −9.414ns | raw_fifo 读地址 → planner 除法输入 |
| r1_capture_pipeline | 输入捕获、signed65 差分、abs、成对/最终 max、预算检查分级；除法 borrow 与差值共用单次减法；预检 rate 用精确常量阈值 | −1.823ns | executor edge_age →控制使能，含加法/DSP乘法 |
| r2_executor_threshold | 运行时 rate 乘法改为最小间隔比较；signed64 更新溢出改为两端边界比较 | −1.350ns | executor elapsed → state，含比较前加法 |
| r3_elapsed_compare | elapsed 表示本次执行拍编号，直接比较 C/next_slot，消除比较前加法 | +0.497ns | prepared FIFO 读地址 → executor next_slot |

`n*R >= 100000000` 与整数 `n >= ceil(100000000/R)` 对 R>0 等价；阈值在 elaboration 中以 u128 计算，不以截断或近似 rate 替代。运行时对 edge_age 使用原 elapsed-cycle 约定判断。位置更新仅 ±1，正向在 INT64_MAX 或反向在 INT64_MIN 拒绝，与 signed65 更新越界检查等价；planner 差分保持 signed65。

elapsed 从 0 改为 1 是内部表示变化：点启动后第 t 拍比较的是 t，STEP/point_done/下一 point_start 的实际时刻保持。没有在执行路径插入延迟安全输入的寄存器。

## 新规划性能与接口影响

非零输入握手至 plan_valid=71 拍，输出即时消费时请求间隔=73 拍；驻留点=6 拍，间隔=8 拍。100MHz 的非零计算吞吐约 1.370M 点/s，高于 duration_tick=1 的 1M 点/s 消费上限；背压和混合队列仍影响实际吞吐，不能只据此保证任意迟到流连续。

输入捕获同时保存 session、sequence、mask、END 和 signed64 base/target；一次拥有一条记录，取消作废所有规划阶段、FIFO 和预测链。边界仍检查实际已输出位置、脉冲安全和会话。准备好点同拍提交，无额外段间等待。

新截止测试先缓存两点、等待 planner 空闲，再在第二段结束前 73/74/75 拍握手下一非零点。73 拍不足，边界取消并清空；74/75 拍按时提交。100/200 拍 duration 两夹具均通过，暂停墙钟、END 和同拍安全输入优先级保持。排队或准备 FIFO 背压时仍须增加提前量。外部接口未改，上游需迁移其提前量预算，不能再硬编码旧 65 拍。

## 验证和复现

本轮门级 SWNS=+0.497ns、布局 +3.098ns、布线 +0.688ns，均 STNS=0。布线 hold WNS=+0.020ns、HTNS=0，最小周期 9.312ns / Fmax=107.388MHz，STA coverage=94.26%。最差布线路径 planner/base_saved_reg[97] → executor/accumulator_reg[72]，数据延迟 9.103ns（cell 1.658ns、net 7.445ns），7 逻辑级。工具推导 GCLK，物理阶段默认 uncertainty=0.060ns；没有填未经批准的板级 jitter 值。

| 范围 | logic LUT | ripple adder | 寄存器 | DSP | RAM 计量 |
| --- | ---: | ---: | ---: | ---: | --- |
| 门级连续内核 | 3,829 | 4,061 | 5,267 | 4 | DRAM=82 |
| 布线连续内核 | 4,349 | 3,402 | 5,316 | 4 | DRAM LUT=656 |
| 布线含包装 | 4,733 | 3,402 | 6,645 | 4 | DRAM LUT=656、shifter LUT=8 |

门级和物理 RAM 资源栏计量不同，不直接比较 82 与 656。ERAM=0；含包装最终 slice=9,260/52,480（17.64%），reg=6.33%，DSP=1.67%，GCLK=1/SCLK=2。原门级连续内核为 3,462 logic LUT、5,056 ripple、4,481 reg、24 DSP；本批用捕获/阶段寄存器换取短路径并显著减少运行时乘法。

check_timing 报告 0 无时钟、0 无效约束、0 组合环，但保留 1 个物理 LSLICE 悬空输出：executor/state_reg[0]_syn_770.ofb（HIGH）。这是映射后未使用输出诊断，尚未消除，不把检查器宣称为全绿。load/rst_n/serial_in 的 input delay 和 serial_out 的 output delay 未设；真实 IO/复位释放约束继续待定，不能为消除诊断虚构数值。route checker 完整运行，无错误消息；该 TD 没生成请求的 route.drc 文件，其实际输出单独归档 route_check.log，不编造 DRC 计数。默认 route 曾出现 −0.035ns hold，工具正常 fix_hold 后最终 +0.020ns，未关闭 hold 检查。

```powershell
python pl_motion/tests/run_continuous.py
python pl_motion/tests/run_sim.py --environment-check
python pl_motion/tests/run_sim.py
python pl_motion/tests/run_four_axis.py
python pl_interface/tests/test_interface.py
python pl_interface/tests/check_verilog.py
python pl_interface/generate.py --check
python golden_model/tests/test_regression.py
python pl_motion/build_td.py --tag timing_100mhz --place-route
```

完整新综合采用当前 RTL；tag 保存不同轮次于忽略的 build/td_continuous_motion_TAG。`--physical-only` 只复用该 tag 中通过的 gate.db，核对源码 LF 摘要与速度等级。每阶段核实实际报告中的 100MHz，不把工具进程 exit=0 当作成功：必须有完成标记，ERROR/关键警告退出失败；门级未过不能启动物理流程。

本轮报告、资源及限制见 TD_RESULTS.json 与 reports/timing_20261011；既有单轴/四轴单点接口和 Golden 基线不变。仍需实际器件/封装/速度确认、真实顶层和板级 IO、时钟抖动/不确定性、CDC、复位释放与驱动时序约束验证。夹具通过不表示这些系统条件已签核。
