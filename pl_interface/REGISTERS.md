# Register Map / Error Definition — Draft

2026-10-12 补充：`schema.gp_control_profiles.gp_control_probe_v1` 的最小子集已由用户确认，完整语义见 [GP 最小控制契约](../pl_motion/GP_CONTROL_DRAFT.md)。本页下文的整体运动寄存器/命令/CDC 描述仍为 Draft；冲突处以该 profile 为准。首轮只支持 NOP/SNAPSHOT、ACK/TEST IRQ，无运动/DMA。生成表列出白名单、profile reset 和字段限制；GP 资源实际核验及 RTL/板级实现仍待完成。

所有offset是设备窗口内相对偏移，不是GP绝对物理地址。候选窗口4KiB，32bit访问，little endian。具体表由唯一机器源schema.json生成到generated/registers.md、errors.md；地址/错误码不得在手写PS/RTL再定义第二套。JSON格式和生成产物入库已确认，地址/位域/错误策略表本身仍Draft。

## AXI与副作用

GP full AXI到Lite转换由互连承担，不能假设GP本身已经是Lite。Lite从机分别缓存AW和W，独立ready，先AW/先W/同时都接受，配对一次后才发生写副作用；BVALID持有到BREADY。AR/R独立，RDATA/RRESP在背压稳定。允许最多一笔未完成写、一笔读；不依赖AWVALID与WVALID同时出现。跨域命令AXI OKAY只表示已进入mailbox，不代表运动动作完成。

shadow RW按WSTRB逐字节更新，保留位写1整笔SLVERR且无副作用；doorbell/transaction提交和W1C候选要求WSTRB=0xF，其他SLVERR。WSTRB=0是无副作用OKAY。RO写、WO读、未对齐/未知offset、非法字段为SLVERR；上游无窗口decode用DECERR。读未实现位置不返回随机数据。读没有清故障/清中断副作用。

全部运行参数影子写不改active。CONFIG_COMMIT候选仅READY/NOT_READY、EN disabled、queue空、无session；运动域一次校验mask、时序非零、min<=max、节点映射与watchdog，再原子替换整个配置，config_generation++。失败保留原配置，返回错误字段。运行/暂停状态拒绝提交，通信策略也不得局部热改。机械参数由PS配置管理持久化，PL仅存本次已提交执行参数，不继承Golden基线。

## 命令事务、应答与幂等

单writer按CMD_OPCODE、CMD_ARG、TXN_ID、SESSION_LO/HI影子→CMD_SUBMIT=1；提交时所有payload被捕获且锁定到ack。CMD_STATUS：busy bit0、ack_valid bit1、accepted bit2、completed bit3；ACK_ID对应ID、ACK_ERROR错误码。未读ack允许保留，但新ID覆盖前PS必须已读取；busy拒绝新事务。accepted表示动作合法已开始，completed表示该命令最终条件满足（START原子启动、STOP pulse-safe完成、PAUSE到边界、HOME全部完成）。error会结束事务且completed=1/accepted=0；STOPING中故障只改最终状态，不能吞ack。

同ID同payload重复submit返回缓存状态，不重复动作；同ID不同payload报DUP_COMMAND。只缓存最近一个事务；旧ID不允许倒退或回绕，达到u32上界后停机建立新control generation。BUSY时不覆盖payload/ack。STOP独立于DMA输入且安全输入优先，不等待RS485或DMA。软件不得发送新的START作为已在RUN的重复命令。

候选opcode由机器源枚举：CONFIG_COMMIT、OPEN_SESSION、ENABLE、START、STOP、PAUSE、RESUME、DISABLE、CLEAR_FAULT、FLUSH、REBASE、HOME、SNAPSHOT、CLEAR_STATS、LINK_RECOVER。OPEN_SESSION非零新session、从seq0开始；会话ID在当前PL epoch不能复用，由PS管理；首次ready不会自动enable。

## 快照与原子读

SNAPSHOT命令携带TXN_ID。运动域同拍捕获四轴signed64位置、u64 timestamp、四轴u64 pulse_total、position_valid/state/session、accepted/done_seq，经稳定payload mailbox送GP；SNAP_ID=事务ID并置SNAP_VALID后读所有LO/HI。snapshot保持到下一SNAPSHOT完成，普通读不触发捕获，读LO再HI不会跨时刻。PS串行快照并在读前后核对SNAP_ID；init epoch变化使SNAP_VALID=0，禁止混用旧样本。

REBASE使用四轴64bit影子值（low/high不是各自生效），仅EN disabled、停止完成、FIFO空、session关闭、受控维护或HOME流程；CMD_ARG mask确定重标轴。不得通过写只读位置寄存器改变计数，REBASE不清pulse_total、不重置timestamp，维护动作是否允许机械有效标记须用户确认。

## 故障、W1C、中断与watchdog

FAULT_BITS锁存事件，FAULT_FIRST_CODE和FAULT_TIME保存第一次未清故障。FAULT_BITS本身RO，CLEAR_FAULT命令携带mask并检测源已解除；不解除源返回FAULT_ACTIVE。清锁存不自动EN、不回放队列。故障发生与清同拍set优先，first-code/time不因重复故障覆盖；其他事件另走遥测和bitmap。

FAULT_BITS使用六类bitmap（RECORD/MOTION/SAFETY/COMM/DMA/CONTROL，生成字段给出位号），类别清除须该类全部源解除。STATE枚举值由schema.states生成；CAPS为支持轴bitmap；CFG_NODE_ENABLE为四个配置节点槽mask，CFG_Ax_NODE_ID是其RS485地址，不是256节点bitmap。COMM_POLICY候选0=未配置禁止START、1=WARN、2=STOP、3=保留；阈值与报警政策仍需批准。

IRQ_PENDING为W1C，IRQ_MASK为RW（1使能），IRQ输出候选level=|(pending&mask)。同拍clear和事件set优先；持续条件（fault active、FIFO低水位等）清后仍应重新置位，PS须处理源再清pending。清IRQ不清fault，清fault不清日志计数。中断位：0 command_ack、1 fault、2 motion_low、3 telemetry_available、4 telemetry_drop、5 motion_end、6 link_error，其余保留0。DTS触发方式必须与level输出匹配，不能复制示例IRQF_TRIGGER_RISING。

Watchdog候选由100MHz安全域计时，配置timeout以timestamp tick换算；kick用递增WD_TOKEN和全WSTRB，相同token不续命；配置enable/timeout仅停机提交，未配禁止START；有效kick才从当前时间重装。运行/暂停/回零中启用范围TBD，推荐均启用；timeout引发fault/STOP，Linux死亡不需软件ack才停止。超时与kick同拍候选超时优先。watchdog恢复仍需显式清错、新session，不自动start。

## 错误分类

错误表生成含值、severity、状态影响与报告通路。类别高字节：0x01记录/会话、0x02运动、0x03安全、0x04通信、0x05DMA/链路、0x06控制。ERROR severity表示拒绝或停止；WARN表示诊断；POLICY表示等待通信策略确认。FAULT发生时在GP锁存+IRQ+尽力遥测，单次拒绝至少ack/诊断计数+尽力遥测；CRC等使运动session失效的记录错误必须停止并锁存，不能只丢一条继续。通信CHECKSUM/TIMEOUT不是PS/PL CRC；按节点阈值策略选择告警/停机，仍TBD。
