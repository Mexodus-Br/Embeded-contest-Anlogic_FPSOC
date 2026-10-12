# GP 最小控制实现验证 — 2026-10-12

结论：冻结 `gp_control_probe_v1` 的独立寄存器模块和真实 TD AXI3→Lite 转换器集成自检通过；参考 DR1M90GEG400 speed=2 的 OOC 门级及布局布线均通过固定 10ns。**PS raw端口核对已完成；完整 PS/HPF/DTS/FSBL 和板级 GP 验收未完成**。接线、共同复位与启动依赖见 [GP_INTEGRATION.md](GP_INTEGRATION.md)。既有运动 RTL、接口与 Golden 文件没有修改。

## 仿真结果与行为

| 实际入口/环境 | 结果 | 主要覆盖 |
| --- | --- | --- |
| `tests/run_gp.py`，Icarus 12.0，Verilog-2005 | 独立 GP 3,822 检查通过 | AW/W 先后/同时、字节写、读写独立并发/背压、非法写无副作用、完整33bit窗口/高位别名拒绝、NOP/错误/重复/倒退/忙/编号上界；变化源四轴整帧与 signed64/u64 边界；masked事件、持续源/set-clear同拍/重新触发；取消全部命令阶段、半笔AW/W与阻塞R/B；1MHz时间及u64回绕 |
| 同入口，Questa Altera Starter 2025.2，真实当前 TD 受保护库 | 集成 7,216 检查通过，compile/simulation 零错误/警告 | GP ACLK 同源、两级复位释放、AXI3 ID12、INCR三拍写/两拍读、RLAST/BRESP/RRESP、背压/byte strobes、A33高位别名拒绝、NOP/SNAPSHOT、空闲四轴快照、IRQ解除/屏蔽/重新触发、转换器AW/W/B/AR/R在途复位 |

独立模块的事务内部延迟：SUBMIT AW/W 配对写副作用发生后，第1拍校验、第2拍采样整帧、第3拍发布ACK与事件。快照采样上升沿前已登记值，ACK晚一拍；重复 SNAPSHOT 不重新采样。新的合法 ID（含 BAD_COMMAND）在应答发布时更新 LAST_TXN_ID；busy期间不会接收另一个SUBMIT。Lite AW/W 无等待配对之外的 ready 门：分别捕获、随后一拍配对/写副作用，B/R 在背压保持；不能将这个延迟视为 PS 访问耗时或运动 duration。

真实转换器本批验证普通 MMIO 及选定 INCR突发；没有宣称 AXI3 全协议认证（全部 WRAP、LOCK、跨 ID 数据交织/所有 burst-size 组合未穷举）。Linux 首轮使用白名单32bit对齐 MMIO；非法CPU访问不用于制造 external abort。全部端口参数与未修改厂商源 SHA256 见 `GP_SIM_RESULTS.json` 和 `GP_TD_RESULTS.json`。

## 实际 PS 边界最终验收

实际PS不提供WID，SIZE2/LOCK1。`gp_ps_control_top` 明确补零并用单笔AW–B所有权适配（WLAST后阻止后续W），保持冻结A33/D32/ID12和寄存器契约。独立适配器Icarus3,167检查通过；通用AXI3及实际PS封装的真实厂商转换器Questa自检各7,216检查通过。实际PS HDL端口、复位/IRQ绑定和SHA记录于 `GP_PS_PORTS.json`；未改变厂商原始源。

**最终PS封装**重新执行TD（`build/td_gp_ps_final`，固定10ns、参考speed2）：gate SWNS+3.013ns；place +5.451ns；route SWNS+3.533ns、HWNS+0.025ns、STNS/HTNS=0。最终最差路径 txn_shadow[6] → txn_shadow[18] 的写使能，6级，数据路径6.290ns（cell1.340/net4.950）；最小周期6.467ns、Fmax154.631MHz，仅为该OOC夹具。

最终PS夹具gate 1,144 logic LUT/177 adder/2,981 registers，其中边界内核1,109 logic LUT/177 adder/2,734 registers；route 1,317 logic LUT/130 adder/3,015 registers/2,397 slices（4.57%），DSP/ERAM0、GCLK1/SCLK4。含164位输入和83位观测寄存器；所有权ID在TD的非交织转换分支中可合法优化，不能据资源推算缺失的PS WID端口。STA coverage99.55%，HIGH检查0，观测夹具仍缺3个input delay/1个output delay。

实际PS封装的最终源/厂商库/约束SHA已匹配；结果在 `GP_TD_RESULTS.json.ps_boundary`，版本化报告以 `ps_` 为前缀。较早通用AXI3夹具的结果保留在下节，不能代替最终PS封装时序。PS硬宏、FSBL、完整系统布线和板级GP仍未验收。

