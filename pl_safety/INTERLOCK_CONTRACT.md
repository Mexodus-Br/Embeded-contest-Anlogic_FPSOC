# SAF2 / R5S2：485与PS心跳联锁契约

行为于2026-10-18由用户集中确认。实现和验证状态以INTERLOCK_HANDOFF.md为准；
本契约不授权BSP部署、实体接线或上板。原SAF1、R5S1、MOT2/72B、采集32B和遥测64B
数值/语义保留；新行为仅用于显式interlock_*生成链。

## 配置与身份

唯一机器源是pl_interface/schema.json的interlock_profiles.gp_safety_interlock_v2。
generate_interlock.py生成C/Verilog常量及485窗口的派生身份头。
安全仍是0x80a00000/4KiB、IRQ7，485仍是0x80700000/4KiB、IRQ4。
不增加PS GP/HP、DMA、AXI-Stream、针脚或遥测FIFO。

|窗口|旧profile|新profile及能力|
|---|---|---|
|安全|SAF1/version1/caps=0x3f|SAF2/version2/caps=features=0xff；bit0..5原义，bit6为485联锁，bit7为PS看门狗|
|485|R5S1/version1/caps=0x1f|R5S2/version2/caps=features=0x3f；bit0..4原义，bit5表示受安全空闲/查询资格门约束|

旧入口默认INTERLOCK_SUPPORT=0；新增完整入口interlock_rs485_gp_ps_top，经原七窗口
路由及实际GP转换器接入。仅识别旧profile的软件不得把R5S2当作旧动态配置profile。
原采集事务、重试、隔离、500ms退避、revision、generation和已有记录格式保持。
生产HOME配置PROFILE0仍未批准，仍禁止启动；本次冻结的联锁数值不能替代机械配置。

两类期限单位均为us，合法范围1000000..3000000，默认2000000。485三轴共用期限，
各轴独立计时；监测掩码为非零三位，默认7，M4不启用。PS健康报活目标周期500000us。
PL所有者为非零递增u64，序号非零且严格递增u64，二者在同一PL epoch内均不回绕复用。
该owner_id与原MOT2运动session_id是独立命名空间；报活不会创建运动session或接受轨迹。

## 485监测

唯一有效轮询开关仍是采集器GP RUN。安全层只使用采集器实际状态和完成事件。
RUN关闭停止新查询、在途事务按原有限重试/隔离结束；不新增反馈超时，但在途本轮
有效保护应答仍锁存保护故障（关闭仅允许无运动的空闲门）。已锁存故障不清除。

每次开启、采集配置应用、generation/revision变化或local reset撤销旧健康资格。
开启后立即从本轮时基计时，不能等首帧才开始；所有受监测轴必须各自收到本轮
有效且枚举2的0x3E，才能获得启动资格。受监测查询须实际启用且周期非零。
age>=期限的采样沿即触发；同拍正常反馈不救活已到期轴，保护=1始终触发。

只有实际应答提交事件同时满足节点、版本、status、长度、payload、0x3E、已知枚举、
当前generation/revision及本轮request/event时基才更新相应轴。枚举1触发保护、
枚举2为健康；未知枚举、其他查询/轴、坏帧、错误地址、超时、重试失败、cache历史读取
均不能代替本轴健康反馈。任一Delta轴有效保护=1均整组停止；受监测轴掩码只限制反馈超时。
安全监测器只译码固定保护格式，使用同一生成协议定义直接形成逐轴位图；其资格由
未修改的通用采集解析器作差分验证，避免通用task编码/再译码进入当拍停止长路径。
角度、误差及接收STP数量仍仅采集给PS，不增加PL停机规则。

事件来自rs485_transaction.EMIT的push/raw，经桥completed_*直接分支，
不依赖FIFO接纳/GP消费/cache读取、DMA完成、IRQ或PS读取。时间戳使用原统一
system_time_us/u64/1MHz；event_time是原RX校验事件标记，联锁first_time为检测采样沿
之前登记的系统时间，last feedback time为监测器采样实际提交的时间。

