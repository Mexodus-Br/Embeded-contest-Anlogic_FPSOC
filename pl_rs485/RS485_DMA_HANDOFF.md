# RS485轻量解析、最新值缓存与独立HP1 DMA遥测交接

2026-10-18：SAF2联锁从实际提交事件独立分支，FIFO满、遥测HP1背压或PS不读取不能
屏蔽保护检测；原64B遥测、32B采集和DMA缓冲生命周期不变。
新增行为/真实双DMA验证状态见[合并交接](../pl_safety/INTERLOCK_HANDOFF.md)。

本交付独立验证，尚未系统集成或实板验收。未修改BSP、Golden、原运动/GPIO默认顶层、启动镜像，未下载板卡或接电机。基线7a0d479，最新规划698834c。用户于2026-10-14接受DMA_INDEPENDENT_ADDENDUM.md：独立S2MM-only controller/HP1及局部恢复；原提案的共享controller建议已被覆盖。完成交接后停止，BSP统一接入。

固定源码为本交接提交，逐文件源码/IP/规范/配置/夹具/证据SHA256见evidence/identity_telemetry.json。原协议schema.json/rate_design.json及32B记录不改。唯一ABI来源pl_interface/schema.json新增rs485_telemetry；全局generate.py和tools/generate_telem.py生成PLI_TELEM_/RT_定义，旧GP、DMA、运动及RS485 profile数值不变。旧生成文件banner哈希随完整schema变化，BSP导入时必须按同一提交整体更新定义，不覆盖历史镜像身份。

## 接线与资源

入口 `pl_dma/rtl/rs485_gp_ps_top.v` 是显式opt-in系统，复用PS GP0 AXI3→Lite转换器和写所有权适配，六路完整A33译码：probe、旧DMA、motion、旧RS485 GP、新cache/telem、新DMA。旧默认生成器/顶层保持；新接线由pl_dma/generate_telemetry.py再生并--check。不要并联同一GP总线或重复实例PS转换器。

|功能|窗口/IRQ|数据通路|
|---|---|---|
|原probe|0x80400000，IRQ0/SPI82|保持|
|原DMA|0x80500000，IRQ1/2/SPI83/84|原controller/HP0，MM2S运动，旧S2MM默认保持|
|原motion|0x80600000，IRQ3/SPI85|MOT2/运动契约保持|
|原RS485 GP|0x80700000，IRQ4/SPI86|诊断FIFO8，原捕获/显式消费保持|
|新cache/telem GP|0x80800000/4KiB，IRQ5/SPI87/INTID119|VERSION1/PROFILE0x31544352/CAPS1f/FEATURES1f|
|新S2MM-only DMA|0x80900000/4KiB，IRQ6/SPI88/INTID120|独立controller→独立原厂转换器→HP1|

新IRQ均level-high；最终HPF/完整DT/GIC路由须BSP审核。候选补审审核六份现有expanded DTS数字CPU资源（含disabled），未发现新窗口/SPI冲突，限制与每份源SHA见pl_dma/reports/telemetry_candidate/audit.json。不以数字扫描代替所有child-bus翻译或最终地址图。

同源H16 100MHz驱动GP/两controller/转换器/HP0/HP1，ASYNC0。隔离副本由当前原厂xmlipgen实际生成HP0+HP1，各38端口；HP0方向/位宽、GP0 A33与IRQ16保留。HP1 A33/D64/ID6/LEN4/SIZE2/LOCK1/QoS4，无WID；DMA A32补高位0，经真实AXI4→AXI3转换，不截LEN，单master独占HP1。HP0不加PL多master仲裁。HP1仍与HP0共享PS内部互连/DDR，不承诺带宽绝对隔离。

真实IP为当前TD2026.1 SP2 Anlogic AXI DMA1.0、AXI Protocol Converter1.0，安装源/Component/头文件SHA保留。新实例AL_INCLUDE_MM2S=0、AL_INCLUDE_S2MM=1；simple、SG/Micro/status-control0，memory/stream64、DMA地址32、burst16、DRE/SF1、BTT16、100MHz。prepare_ip的库存manifest包含原双向profile参数；**新实例有效参数以新增schema的dma.parameters及生成实例宏为准**，不能据库存manifest误认为新实例启用了MM2S。

