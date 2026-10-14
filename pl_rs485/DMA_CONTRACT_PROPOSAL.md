# RS485 解析、最新缓存与DMA遥测：最小契约提案

后续选择：用户已选择独立controller，接受数据/缓存及容量/精确BTT/批量参数。本文保留原提案历史；controller、HP/IRQ资源、六端点路由及恢复范围由DMA_INDEPENDENT_ADDENDUM.md覆盖，待该增补确认。

2026-10-14，等待用户确认。采集/GP基线7a0d479，规划基线698834c。本文件是待确认方案，尚未扩展pl_interface规范、实现RTL或授权部署。

## 1. Controller、资源与兼容

推荐首版共享现有Anlogic AXI DMA controller：MM2S继续运动，S2MM用于遥测；沿用0x80500000、IRQ1/2/SPI83/84、真实HP0及原厂AXI4→AXI3转换器、同源100MHz。仅一条DMA memory master，不并联第二个master到HP0。共享意味着任一方向reset可能同时复位两方向并取消运动，不能承诺遥测恢复隔离。

备选独立controller可隔离controller reset，但必须另行启用实际HP1等端口或实现/验证HP0多master仲裁，并审核DMA窗口/IRQ/时钟和PS配置。本次读取的pl_dma/build/ps实际wrapper只公开已验证HP0，HP1等硬宏端口在内部绑零，不能把“硬宏存在”当已接通。若用户选择独立controller，先补审资源，再确认具体接口，不沿用共享方案的资源假设。

保留旧GP诊断FIFO8、0x80700000/IRQ4/SPI86、gp_rs485_v1的ID/features及捕获/8字读取/显式消费语义。新增独立profile `gp_rs485_telem_v1`，候选0x80800000/4KiB、IRQ5/SPI87/INTID119、level-high；原0x804/805/806/807窗口和SPI82..86不动。新增VERSION/PROFILE/CAPS/FEATURES，字段及错误码确认后从pl_interface/schema.json生成。

资源初审：bsp/artifacts/gp-release/debug/gp-board.expanded.dts SHA256=d6e19f633918c8f982c9eafa0ebe77e784f7a4d2142a4d6a4914bdb882d6c1fe。沿用既有数字四cell CPU资源扫描方法，0x80800000/4KiB无重叠，interrupts无87/0x57文本匹配；唯一规范现有资源至0x807/IRQ4。此结果不是最终HPF/完整DT/IRQ映射验收，BSP仍需复审。新独立验证顶层扩展现有Lite路由到五端点，不重复PS全AXI转换，不修改旧运动/GPIO默认顶层。

新profile地址分组：0x000..0x03C身份/状态/IRQ，0x040..0x0FC遥测控制/包握手/计数，0x100..0x1FC快照控制与全局快照，0x200..0x97F为15个128B缓存行。具体寄存器位号在确认后规范化；A33/D32、完整译码、WSTRB/背压/非法访问沿用旧桥的原则。

## 2. 不可变完成事件分支与消费权

从采集器observe_push/data（完整记录发布事件，含有效应答和异常尝试）分支，不从GP队首pop：

- 旧诊断FIFO由GP唯一消费；满仍丢新，原dropped语义不变。
- 轻量解析/缓存每次直接处理完成事件，不依赖任何FIFO接纳或消费者。
- 新遥测FIFO由打包器唯一消费，独立满/丢弃统计。GP不pop遥测FIFO，DMA不pop旧诊断FIFO。

事件同时锁存source generation、cfg_revision、transport_generation和64bit completion_serial。serial每个完成事件递增，包含后续被丢弃的事件，区别于源request sequence（一个请求的重试共用源sequence）。不在发送时贴当前revision。series/generation耗尽不回绕：拒绝新的相应传输/控制，保留缓存工作并报告诊断，整域会话重建另行处理。

## 3. 轻量解析与缓存

仅处理白名单30/33/39/3A/3E及E0/E1/E2，M4禁用，编译期地址表与既有采集器一致。30分别提供signed32 carry、unsigned16 value；33符号扩展到signed64的接收脉冲；39符号扩展到signed64的角度误差；3A/3E保留raw enum并独立给出known（1/2已知，其他值未知但仍可为协议有效数据）。不做机械标定/浮点、不修正运动命令位置、不新增自动停机。