R5S2中RUN改动、周期/掩码提交只接受安全空闲条件：无HOME/运动session、队列、
planner、transport半包、普通命令或已捕获AW/W，且pulse-safe；RUN开启还要求
采集配置已应用、无pending、0x3E启用，且旧在途事务及隔离已结束。CFG_SUBMIT继续原子捕获完整周期/掩码。
pending提交及应用期间禁止新HOME/普通使能，避免先提交后运动绕过空闲门。
拒绝的写、幂等重放不重建监测时基。LOCAL_RESET还要求EN失能、RUN=0、原采集器静止门。
它不清联锁、统一时间或看门狗。旧profile保留原动态配置行为。

## 看门狗与停止

所有者OPEN仅停稳、EN失能、无运动/HOME所有权或待执行数据时接受；PL分配新ID。
从OPEN采样沿就开始首次心跳期限。首次有效心跳前不允许HOME/真实使能/运动。
心跳使用独立shadow和COMMIT，普通HOME/命令busy不阻塞它。4个32位身份/序号字
全部写齐后才可提交；身份必须匹配当前活动所有者、序号必须严格增加。重复/倒退/
旧所有者/耗尽/撕裂/非法写不刷新。到期优先于同拍提交；故障后的迟到心跳不恢复旧所有者。

普通STOP、PAUSE、空闲、清IRQ、DMA-only reset或软件关闭设备都不解除看门狗。
关闭/交接要求停稳、EN失能、无运动session/HOME/队列/半包，并显式OWNER_CLOSE，
携带当前所有者身份。新服务不能读取旧ID后接管续喂；旧所有者关闭或超时取消后，
只能显式OPEN新所有者、首次报活，再建立新任务。浏览器断线按PS需求基线处理，
不直接等同于PS看门狗超时。

三类联锁都在检测当拍禁止新STEP并撤销三轴position_valid，完整取消motion/HOME、
watchdog owner、FIFO/planner、transport半包/持有记录及旧任务所有权。
已发出的STEP计数保留为诊断，不回滚。现有执行器唯一持有STEP/DIR/EN/位置；
完成原H/L/DIR保持排空，再按原OFF延迟失能，不新增脉冲源、输出与门或公共复位。
任何故障优先于候选STEP、HOME命中/完成、新命令和正常END；原急停/限位/STOP边沿不延后。

逐轴保护、逐轴反馈超时与心跳超时按schema原因位OR锁存，首事件时间不被后续覆盖。
全局安全first_cause在首次同拍采用急停>限位>485保护>反馈超时>看门狗，
同一类同时多个轴以位图保留。SAF2扩展的FIRST_CAUSE仅针对两类新增联锁；
原0x200快照的全局原因/首因/首时包含急停/限位/HOME错误及新增原因。

通信恢复、驱动保护解除、RUN关闭、IRQ清除或恢复报活都不清错、不使能、不恢复旧任务。
恢复流程：人工排除原因，停稳且EN失能；建立本轮全轴健康反馈；显式OPEN新所有者并
首次报活；显式安全CLEAR_FAULT；完整HOME；从新位置/新运动session显式规划启动。
故障期间允许前述健康资格建立，故障锁存仍阻止运动，避免清错/资格互相等待。
清错要求原急停释放门、空闲/pulse-safe、无持续新原因、全轴反馈资格和有效心跳。
HOME被任何联锁打断必须完整重做。

## AXI与状态