新DMA guard只允许原厂S2MM offset30/34/48/4C/58；完整A33/D32译码，对齐、完整WSTRB、BTT1..65535、buffer8B对齐、地址高字0。未知/禁用MM2S访问SLVERR，窗口外DECERR；业务只用N×64。新GP shadow支持byte strobes，doorbell/W1C全字；WSTRB0无动作（合法地址/方向），非法保留位/ID/gen/长度/状态返回SLVERR并保留旧事务，AW/W独立、R/B背压稳定。表见generated/telem_registers.md，字段/错误码见telem_defs.h/vh。

## 事件、解析、缓存与时间

原采集器完成事件observe_push/data通过旧GP桥新增**只读输出**completed_valid/raw/generation/revision/current_periods/current_mask显式导出，不使用综合层级引用。旧GP regs只新增generation观察输出；collector rate函数include仅移到其所用BIT_CYCLES声明之后以兼容Questa，算法不改。旧UART/transaction/FIFO/divider保持字节身份，旧GP/多速率全部回归。

新模块：rs485_light_parse（字段解释）、rs485_latest_cache（15组最新有效/最近结果及原子快照）、rs485_telemetry（完整队列/CRC/包credit）、rs485_telem_regs（AXI-Lite）、rs485_telem_top（组合接线）。原运动probe不公开time输出；新opt-in rs485_probe_time_regs由原源码生成，仅改模块名并导出原timestamp，**不新增时间计数器或epoch**。原pl_motion文件未修改，生成器/身份检查核对导出增量。新模块全部使用该64bit/1MHz系统时间。实际系统bench断言其与原运动timestamp逐拍相等。

完成事件同时分支：旧诊断FIFO由GP唯一消费；新遥测FIFO由打包器唯一消费；解析/cache不等待任一队列。cache不因FIFO满丢更新，DMA不pop旧GP FIFO，GP不pop遥测FIFO。completion_serial64按每个完成事件递增（包含未接纳/满丢事件），区别于源request sequence（重试共用sequence、attempt不同）。串口无线上事务号的迟到/重复歧义仍按原PROTOCOL_CONTRACT.md保留。

30分别提供signed32 carry和unsigned16 value；33为signed32接收脉冲，39为signed16角度误差，内部符号扩展至signed64；30的signed64字段是carry符号扩展，value单列，不能当作机械位置。3A/3E保留raw enum，1/2已知，其他枚举可协议有效但known=0。无浮点/机械标定，不修正运动命令位置，不新增自动停机。33不是编码器反馈。

每(节点,查询)行保留last_valid完整32B及generation/revision、last_result完整32B及标签。失败更新last_result，不覆盖last_valid；BUS_BUSY原状态保留。版本/长度/地址/查询等内部不一致计parse_errors，不覆盖有效值。M1～M3/E0～E2、五查询15行，M4禁用。原始status=VALID才允许有效数据；未知枚举不等于通信失败。

配置更新保留旧有效值与原revision，不追贴当前版本。stale_limit_us=max(3×当前查询period,100000)；无有效值、查询禁用或age>=limit标stale，disabled单独标志。age为系统time_us减last_valid.event_us的uint64差，支持自然回绕；阈值范围<2^63us。不同查询依然异步，不是15通道同步采样。

SNAP_REQ_ID非零递增、SNAP_SUBMIT=1一次捕获全部已登记行及全局头；同最近ID重放不重采，新ID替换。读无副作用，SNAP_STATUS/ID及头部time/generation标识同一采样时刻；多字raw/time/age同拍。采集generation改变使旧快照valid撤销，旧在途AXI应答保持，PS检查generation；新DMA reset不清cache。

128B行（0x200+index×128，index=node×5+query）：0flags（VALID_SEEN、RESULT_SEEN、RESULT_VALID、ENUM_KNOWN、STALE、DISABLED），4地址/查询，8/12有效值gen/rev，16/20最近结果gen/rev，24有效更新饱和计数，28保留0，32..63 last_valid raw，64..95 last_result raw，96..103 signed64，104..107 carry，108..109 value，110 raw enum，111 known(0/1)，112..119 age_us，120..127 stale_limit。carry/value仅30有解释，enum仅3A/3E有解释；未见/无效行必须先检查flags，不能解释保留诊断数值为零反馈。ENUM_KNOWN指last_valid，RESULT_VALID指最近通信结果。

## 64B遥测与容量

不采用历史128B草案，也不修改原32B。外层小端：magic0x31543452@0、u16 version1@4、u16 length64@6、collector_generation32@8、cfg_revision32@12、transport_generation32@16、completion_serial64@20、raw32B@28、CRC32@60。CRC32/ISO-HDLC覆盖0..59，reflected polyEDB88320、init/xorout FFFFFFFF，小端输出。