## TD 10ns 与资源（较早通用AXI3夹具）

工具 TD 2026.1 SP2 / 6.2.2.200067，DR1M90GEG400，**参考 speed=2，非实物已确认等级**。夹具把 GP 输入串行加载到180位寄存器、将响应串行观测于83位寄存器，保持转换器和所有 GP 寄存器通道；四轴为冻结首轮空闲源。不是板级 GP/PS 引脚布局，不含PS primitive及系统资源。

| 阶段 | setup SWNS | hold HWNS | 结果 |
| --- | --- | --- | --- |
| optimize_gate | +3.015ns | 0.000ns | 门级估算通过 |
| place/manhattan | +5.676ns | 0.000ns | 放置估算通过 |
| route/final | +4.186ns | +0.033ns | 最终 OOC setup/hold 通过，STNS/HTNS=0 |

门级最差路径为共同 reset_release[1] → 转换器 WR/wrap_cmd/axaddr_wrap[0]。最终布线最差路径为寄存器 argument[22] → result_error[0]，报告最小周期5.814ns/Fmax171.999MHz；不据此提升冻结100MHz或承诺实板速度。布局布线运行了正常hold修复，没有关闭hold检查、放宽时钟或添加时序例外。

门级夹具1,154 logic LUT、177 adder、2,995 registers；其中寄存器模块468 logic LUT、99 adder、624 registers（空闲快照输入被合法常量折叠）。最终夹具1,303 logic LUT、130 adder、3,023 registers、2,400 slices（4.57%），DSP/ERAM=0、GCLK=1、SCLK=4；含263位观测/加载寄存器，不能作为最终PS系统资源预算。

STA coverage99.56%。最终 `check_timing`：无时钟/时钟问题/无效约束/组合环/悬空节点均0；观测夹具仍有3个无input delay、1个无output delay，真实PS集成必须重新约束。gate 阶段有厂商转换器 dangling LUT诊断，最终route已为0；不隐藏中间诊断。route checker已执行pin-swap/net-connection/LUT-bridge/multi-drive/clock/abnormal-path检查，无错误诊断；本版本没有生成请求的route.drc，真实console片段单独保存。

当前构建：`build/td_gp_verified`，版本化原始摘要/首条关键路径/area/checker/失败诊断位于 `reports/gp_20261012`，完整实际结果与原报告SHA见 `GP_TD_RESULTS.json`。首条路径文件只含summary与第一条路径，完整多路径raw报告留build；文本入库仅去尾随空白。

## 历史失败与修复

- PS写适配器初始TB在驱动m_wready后同一delta立即检查连续赋值，产生一次失败；添加#1采样相位后通过，没有改RTL或放宽原断言。随后复核增加WLAST后W阻断逻辑及专项断言，防止旧ID吞入下一笔数据；最终适配器3,167检查及两个真实IP顶层各7,216检查通过。

- 实际 TD IP 的 Icarus 集成编译在 `pragma protect` 处失败；这是工具不支持受保护库，不是已经通过的集成结果。独立模块继续使用 Icarus；真实IP改用可用且能解读官方保护格式的Questa。不修改或解密重写库，不使用行为stub。
- 初始Questa `-c` localhost IPv6 RPC初始化失败；随后绝对物理路径作为 `-lib` 也失败。官方 `-batch work.tb_gp_control_top` 正常运行，零错误/警告；未改许可证。
- 初始 IpTool batch尝试 exit1、没有生成wrapper，诊断保留。最终采用安装库的正式参数化 Verilog 直接实例化，明确不宣称 wizard/XML生成成功。TD确实解读并综合了该受保护实例，Questa确实执行了它。
- 初始 TD include 不生效；实际版本拒绝手册里的read_hdl `-included_dir`。构建忠实展开唯一生成header后标准analyze成功；没有复制维护另一套常量。

## 既有回归与剩余事项

本轮实际重跑：单轴三个参数夹具共236,273检查及tb_contract通过；四轴12组9,710,041检查、3,360安全/840复位扫描；连续组件FIFO深度2/3/8、planner753/executor1665及22组集成6,065,980检查、2,700取消扫描全部通过；接口8项、生成4文件一致、实际HDL822常量通过。既有Golden数值样例核对通过，未改或重新执行Golden算法全套基线。

已完成read-only实际PS端口核对（A33/D32/ID12、无WID、SIZE2/LOCK1、f2p_irq16、p2f_rst0_n），见 GP_PS_PORTS.json。未完成：完整地址图/HPF/DTS审核、FSBL GP使能/共同复位释放、整系统真实时钟/复位/内部路径约束与时序、bitstream/启动镜像和板级 MMIO/IRQ/快照/恢复。BSP任务维护这些工程和部署；PL提供实现及上述证据。首轮无运动输出、无DMA，不把ACK当作运动完成。
