# DDR / DMA / Linux 接口契约 — Draft

> 2026-10-12：用户已确认独立数据通路 profile `dma_loopback_v1`，见唯一 `schema.json/dma_loopback_profiles` 和 `../pl_dma/DMA_HANDOFF.md`。本批新增0x80500000/4KiB、IRQ1/2（SPI83/84）、32bit DMA地址、64bit memory/stream、同源100MHz、simple双向/BTT16/burst16/DRE/SF、16拍回环FIFO及双方向取消恢复契约。原GP资源保持。本页下方80B/128B记录与运动/遥测软件环仍为Draft，不据回环验收冻结；本批不接运动FIFO。当前PL真实IP仿真及OOC/隔离PS参考时序通过，不代表Linux DMAengine或DMA实板验收。

## 1. 首批选择已确认，集成行为待验证

用户已接受Anlogic AXI DMA / HP0 / 64bit stream / simple模式 / 每记录一packet / Linux DMAengine验证。该确认不代表板上回环通过或其余DDR/cache参数冻结。

推荐Anlogic通用AXI DMA、HP0、MM2S轨迹DDR→PL、S2MM遥测PL→DDR，64bit内部stream、32bit Lite控制，经实际工程互连适配。首批simple direct模式+Linux DMAengine验证回环；scatter-gather/cyclic作为后续选项，不能从驱动源码支持推定当前生成IP已启用。FDMA的请求/长度和视频VDMA帧语义不直接等于运动点协议。

第一版为“一条记录一个stream packet”，motion 80B / telemetry128B，TLAST at末拍、全keep；DMA描述符或direct transfer不得跨/切断记录。批量由多个描述符/transfer组成，不额外在每点插控制字节。若首批simple模式吞吐/提交延迟不能覆盖PS最大生产周期，必须增加预缓存或确认SG/自有packetizer版本；不能将任意bulk DMA长度直接套入此候选。packetizer另需定义传输长度与TLAST，本阶段不默认实现。

CRC/长度在记录层检查，DMA BTT/descriptor length在传输层检查；DMA完成、记录接收、执行done三种通知独立。S2MM精确128B接收buffer，必须先预投足够buffer再允许遥测；异常长包让DMA报错并按恢复契约处理，不覆盖相邻内存。

## 2. 地址、容量与所有权

Linux kernel负责人使用dma_alloc_coherent或DMAengine支持的映射API；dma_addr_t来自设备DMA映射，绝不是用户态指针或简单virt_to_phys。物理地址、DMA/bus地址（可能IOMMU/映射）、kernel虚拟地址、user虚拟地址必须分开表示。用户态不写DMA IP寄存器或提交任意地址；本阶段只给契约，不实现驱动。

地址范围取生成IP地址位宽、设备dma mask及Linux映射返回结果的交集；样例DMA AXI addr32不能据CPU64位推定可达64位DDR地址。单条记录8B对齐；分配/映射还满足设备burst/cacheline/page要求取最大值（具体TBD）。每buffer整记录容量，byte_count溢出checked。不复制裸机固定DDR地址；如用reserved-memory必须由DTS唯一保留并避免kernel/bootloader占用，CMA/coherent为推荐首批方式。

Motion容量N_m：至少cover ceil((Linux最大提交间隔+DMA恢复/仲裁裕量)/最短duration)+预取；数据80*N_m checked。Telemetry容量N_t：cover peak_event_rate*(最大回收延迟+裕量)，128*N_t checked。FIFO深度/预缓存低水位、DDR pool容量、最坏DMA带宽/IRQ负载待测试，不任意冻结容量。motion/telemetry/staging不能共享可变buffer所有权。

候选软件环索引（存在kernel，PL不直接读取DDR索引）：PS生产motion_prod，kernel completion推进motion_cons（表示DMA释放，不表示执行）；kernel/DMA完成推进telemetry_prod，用户消费推进telemetry_cons。单生产/消费、u64单调索引、距离<=capacity，wrap需受控重建。kernel唯一拥有DMA描述符；用户不得改consumer以覆盖仍由DMA持有的数据。PL另有accepted_seq/done_seq与FIFO occupancy，不能混用DMA消费索引。

## 3. 提交、cache与映射

motion：用户写payload→release发布可提交槽→kernel acquire读槽并验证长度/session→streaming mapping用dma_sync_single_for_device(DMA_TO_DEVICE)，coherent仍dma_wmb保证内容先于描述符所有权/doorbell→dmaengine_submit/issue_pending→completion标记buffer归PS。发布索引前buffer必须不再被用户改写。

telemetry：kernel预投device-owned buffer→DMA完成→确认transfer status/length→streaming用dma_sync_single_for_cpu(DMA_FROM_DEVICE)，coherent用适当dma_rmb→kernel release发布→用户acquire读取/解码CRC→用户释放→kernel同步for_device再投。单纯CPU内存屏障不等于cache维护；映射属性由kernel/DMA API决定，用户mmap由dma_mmap_coherent或受控等价API建立，不能允许/ dev /mem绕过所有权。coherent支持与HP端口一致性需板上核对，不假定HP自动snoop。

AXI MMIO用readl/writel；命令payload先写完成、barrier后doorbell；必要读回保证posted write顺序由驱动适配。并发客户端由kernel单writer锁保护，不用用户进程各自操作影子寄存器。

## 4. 背压、错误与恢复

MM2S背压只影响记录预缓存，已启动脉冲不等待DMA。记录适配器只ready于完整记录资源足够；FIFO满不覆盖旧点。区间边界欠流触发候选停止，不临时拉长点。Telemetry full丢完整帧并统计，不停止脉冲；统计包括accepted/rejected/stale、underrun、telemetry_drop、DMA_error、comm_fail，使用饱和计数，清计数必须独立停止态事务，不能清故障顺带丢证据。

DMA错误/terminate/reset：先由PL停止并锁存session invalid、阻断新记录提交；kernel dmaengine_terminate_sync并确认不再访问buffer；排空/复位两个方向适配器的半包、异步FIFO握手；PL确认quiescent后释放buffer、建立新DMA generation与新session。旧descriptor callback和旧buffer使用generation拒绝；重新下发需从最新实际位置快照规划。仅reset DMA控制位不能证明流尾字节或FIFO已清。GP复位、PL重配置和Linux重启同样不得保留旧session；只有显式恢复完成后START，EN恢复仍TBD。

DMA错误停止的脉冲safe时序见整体文档；DMA reset不能直接复位运动位置或时间戳。故障遥测可能无法到DDR，GP fault latch/IRQ为独立报告通路。