raw byte i=源record[8*i+:8]，等价GP八个D32字各自小端；这不是直接复制UART线上字节。PS先还原原bitvector，再按原大端payload字段解释，不把raw开头的payload字节误当外层大端数据。每条8个64bit AXIS拍，KEEP=FF；CRC只保护封装完整性，不代替CHECKSUM-8。

FIFO256条、满整条丢新，不阻塞UART/cache/STEP；full_drop与旧GP dropped分开，disabled_drop包括关闭/取消期间不接纳，cancel_drop计复位/恢复/本地空闲取消清掉的队列记录（含尚未完整握手的队首）。已完整stream交付但未确认的包若被reset取消，dma_failed计失败/中止包一次；不能把它当作确定已写DDR或确定未写DDR。stream_records/packets、dma_ok/failed分开，计数u32饱和。FIFO计数包含正在复制/发送的队首，直到该记录末拍握手才pop。

最多16条/1024B，包槽空闲且达到16条或最老等待10ms即冻结N/packet_id/gen/bytes，READY level保持。前包等待ARM/发送/确认时不覆盖；释放槽后到期记录立即有资格形成下一包。低速单条也形成64B短批，无数据不发空包。10ms是形成待发包时限，不含PS、前包或DDR等待。等待ARM/背压/形成包额外延迟有最大统计。容量与服务预算见TELEMETRY_SERVICE_BUDGET.md。

## RX buffer、ARM与完成

启动时transport关闭。生命周期owner确认新controller/HP1已静止且primary reset释放 → 写新非零递增RECOVER_GEN、RECOVER=1 → ENABLE=1。ENABLE仅控制接纳新完成事件；关闭不撤回已提出VALID，也不停止采集/cache。ID/generation/serial耗尽不回绕，报告exhausted，不能静默复用。

正常循环：读稳定READY包ID/gen/bytes → 分配或取预分配DMA buffer（容量可1024，地址8B对齐，设备DMA API/32bit mask）→ **提交恰好bytes=N×64的S2MM descriptor并issue_pending** → 写ARM_ID/GEN/BYTES、ARM=1。硬件匹配所有字段；无credit绝不提出VALID；相同当前ARM幂等，错误ID/gen/bytes拒绝。不能先ARM再准备RX。

VALID/READY/KEEP/LAST背压稳定；开始后不再等新记录，TLAST只在最后记录末拍。STREAM_DONE仅代表全部stream握手，DMA可能还未完成DDR。PS等待DMA IOC成功且无error，核对S2MM实际长度、冻结bytes、包ID/gen、所有CRC与raw有效性，完成必要持久化后，写COMPLETE_ID/GEN/RESULT(0成功/1失败)、COMPLETE=1。成功后才开放下一包；最近同ID同结果重放不重复动作，同ID矛盾结果拒绝。

失败结果可在任意已ARM阶段报告，关闭后续接纳/新包，仍保持在途VALID，等待受控reset；未ARM包不能假装DMA失败完成。reset对未确认包计dma_failed一次，显式失败后再reset不重复计数。软件负责具体DMA error分类，不把全部DMA IRQ当故障（IOC也中断）。

## 取消与复位作用域

独立controller的软件reset/primary reset仅影响新遥测队列/半包/credit/closed状态，保持cache、采集/旧GP、统一time_us及HP0运动会话。它不连原controller reset，不发运动STOP。CANCEL阻断新ARM/新接纳；若无在途包可本地清队列，若有在途/held VALID，不能撤VALID或仅清FIFO宣称取消完成。

BSP新controller owner执行：禁止新提交/ARM → terminate_sync新S2MM → 允许在途HP1事务收敛、按该实例作用域协调reset → 检查HALTED/reset/IRQ/tasklet/callback及在途DDR写静止 → 不确定或失败buffer quarantine → 新transport_generation显式RECOVER、投RX、再ARM。硬件观察HP1 accepted AW至B响应并检查未握手AW/W/B，RECOVER还要求hp_idle；**hp_idle/primary high/队列空并不能单独证明硬PS/DDR与软件描述符已静止**。

无RX buffer、FIFO满或正常背压不自动触发运动停机。公共p2f_rst0_n/整域重配置仍影响两系统和epoch，只用于启动/受控整域重建，不作为遥测局部恢复。HP1可影响共享DDR带宽，不能承诺运动无欠流；必须实测并发补给界。

