# RS485 GP profile 确认契约

2026-10-14；基线采集器提交2792c66。用户三组回复全部接受；资源是独立开发候选，未授权部署。唯一规范已按本契约扩展。

## 资源审计与入口

建议 `gp_rs485_v1`：0x80700000/4KiB，A33/D32，小端寄存器，100MHz同源AXI-Lite；IRQ f2p_irq[4]、SPI86/INTID118，高有效level。

当前BSP展开DTS `bsp/artifacts/gp-release/debug/gp-board.expanded.dts` SHA256=d6e19f633918c8f982c9eafa0ebe77e784f7a4d2142a4d6a4914bdb882d6c1fe：按现有DMA审计方法检查数字四cell CPU资源（含disabled），候选窗口无重叠；interrupts文本无86/0x56匹配。现有唯一schema保留GP probe 0x80400000/IRQ0/SPI82、DMA 0x80500000/IRQ1/2/SPI83/84、motion 0x80600000/IRQ3/SPI85。现有PS连接为16bit f2p_irq。

以上仅证明当前可解析资料未发现冲突，不证明最终HPF decode或中断映射空闲。SPI86是沿用既有映射的候选，最终HPF、完整DT、中断控制器映射须BSP审核。当前三路Lite路由未提供第四入口；交付独立从机，BSP随后扩展现有路由，不新增PS全AXI转换器，不修改当前运动/DMA顶层。

## 寄存器分组

|偏移|寄存器/块|语义|
|---|---|---|
|000/004/008/00C|VERSION/PROFILE/CAPS/FEATURES|RO；version1、profile 0x31533552（R5S1）；能力位明确配置、整记录捕获、统计快照、IRQ、版本旁带；无DMA/DDR功能|
|010/014/018/01C|RUN/STATUS/GENERATION/LOCAL_RESET|RUN bit0启停新轮询；复位RUN=0；LOCAL_RESET全字写1，仅RUN=0且无事务/配置在途时接受|
|020/024|IRQ_PENDING/IRQ_MASK|W1C/RW，复位0|
|028/02C|LAST_ACCESS_ERROR/FIFO_LEVEL|最近非法访问原因/当前水位；错误不替代AXI RESP|
|040..050/054/058/05C|SHADOW_PERIOD[5]/MASK/TXN_ID/CFG_SUBMIT|周期顺序30、33、39、3A、3E；提交全字写1，捕获完整shadow|
|060..07C|CFG_RESULT|accepted/pending/applied/rejected、txn_id、原因、revision、apply_sequence、apply_us64、generation|
|080..098|CURRENT_CONFIG|五周期、mask、load；跨多字一致读取使用统计快照|
|0A0..0BC|记录控制/元数据|CAPTURE写1、CAPTURE_ID、VALID/READ_BITMAP、GENERATION、REVISION、CONSUME_ID、ABANDON_ID、LAST_CONSUMED_ID|
|0C0..0DC|RECORD_WORD[8]|冻结记录，word0=record[31:0]；读无pop；未捕获读SLVERR|
|100/104/108/10C|SNAP_REQ_ID/SNAP_SUBMIT/SNAP_STATUS/SNAP_ID|全字写1提交；最近ID重放不重新采样；快照状态含valid及ID|
|200..27C|快照公共头|同拍系统time_us、generation、配置/结果、FIFO/采集/总线计数；只读|
|280..31C|快照节点[10]，stride16|failure/offline、cooldown_us64、backoff_entries；未配置节点0|
|340..97C|快照任务[50]，stride32|scheduled/sent/valid/missed/max_lateness_us及保留0；未配置任务0|

确认后字段、位号、具体错误码和上述地址由pl_interface/schema.json新增独立profile生成Verilog/C及表格。其余旧profile数值不变。未列偏移SLVERR，窗口外DECERR，高地址位不截断，不对齐/RO写/WO读SLVERR。

RW shadow、RUN、IRQ_MASK支持逐字节WSTRB，按合并后值校验保留位；WSTRB=0无动作OKAY。doorbell、ID命令与W1C要求0xf，其他非零strobes拒绝。AW/W分别缓存，每笔最多一次写副作用，R/B背压保持数据/RESP，一笔读和一笔写可独立在途。副作用在写配对执行拍发生，不等BREADY。

## 配置事务

非零32bit单调txn_id；同最近ID同完整payload重放缓存的pending或终态，不重发；同ID不同payload、倒退、ID0及有其他事务pending拒绝SLVERR。忙时可继续写shadow，但不改变已捕获参数。ID不回绕，耗尽后需整域会话重建。

