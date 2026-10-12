# DMA PL 验证记录 — 2026-10-12

已接受 profile `dma_loopback_v1`，当前为 PL 仿真及参考时序验证；DMA未经板测。完整交接见 DMA_HANDOFF.md。失败和warning均保留，未用stub、放宽时钟或时序例外替代验收。

## 功能

- Icarus12自研FIFO：深度2/3/16分别16,053 / 15,942 / 16,365项检查通过。填满后保持、满空边界、并发推拉、随机DATA/KEEP/LAST/USER/ID/DEST、反复reset和旧队列取消；空队列不发valid、复位不接收。
- Questa2025.2真实当前DMA＋真实AXI4→AXI3转换器：独立入口21次传输、162,206项检查。共享GP0入口21次传输、159,606项检查，满载occupancy16；共享原GP回归7,632项检查通过。
- 传输长度1、7、8、9、15、16、31、127、129、255、256、4095、4096、4097、65535、8193字节，以及在途reset恢复17/18/19/20字节和协调DMA reset后33字节。模式递增、固定A5、乘37扰动、反码；字节逐项比较、目标前后guard、末拍KEEP与TLAST计数、实际S2MM length、IOC/error status和IRQ W1C。
- HP地址/LEN/SIZE/LOCK/ID/QoS检查，AR/AW/W/R阻塞保持，延迟B响应；长时间写背压推动FIFO满16拍，恢复不丢数据。GP/DMA交叉读写归属以及DMA期间原GP scratch访问通过。
- AW先到/W先到，R/B保持；DMA A33高位alias、窗口外/保留3KiB/未对齐/非完整WSTRB拒绝，零BTT/65536B/未对齐DDR地址/非零address-MSB写拒绝。
- 4个不同在途偏移whole-domain reset＋partial packet软件reset恢复均通过。模型内DDR slave在whole reset时同步清交易，因此不证明硬PS上的在途取消/内存静止；软件在板上仍必须正确terminate、两个方向reset和buffer代际管理。
- 契约结构5测试通过；既有常量逐项不变，接口生成物与唯一规范完全一致，HDL核对884个常量。
- 原有单轴3夹具＋tb_contract、四轴12组、连续组件＋22组、GP组件/原PS封装/通用封装、接口8测试及Golden Model回归通过。连续6,065,980检查、2,700个取消偏移；Golden基线未修改。原GP_SIM_RESULTS.json字节保持原批次。

## 时序与资源

TD Release_2026.1_SP2.200.067，DR1M90GEG400，**参考speed2**，固定10ns；未加false path/multicycle或减弱测试。不生成部署镜像。资源以route.area为准，LUT统计包含逻辑/adder等，两个口径分别报告，不混称裸DMA。

| 最终工程 | Gate setup | Place setup | Route setup | Route hold | LUT6 / FF / slice / ERAM |
|---|---:|---:|---:|---:|---|
| 共享GP/DMA OOC观测夹具 | +1.978ns | +5.060ns | +2.956ns | +0.026ns | 3414 / 6030 / 4851 / 18 |
| 隔离真实PS＋GP0＋HP0参考 | +1.978ns | +4.703ns | +3.117ns | +0.020ns | 3279 / 5540 / 4645 / 18 |

OOC含250位输入和279位输出观测寄存器（以TD_RESULTS.json的probe_register_bits为准）；不会把这些包装资源全部报作DMA IP资源。PS参考使用H16/LVCMOS33，实际生成PS raw，原厂属性仅映射实例路径，IOPLL400/P2F_DIV8不替代100MHz。STA coverage99.99%；GP `GEN_PL_GP0S` 和HP `GEN_PL_HP0`均100MHz，真实PS捕获路径存在，critical warning0。PS参考全局最差setup3.117ns位于HP捕获通路，完整报告含source/capture传播。

OOC check_timing：无时钟0、无效约束0、组合环0；未设input delay3/output delay1，自动IO的SYN-6021仅为观测夹具诊断，原始log保留。PS参考IO delay缺项0、critical warning0；两个工程仍有原厂内部dummy node2。checker详细列出原厂ERAM未用reset端及LSLICE未用输出，未擅自修改厂商IP或删除诊断。BSP须在最终工程审核；本交付不是board STA/DRC全项签核。

Questa49个warning均在原厂受保护DMA/HP转换器内部，不含自研公开端口宽度或缺失连接；未关掉warning。功能测试通过不等于全AXI事务/厂商IP认证；没有SG/cyclic、非8B对齐DDR地址、多master竞争、bus error注入、吞吐/DDR/cache压力或实板中断恢复认证。

## 失败与纠正

1. 首次真实DMA编译569 errors在protected区域：仅加入axi_dma.v，缺原厂文件集中两个vh。随后原样stage两vh并提供include目录，编译/仿真通过；不修改保护内容。first_failure log保留。
2. 隔离xmlipgen第一次缺 `.m_params`元数据而报告错误。补齐复制的厂商metadata，原始RTL生成成功；HP data width使用参数表达式，审计解析器随后正确按默认64求值。BSP原文件未修改。
3. 首轮OOC wrapper的SYN-6021造成严格诊断入口拒绝；当前只对明确OOC自动IO这条诊断分开记录，其他critical warning和ERROR仍拒绝。真实PS参考用H16约束、无该诊断。
4. 原GP fixture time0假定bit1–15永不使用；共享DMA IRQ是live输出。补齐idle HP输入连接，在该fixture时钟检查后加1ns组合settle；保留原GP所有行为检查。DMA RTL显式在common reset期间屏蔽IRQ。初次失败未当PASS。
5. 隔离真实PS接线首次发现HP ARQOS/AWQOS缺失。按实际原厂生成端口补齐，仿真检查均为0并对最终源码重跑OOC/PS布局布线；未假定旧示例完整端口正确。

## 证据与身份

`reports/evidence.zip`保留原始报告/日志字节，不改写warning或尾随空格；`reports/index.json`记录每项SHA256。完整数据库为build可再生产物，不入库。验证脚本拒绝IP/源/规范hash改变后沿用旧timing与sim记录。

尚未验证：新两路GIC实板映射、Linux actual driver binding/DT/probe、DMAengine回环、HP启动reset/cache所有权、DDR供电/训练/容量压力、实物speed、运行中硬PS reset/取消静止和长期吞吐。原GP板测仅作独立基线，不延伸为DMA证据。