旧GP LOCAL_RESET保持原静止接受条件，清cache有效性并使用新collector_generation；已在遥测队列/在途包的记录仍按旧标签送完，不贴新generation，不自动reset DMA。包可跨collector_generation，但同一transport_generation；每条都自带标签。若需丢历史，显式走遥测取消/恢复。新transport generation恢复清旧队列/半包/credit，不自动重放或恢复旧运动。

新IRQ为pending&mask的level、W1C set优先，复位mask0。READY持续源需先mask并处理/解除源，再W1C/readback/unmask；RESULT、FAULT、PARSE_ERROR、FIFO_DROP独立。数据/配置/通信/保护状态继续由旧GP及raw记录区分，不新增自动停机策略。

## 真实IP、软件及回归证据

- pl_dma/reports/telemetry_ip_r2：真实S2MM-only DMA+真实HP converter，2251检查，精确64/1024/192B DDR字节/guard/length通过；BTT1024+64B提前TLAST为IOC/actual64，BTT64+128B报00004012/actual64，缺失TLAST在观察窗口内未完成。没有stub替代最终验证。
- 当前只读provider simple完成路径desc->residue=0，DMA_COMPLETE路径也不提供短包实际长度；**requested-residue不能用**。本生产路径精确BTT，并要求BSP在重新编程下笔前捕获实际S2MM_LENGTH/错误状态或提供等价已验证的provider API。
- pl_dma/reports/telemetry_system_final：真实GP0转换器、两个controller和各自HP converter、实际UART模拟从机及六路路由；23044562检查，3个实际完成事件、HP0读288拍、HP1写16拍，实际DDR内raw/tag/CRC与源事件一致，GP并行捕获消费。遥测背压/取消/reset/显式恢复期间与原运动系统逐拍比较STEP/DIR/EN/HP0，32点正常完成。
- evidence/telemetry_unit_final、telem_results_final：276事件同时填满两FIFO（8/丢268，256/丢20），cache仍为最新值；16条整包/单条刷新/无credit/长背压/CRC/放弃前包/重复与矛盾完成/失败不撤VALID/reset一次统计/代际/时间回绕/原子快照。telem_parse_final直接验证三节点66组signed最值/零/未知枚举/M4禁用。
- evidence/telem_software_final：RTL输出17条由现有rs485_decode交叉核对（16有效、1超时），逐字节翻转1088用例全部拒绝。software/rs485_telem.h/c为独立C11 decoder和ARM/COMPLETE callback助手，无/dev/mem或最终内核驱动。调用前检查接收长度为64倍数且等于冻结bytes，输出保留status/attempt/时间、两种generation、revision/serial；无效值不补成零反馈。
- evidence/sim_dma_legacy_final、sim_dma_gp_final、sim_dma_multirate_final保留旧采集/GP回归。pl_dma/reports/telemetry_regression_r2覆盖接口、原GP、单轴/四轴/连续/运动服务、真实旧DMA独立/共享、真实MM2S运动及Golden；旧release JSON恢复原字节。失败/修正见evidence/TELEMETRY_FAILURES.md及原日志，许可证冲突和身份守卫失败未当作通过。

## 100MHz时序、资源与复现

TD2026.1 SP2、DR1M90GEG400参考speed2，10ns固定，不新增多周期/false-path放宽。组件报告分别pl_dma/reports/telem_parse_r1、telem_cache_packed、telem_packet_final、telem_dma_r1；cache_r1因综合优化错误已作废，不作为交付。整体实际PS/GP0/HP0/HP1与两个真实controller见pl_dma/reports/telemetry_soc_final。最终数值和remaining诊断见下方附录，按层级区分核心与测试scan封装，组件含子模块者不再与整体相加。

整体fixture使用3/2/4/7/5/3cycle、10MHz运动参数，仅为继承的验证夹具，不能用于驱动器实板。UART IO仅隔离观测，不绑定原候选L17/N16/N15到当前GPIO工程；无bitstream/BOOT/FSBL输出。BSP实际GPIO顶层此前余量不能被此独立工程继承，需重新做最终系统STA/DRC/CDC/复位/电气验收。

从dev目录运行，tag使用新名字（日志不覆盖）：