15行各保存last_valid完整原始记录及对应generation/revision、last_result完整记录及标签、解析值、有效/已见标志。通信失败更新last_result，不覆盖last_valid；BUS_BUSY也保留原状态区分，不伪装驱动故障。只有原status=VALID且字段长度/版本/地址/查询合法才更新有效值；内部不一致单独诊断。

原子快照一次锁存全部行和统一system time_us。128B行建议包含flags、有效/最近结果标签、last_valid raw32、last_result raw32、signed64解析量、carry/value/enum/known、age_us64和stale_limit_us64；sequence/attempt/request/event时间由各自原始记录保留。不同查询仍异步，不能当同步15通道采样。

过期策略推荐每查询共用当前period：stale_limit=max(3*period_us,100000us)；无last_valid、禁用查询或age>=limit均标stale，另列disabled与last_result失败，不能混成一个“零值”。age使用unsigned64时间差，支持自然回绕，比较范围<2^63us。配置更新保留历史有效值及原revision；阈值按快照时当前配置计算并输出阈值，旧revision不被替换。

旧GP LOCAL_RESET仍按原条件接受，清缓存有效性并跟随新的采集generation；无额外独立缓存clear命令。配置更新、普通IRQ清除、遥测取消/DMA reset均不清最新值，避免把通信故障当零反馈。缓存复位后的旧解析流水事件不得重新置有效。

## 4. 遥测记录：新64B封装，旧32B保持不变

不是历史128B遥测草案。新记录固定64B，小端外层；内嵌raw字段仍按原源记录及大端payload解释。

|字节|字段|
|---|---|
|0..3|magic，候选0x31543452（R4T1）|
|4..5|version u16=1|
|6..7|length u16=64|
|8..11|collector_generation u32|
|12..15|cfg_revision u32|
|16..19|transport_generation u32|
|20..27|completion_serial u64|
|28..59|原始256bit记录，byte i=record[8*i+:8]，等价GP八个D32字各自小端存放|
|60..63|CRC32/ISO-HDLC，覆盖0..59，小端，poly reflected0xEDB88320、init/xorout0xFFFFFFFF|

64bit AXI-Stream每条8拍，KEEP=0xFF。外层不再重复发送解析值，由PS复用当前C decoder解析内嵌raw；GP缓存提供轻量解析后的最新值。CRC用于DDR封装完整性，不替代源CHECKSUM-8，也不赋予线上迟到帧新的可辨识性。

## 5. FIFO、批量与精确RX长度

推荐独立遥测FIFO256条（64B/条，总数据16KiB），满丢整条新记录，饱和统计full_drop；不阻塞采集/缓存/STEP。还区分disabled/not-admitted、取消清队列丢弃、包已交付stream、DMA完成/失败及源GP丢弃，不能把stream握手当DDR已完成。打包器至多另持有一条完整记录，单独计入容量，不把厂商内部缓冲算作本FIFO。

最多16条/包（1024B）；当队列达到16或最老待发记录满10ms，冻结队首N=min(count,16)及包ID/字节数，置PACKET_READY level。一旦冻结，N和包身份不随新入队改变。低速1条也会在10ms形成64B短批，不等待凑满。无数据不发空包。

采用精确长度握手：PS读取稳定的packet_id/generation/N，先准备>=N*64的DMA buffer并提交**恰好N*64字节**的S2MM descriptor/issue_pending，再向新GP profile提交ARM(packet_id,transport_generation,bytes)。ARM字段必须完全匹配、ID不重复执行；没有ARM credit不向DMA提出VALID。buffer实际容量可以1024B，descriptor长度按本包实际字节，不假定容量=实际数据长度。

10ms是包槽空闲时形成PACKET_READY的时限；已有包等待ARM/发送/确认时不覆盖它，到期记录在包槽释放后立即具备冻结资格。PS提交/ARM服务延迟、前包占用、DDR背压另外计量，不承诺在无RX buffer或无限背压时10ms到DDR。READY时限、等待ARM及发送背压各有统计/最大延迟。发送开始后不再等待新记录，TLAST仅在本包最后记录的第8拍，稳定保持所有sideband直到握手。最后stream拍产生STREAM_DONE；PS须等DMA IOC/错误结果，再显式确认该包，才可ARM下一包（simple模式一笔RX在途）。

