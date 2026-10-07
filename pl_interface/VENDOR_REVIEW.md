# 本地厂商依据核对

2026-10-07再次只读检查HARDWARE §10指定资料。可重复脚本vendor_audit.py记录路径、原文件SHA256和相关行到vendor_evidence.json，未解压落盘、未编译/修改示例。证据根：D:\Works\Embedded_contest\docs\Analogic。以下是工程/源码事实，不是实板能力验收。

| 来源 | 本次核对事实 | 本项目选择与限制 |
| --- | --- | --- |
| Linux Sourcecode/16.plint | plint.c:50 request_irq(...IRQF_TRIGGER_RISING)；kernel DTS:197 interrupts=<0 82 4> | 驱动触发标志与DTS需统一；不能复制IRQ号。项目候选锁存level中断需匹配最终GIC配置 |
| Linux Sourcecode/17.axi_gpio | axigpio.c包含request_irq、ioremap/ioread/iowrite，DTS同中断资源；硬件system连接GP/转换器 | 只证明GP控制和中断示例存在；不用GPIO地址作为机器人地址，也不把示例当DMA Linux集成 |
| SDK基础17_axi_DMA / DMA wrapper | Lite addr10/data32；MM2S/S2MM address32、memory/stream data64、keep8、last/valid/ready；MM2S tid/dest5、user4；独立mm2s_introut/s2mm_introut | 本项目64bit流候选有依据；sideband不作为机器人字段，unused常量/接收忽略需adapter核对 |
| 同wrapper parameters | AL_INCLUDE_SG=0、双向=1、DRE双向=1、burst16、SG_LENGTH_WIDTH=26、AL_PRMRY_IS_ACLK_ASYNC=1；Lite80MHz、MM两向150MHz参数 | 这些是生成工程配置，SG length参数存在不代表SG已启用；DRE不免除项目记录对齐。IP异步属性不代替本项目stream CDC |
| ARM wrapper / protocol converter / matrix | master_gp0 addr33/data32/ID12，HP0 addr32/data64/ID6；GP转换下游addr32 Lite；matrix下游HP0 data64；PS f2p_irq16 | GP要full→Lite转换并核对33→32bit地址窗口；不能忽略高位alias。HP0候选不是全部HP能力结论 |
| SDK system.v | Lite/GP接PLL clk0；HP0/HP1/DMA MM/stream接PLL clk1；DMA interrupt经concat进入f2p_irq | 时钟与wrapper频率参数互相核对后再导出HPF；项目运动100MHz另域，不原样替换demo所有时钟 |
| SDK axidma_s2mm_mm2s/main.c | 双向HAL、cache维护/中断、裸机DDR收发 | 证明示例接口操作链，不复制固定地址，不当Linux cache/所有权方案 |
| BSP tar sources/linux/drivers/dma/anlogic/axi-dma.c | device_prep_slave_sg、device_prep_dma_cyclic、描述符coherent分配、双通道中断/复位流程 | 源码能力存在，simple/SG对应IP/DTS分支需集成验证；不能直接推定所有模式可用 |
| 同axi-dma-test.c:119–171 | dma_request_chan(axidma_mm2s/s2mm)、dma_alloc_coherent、dmaengine_prep_slave_sg双向 | 首批DMAengine参考；测试是SG提交，不证明当前SDK SG=0工程与测试能直接配套 |
| 培训fdma_test / uiFDMA.v | 默认AXI地址32/data64/ID6、burst16、16bit rsize/wsize、req/busy；wvalid/ready命名为自定义消费语义，例O_fdma_wvalid=w_next | 必须做语义适配，不能把同名valid当标准AXI-stream。不能直接复用作motion FIFO接口；该fdma_test的PS f2p_irq接16'b0 |
| 培训fdma_vdma_tpg / main.c | 视频多帧VDMA/FDMA与中断控制 | 帧缓冲不等于记录/轨迹边界；本项目先用通用DMA候选 |

培训TPG当前引用的system/ip/system_VDMA_0 wrapper：MM2S stream64、S2MM stream32，不能统称所有方向都是64bit；MM2S/S2MM中断经concat进入f2p_irq。目录还有`.ipName.customize`旧配置副本，不能据副本当当前工程端口；审计脚本排除这些副本。HPF既有核对VDMA输入133.32MHz、VTG49.995MHz（HARDWARE §10），不是项目运动100MHz。

证据脚本保存过滤行，审查完整上下文应打开原文件；SHA便于识别版本改变。BSP相关Kconfig开关、最终.config/DTS、simple模式匹配、IRQ路由、最大BTT、S2MM TLAST与停止/残留、throughput/背压均未在板上验证。

HARDWARE既有板级问题持续保留：示例DDRC_IO_VOL=1.5 vs用户基线1.35V；旧TD/HPF/IP与TD2026.1 SP2/FD2026.1 SP1适配。接口设计不替代这两项核对，也没有改板级配置。