```powershell
python pl_interface/generate.py --check
python pl_rs485/tools/generate_gp.py --check
python pl_rs485/tools/generate_telem.py --check
python pl_dma/generate_telemetry.py --check
python pl_dma/audit_telemetry_candidate.py --tag verify
python pl_rs485/tests/run_telemetry.py --tag verify
python pl_rs485/tests/run_telem_parse.py --tag verify
python pl_rs485/tests/run_telem_results.py --tag verify
python pl_rs485/tests/run_telem_irq.py --tag verify
python pl_rs485/tests/run_telem_software.py --vectors pl_rs485/evidence/telemetry_verify/frames.hex --tag verify
python pl_dma/tests/run_telemetry.py --tag verify
python pl_dma/tests/run_telemetry_system.py --tag verify
python pl_dma/tests/run_telemetry_regressions.py --tag verify
python pl_rs485/tests/run_sim.py --tag dma_legacy_verify --seed 20261013
python pl_rs485/tests/run_gp.py --tag dma_gp_verify --seed 20261014
python pl_rs485/tests/run_multirate.py --tag dma_multirate_verify --seed 20261013
python pl_dma/build_telemetry_component.py --component parse --tag verify
python pl_dma/build_telemetry_component.py --component cache --tag verify
python pl_dma/build_telemetry_component.py --component packet --tag verify
python pl_dma/build_telemetry_component.py --component dma --tag verify
python pl_dma/build_telemetry_soc.py --tag verify --audit pl_dma/reports/telemetry_candidate_verify/audit.json
python pl_rs485/tools/freeze_telemetry.py
```

Questa同一nodelocked license只允许一个vsim会话，真实IP测试串行运行；Icarus在本机Windows沙箱可能访问异常，使用允许本地工具运行的终端。GCC严格C11编译、Python3.10。freeze核验固定发布目录；验证新tag另留日志，如替换发布证据须明确更新选择再冻结，不修改旧证据。

## BSP接入要求与未验收项

1. 重生成实际PS/HPF，保留DDR/存储/原HP0/GP配置，启用HP1并核对两HP内部soft reset释放；按真实层级加载原厂PS属性，仅改层级路径、不手填时钟。审核六个窗口及SPI87/88/level、最终STA/DRC和remaining诊断。
2. 新controller作为独立Linux DMAengine设备/生命周期，只有S2MM child、addrwidth32、stream64、DRE、sg-length-width16，simple模式不加include-sg。新窗口/compatible/clock/reset绑定由BSP核对，不直接部署未验证候选DTS。当前loopback-pair或motion-controller取消助手不能直接套到新实例；provider需支持新profile而不重置旧controller。
3. 独占新S2MM；buffer地址来自设备DMA API，8B对齐、32bit mask，coherent或明确map/sync/cache所有权和屏障；一笔simple RX，先issue再ARM，完成后核对实际长度/IOC/error、包身份/CRC再确认和重用。不能把用户地址、buffer容量、callback成功或residue0当实际长度。预分配池但不要自动提交下笔覆盖上笔长度寄存器。
4. 每个buffer/回调关联controller身份、transport_generation、packet_id和软件会话epoch，旧回调丢弃；取消失败buffer quarantine。新controller局部恢复不发运动STOP；common reset则执行既有整域重建流程。不能以硬件hp_idle单独证明DDR静止。
5. Web/日志/AI复用快照或完整遥测的原始量、有效性、来源时间及revision映射；按异步采样和缺采/丢弃统计处理，不把33接收命令脉冲当编码器，不做反馈修正运动。固件身份、STP并发、转换模块换向/回显/迟到界、实板HP1/IRQ/cache/DDR压力和长期服务时限仍待实测。

## 未关闭的原厂综合诊断

真实S2MM-only受保护IP在独立DMA组件及整体工程均报SYN-5066：断开内部vyjqtk/rucwti多驱动之一。未编辑受保护IP、未静默改回MM2S开启。真实IP RTL仿真通过不能证明该优化的综合等价；厂商/BSP须确认此参数组合及综合结果，关闭前不得称为可部署硬件签核。DMA scan夹具另有PHY-5060：IP内部时钟候选混合2131个clock与1个data/ctrl fanout；完整诊断保留。OOC未绑定IO、无真实IO delay及速度等级未实物确认也不在本交付签核范围。布线setup/hold结果与diagnostics_closed/signoff_pass分别记录，时序通过不等同诊断关闭。

## 组件100MHz实测报告

下表是各自保留全部输出的独立scan夹具总量，包含输入/观测寄存器及子模块；并非纯核心增量，不能相加推算系统资源。parse已包含于cache，DMA夹具包含真实新controller与转换器。最终系统资源另报。