SUBMIT合法时B=OKAY只表示桥已接受；桥持有cfg_valid直至collector cfg_ready，等待cfg_applied或cfg_rejected后发布终态。沿用采集器范围、mask/period=0禁用、750000ppm预算、不静默降频、revision耗尽拒绝；异步拒绝原因区分RANGE/LOAD/REVISION，保留此前当前配置。桥增加访问/ID/忙错误，不能冒充采集器应用结果。配置应用时刻记录系统time_us、revision和apply_sequence。

RUN=0允许在途逻辑事务含重试/隔离有界完成；无任何串口任意命令入口。上电及local reset后采集器仍验证既有兼容默认配置，自动结果使用txn_id=0，RUN保持0，不自动启动。

## 完整记录与配置关联

CAPTURE锁定FIFO队首的256bit副本，不pop；已有捕获时重放CAPTURE保持同ID/内容。空FIFO返回SLVERR且不分配ID。捕获ID为非零32bit单调、不回绕；耗尽拒绝新捕获。

PS可任意顺序/重复读取8个字；READ_BITMAP在成功RVALID/RREADY交付后登记。CONSUME_ID必须匹配当前ID且8字均已交付，才pop一次并释放捕获；重复确认最近已消费ID返回OKAY且不pop。其他ID/部分读取消费拒绝。ABANDON_ID匹配后只释放捕获、不pop，之后可重新捕获同一队首；旧ID失效。所有操作由软件串行化。新记录永远不覆盖锁定副本或未消费队首。

保留源256bit记录完全不变。建议给采集器增加只读入队事件/数据观测，桥以同样full+pop接纳规则维护独立、等深的revision旁带FIFO；版本在入队拍锁存，非读取拍贴标。捕获同时冻结generation/revision；旧配置记录可继续消费。PS保存每个(generation,revision)的已应用配置及apply_sequence/apply_us，自动revision1配置由已识别profile确定。不以sequence大小比较推断版本，因此源sequence自然回绕仍有效。旁带与记录一致性作为专门仿真断言。

FIFO满沿用整记录丢新、饱和dropped统计，绝不背压UART。首版FIFO深度仍8，不增改源记录；容量评估必须包含异常尝试记录及PS最坏服务间隔。

## 统计、IRQ与复位

建议给采集器增加只读并行统计输出，原debug选择接口及全部调度行为保留；桥在同一个100MHz上升沿锁存所有已登记统计、配置、节点和任务及系统time_us，禁止逐项扫描后宣称原子快照。同SNAP ID重放保持旧快照；新递增ID重新采样。快照保持至下一成功请求或local reset。

IRQ位：DATA、CFG_RESULT、COMM_ERROR、PROTECT_OBSERVED、FIFO_DROP、BUS_DIAGNOSTIC、RESET_DONE；mask/pending复位0；irq=|(pending&mask)，(pending&~W1C)|事件或持续源，同拍set优先。DATA在FIFO非空/有捕获时持续置位；先mask并批量排空，再W1C/readback/unmask，不能在非空时反复清IRQ。配置结果与通信失败、已校验3E=1保护观察、整记录丢弃和BUS_BUSY分别报告；诊断为离散事件，未读快照不自动停止采集或运动。

LOCAL_RESET仅静止时接受；不复位AXI端点、不截在途B/R，也不触碰time_us/运动。取消捕获及旁带、清采集FIFO/统计/快照/配置结果，RUN=0；generation32递增，collector revision/sequence按既有复位重建。桥txn_id/capture_id/snapshot_id单调水位跨local reset保留，旧未完成ID不可复用；重复消费缓存失效。generation耗尽拒绝reset，不回绕。pending旧事件清除，并以RESET_DONE通知；IRQ_MASK保留。已发未交付RDATA保持原AXI响应，软件在reset后检查generation并丢弃旧操作。

整域rst_n沿用系统启动/重配置会话复位，桥ID/generation重新初始化；PS按现有整域epoch协议重建会话，不宣称持久硬件epoch。独立运行中GP warm reset不在首版支持范围。

## 实现与交接范围

确认后完成独立RTL、mock寄存器C解码/访问示例、AXI和真实collector+模拟slave测试、既有回归、100MHz OOC综合/布局布线。只读观测端口属于必要的可观测性扩展：不改源协议、调度、退避、256bit记录、既有debug及运动接口；重新跑回归验证。BSP后续负责四路路由、最终地址/IRQ审计、DTS、驱动及服务，首版无/dev/mem、无S2MM或DDR遥测，不下板。

确认后的布局细化：SNAP_STATUS只含valid，SNAP_ID独立于0x10C，避免32位ID与valid打包损失位宽。CURRENT_CONFIG非快照跨字读取不承诺原子性，PS使用统计快照。采集拒绝码引用原rate_design.json，不新增第二份维护值。

实现标记时刻细化：CFG_TIME是桥采样cfg_applied/rejected脉冲的结果通知时刻；源revision/application_sequence已在前一100MHz边沿更新。跨1MHz边界可能差1us，精确版本切分使用入队旁带revision。