现有只读驱动事实：bsp/dma/provider/axi-dma.c及bsp/motion/provider/axi-dma.c的simple完成路径将desc->residue=0，tx_status完成路径直接返回。因此不能靠requested-residue推导提前TLAST短包长度。现有真实DMA回环bench只证明“BTT等于TLAST字节数”的S2MM长度回读；BTT较大时提前TLAST行为尚未验证。

确认后用未经修改真实Anlogic DMA/HP converter单独探测BTT>packet、过小BTT、提前/缺失TLAST、S2MM_LENGTH/IOC/错误、DDR guard字节；记录结果，但生产路径保持精确BTT，不依赖不可靠的simple residue。BSP核对实际接收长度来源，必须与冻结N*64、完成包ID及CRC一致；callback成功本身不证明DDR数据完整。若连精确BTT路径验证失败，报告阻塞，不以stub或静默协议切换代替。

## 6. DMA取消、复位与generation

transport_generation独立于collector_generation及系统epoch。上电telemetry enqueue关闭、无ARM；软件在确认controller/DDR静止后显式RECOVER新非零递增transport_generation，清旧传输队列/半包/credit，再ENABLE接纳新完成事件。关闭enqueue仅停止接纳新遥测，不撤回已经提出的VALID，也不停止采集/缓存或在途包。

取消采用CANCEL_REQ→禁止新包/新ARM并锁存cancel_pending。若已有VALID/在途DMA，不能仅撤VALID或清FIFO宣称取消成功；保持协议，等待BSP终止/协调controller reset并证明DDR静止后显式RECOVER。无在途包/无held VALID时可以清队列报告本地取消完成，但仍不等于DMA/DDR静止证明。

任一真实primary reset立即阻断旧传输，清遥测有效队列/半包/credit并保持CLOSED，恢复必须新transport_generation；不自动重新打开、重放旧包或恢复旧运动。共享controller reset照旧取消MM2S运动会话，保持实际位置及系统时间，不改原STOP/安全排空契约。

S2MM错误恢复由BSP共享controller生命周期owner执行：阻断新运动/遥测提交→运动GP STOP并等pulse-safe→terminate_sync相关方向→协调reset并确认HALTED、reset/中断/tasklet/callback与在途DDR静止→失败buffer quarantine→新transport generation显式RECOVER、重新投RX再ARM。新运动必须另外建立新session/显式启动。不可把普通无RX buffer/FIFO满当作触发该取消流程的故障。

旧GP采集LOCAL_RESET不改变其行为，也不擅自reset DMA：缓存无效、新事件使用新collector_generation；已经入遥测队列/在途包可按原不可变collector_generation送完，不改贴新generation。包可含多个collector_generation，但**同一transport_generation**，每条自带完整标签。若要求丢弃采集复位前遥测，PS应另走显式取消/恢复，不能把尚有AXI有效拍的局部清空当安全取消。

共享DDR带宽/仲裁仍可能影响运动MM2S供给，本批不承诺总线绝对隔离。正常遥测背压/FIFO满不连运动fault/STOP；真实controller复位导致的取消属于已确认共享作用域。

## 7. IRQ、快照与统计

新profile IRQ使用pending&mask、level、W1C同拍set优先；PACKET_READY为持续源，packet result/传输故障/cache解析异常/FIFO drop分别锁存。旧GP IRQ/配置/诊断保持，不重复制造逐记录中断。cache快照包含全部15行同拍数据，计数/包状态/两种generation及统一time_us一并冻结。计数饱和且溢出可诊断；无自动停机策略。

## 8. 验证及交付范围

确认后扩展唯一规范，实现独立解析、缓存、FIFO/CRC/AXIS打包、新GP及显式opt-in共享DMA验证顶层。真实受保护IP用Questa，不用stub作最终证据；DDR模型核对实际字节、guard、metadata、CRC/短批/背压/错误与取消。运行受影响RS485/GP/DMA/运动回归，交叉核对现有C解码，独立连续STEP参考比较。

100MHz综合与布局布线分组件与整体报告；整体含一套真实DMA/转换器/互连，层级资源不与单元scan夹具相加重复计算。真实PS/HP0接线/时钟与现有规划核对，不修改BSP/Golden/运动GPIO默认行为，不下载板卡、不接电机。保留旧源码/证据，最终Git提交及RS485_DMA_HANDOFF.md交接后停止。BSP后续负责统一路由/DT/驱动/buffer所有权/共享取消生命周期及实板验收。