|夹具|LUT6|寄存器|Slice|ERAM|gate setup/hold ns|place setup/hold ns|route setup/hold ns|
|---|---:|---:|---:|---:|---|---|---|
|parse_r1|142|234|202|0|+3.191/+0.000|+5.555/+0.000|+4.059/+0.098|
|cache_packed|7218|22646|15550|0|+0.909/+0.000|+3.450/+0.000|+0.313/+0.022|
|packet_final|4705|2841|5093|0|-0.427/+0.000|+3.242/+0.000|+1.059/+0.021|
|dma_r1|1251|2116|1678|12|+1.978/+0.000|+5.089/+0.000|+3.357/+0.030|

packet门级估计有负setup，最终布线通过；不删除早期负裕量。cache_packed替代无效cache_r1，保留完整15360bit原子快照，避免把被优化掉的功能算作资源节省。组件的时序结果不关闭前述原厂critical诊断。

原GP C助手另以software_dma_final验证（527次mock读/12次写）。PS必须以单个owner或mutex串行执行SNAP提交及整组读取，读前后核对SNAP_ID/STATUS/generation，避免另一个软件客户端刷新快照造成混读。snapshot并非自动跨客户端锁。

整体SoC参考夹具仅保留H16和UART观测IO，运动STEP/DIR/EN未作为其顶层IO保留，未观测输出可能被优化；它用于真实PS双HP结构和内部状态路径时序评估，资源不能冒充最终运动GPIO顶层资源。功能系统仿真则逐拍观察并比较全部运动输出。

新profile IRQ定向自检telem_irq_final通过105项：READY持续源与W1C同拍set优先、mask不丢pending、unmask重现、primary reset故障边沿与W1C同拍竞争、清除后不重复制造边沿。使用同一随机AXI AW/W顺序及R/B背压BFM。

门级层级报告可分离的核心估计（logic LUT/ripple/seq/ERAM/DSP，非route LUT6）：cache=1085/1041/21674/0/10，packet=1323/728/1211/0/0，独立DMA+converter+guard=925/154/1712/12/0。纯组合parser在该夹具已被flatten，报告未单独保留dut行，故仅报告上表整体夹具数值，不虚构核心精确增量。门级数字不与最终route夹具/整体相加。

软件首版匹配VERSION/PROFILE及CAPS/FEATURES的固定整体值；本profile未定义的能力位不得据位号推断未来兼容性。rs485_io回调ctx应绑定新0x808窗口，采用有序D32访问并返回总线/驱动错误；ARM助手的成功只表示授权发送，仍须执行上文DMA长度及完成检查。

候选审计JSON中的contract_confirmed=false来自集中确认前的历史证据，保持原字节；当前确认状态以本交接及独立增补为准。审计复现必须使用新tag，整体新构建以--audit指向该次实际PS生成审计，不覆盖已归档审计证据。

PS应记录(collector_generation, revision)到实际已应用配置、apply_sequence的映射账本，接受提交与实际应用分开记。不能用当前配置解释旧FIFO/遥测/last_valid标签；重启后若未保留历史映射，明确标配置来源未知，不补贴当前revision。

## 整体最终布线结果

telemetry_soc_final从相同gate.db续跑完成，完整initial_attempt.log/physical.tcl/physical.log/run.log均已归档。固定100MHz：

|阶段|setup WNS ns|hold WNS ns|
|---|---:|---:|
|gate|-1.368|0.000|
|place|+1.708|0.000|
|route|+0.018|+0.020|

最终setup/hold违例端点均0，早期负估计与物理修复过程完整保留。整体参考夹具资源：34187 LUT6、49540寄存器、45387 Slice（86.48%）、34 ERAM、15 DSP、1 GCLK、6 SCLK。此为整体一次计数，不能再加上述组件夹具或核心资源。实际STA识别board_100m及PS GEN_PL_GP0S/GEN_PL_HP0/GEN_PL_HP1，均100MHz。

check_timing：no_clock=0、clock_definition=0、invalid_constraint=0、combinational_loop=0；dummy_nodes=2，缺input_delay=1/output_delay=2（隔离UART IO）。SYN-6021为3个未绑定UART逻辑端口；SYN-5066原厂内部多驱动仍未关闭。因此报告timing_pass=true、diagnostics_closed=false、signoff_pass=false。最终setup仅18ps，参考speed2且未签核真实IO/jitter/CDC/复位/电气；该结果不能直接部署，也不能继承为最终GPIO系统余量。BSP/厂商须关闭IP诊断并重新做最终顶层时序。

软件证据另用Python标准库zlib独立核对17条实际RTL帧的CRC32/ISO-HDLC，与RTL/C一致，见telem_software_final/crc_zlib.log。