所有新增偏移和快照word编号见生成interlock_defs.h/vh及
[寄存器/位域表](generated/interlock_registers.md)；旧偏移不变。
安全扩展使用0x100..0x16c及0x300..0x37f快照；复用原安全端点AW/W独立捕获和B/R保持。
完整对齐D32/full WSTRB；窗口外DECERR、非法偏移/值/状态/身份/撕裂SLVERR。
副作用精确发生在held AW && held W && !BVALID的采样沿，一次提交只生效一次。
配置/OPEN/CLOSE/心跳各自直接译码合法条件，不经共享响应mux形成反馈环。
HOME opcode及RUN关闭的精确地址/字节条件在原AW/W捕获沿预译码；正式命令校验、
RUN写入和联锁副作用仍在原fire采样沿。HOME SUBMIT地址已捕获时保守拒绝配置，
不让事务号比较进入停止组合锥；不会将B响应或预译码视为命令已执行。
实际RUN直接来自采集器唯一寄存器；合法关闭fire另以内部分支抑制当拍反馈到期，
不参与restart或在途保护资格。SAF2的pulse-safe与完整排空条件一起采样形成保守空闲
许可，并由当前命令/AXI/session/HOME所有权即时撤销；故障检测和停止边沿不流水。
SAF2的HOME所有权缓存与改变所有权的状态赋值同拍更新，逐拍等价于原state范围/DRAIN
译码，避免重复状态译码进入监测/停止长路径；其他状态/优先级和legacy表达式不变。
SAF2完整实际链在transaction原EMIT沿同时捕获原始记录和6位保护/轴号预译码，
以原始记录及旧通用解析器差分核对；监测器仍在原push采样沿检测，不增加提交延迟。
时间戳、本轮、复位和配置变化资格仍须全部满足。generation/revision使用完整32位
下一值与下一round值计算相等关系缓存，使缓存在当前拍等价于完整当前字比较，
不截位、不以奇偶代际替代身份、不延迟检测。local reset同拍引起revision异步清零
也纳入下一值；源计数器原更新/拒绝/MAX耗尽规则保留，新增接口仅为内部连线。
原generic监测器参数默认保留直接译码/完整比较，旧profile预译码默认禁用。
SAF2进一步以完整下一源/round值和精确下一reset/config-change/config-apply计算两个
当前资格投影：active与previous_run及全部当前资格等价，off保留RUN关闭后的在途保护。
实际当前RUN和OFF提交仍即时作用。两个资格是当前表达式的同拍投影，不是旧判定的
延迟版本；原时间戳、完整身份、本轮资格和到期优先级均保留。
未交付的B仍会背压共享端点，PL不承诺CPU发起MMIO至写生效的固定延迟。

配置三个shadow全部写齐、非零递增CONFIG_TXN、CONFIG_COMMIT；仅停稳失能且无看门狗
owner、RUN=0、无采集配置pending且无旧在途事务时接受整组参数，CONFIG_ACCEPTED返回txn；
下一采样沿原子应用已捕获参数，CONFIG_APPLIED才返回txn，期间STATUS.CONFIG_PENDING为1。
安全轴/期限配置前先关闭轮询并等待在途结束，防止参数提交与新查询启动同拍；
开启的事务边界门避免小于1us的开关把旧请求误当新轮；时间戳比较只是附加检查。
安全配置pending期间禁止新HOME/使能；没有跨时钟传输。485配置仍有原
accepted/pending/applied状态。最近相同txn/完整payload幂等，不重置时基；同ID不同payload拒绝。
CFG范围/掩码非法保留旧active；shadow写本身无应用副作用。

STATUS分别报告RUN、反馈资格、owner、心跳资格、permit、fault、drained、任一配置pending。
其中PERMIT/FAULT限定为新增485/心跳联锁链，不替代原全局安全状态、急停/限位、
机械HOME资格或原命令接受结果；全局故障和首因仍须读取原0x200快照。
drained要求PL静止且EN失能；B响应、IRQ W1C、CFG_APPLIED、qualified均不代表停止完成。
0x300快照以独立非零递增SNAP_REQ捕获32word，使用SNAP_ID前后核对；多字live读不原子。
保留原0x200完整安全/位置快照。快照采样上升沿前登记值，R背压不改变已形成响应。

PS仍需执行原DMA buffer生命周期、terminate/reset/quarantine流程；PL取消与drained
不证明DMA/硬PS/DDR静止，不允许因此释放或复用在途buffer。

## PS调用边界与实物门禁

software/interlock.h/c与example.c只提供有序D32 callback接口及显式调用。
串口/Web共用的唯一执行后端在关键控制循环健康检查通过后每500ms报活；不得由
独立线程、内核定时器或硬件无条件续命。MMIO错误须传播，失败/不确定写不能当健康证明；
调用例子跳过已尝试序号，绝不在写结果未知后复用序号。PL报活不证明软件所有逻辑正确。
服务重启/重连不自动OPEN/REBASE/ENABLE/START或重放旧任务。

0x3E保护语义、实物固件/STP期间查询、转换模块换向/回显/迟到边界仍待实测；协议
本身无法严格识别跨隔离窗口的同地址同长度无限迟到帧，本地ID不能修复线上歧义。
SYN-5066原厂IP、实际针脚/电气/同步器资格、外部IO delay、机械停止与复电、BSP/DDR
静止验证仍独立保留。完整数字功能及STA通过也不等于可以上板。
