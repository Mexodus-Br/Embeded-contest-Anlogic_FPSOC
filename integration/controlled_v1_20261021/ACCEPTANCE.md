# 分阶段验收与当前状态

本候选未获部署资格。工程来源/离线软件可审查，不等同于镜像启动、无电机实板验收或机械运动许可。最终P&R结论在`RESOURCE_REPORT.md`独立记录，不能用PROFILE0缩减逻辑尝试替代完整系统。

|阶段|项目|结果|证据/限制|
|---|---|---|---|
|A|固定实际PL输入、19个候选覆盖文件|PASS|frozen/pl、sources.json、input-audit.json；不是当前产品工作树|
|A|真实保护/WD/反馈超时场景来源对应|PASS复用|每场景71份编译来源审核；显式记录旧内联头展开及实际使用宏值；不当硬件综合等价证明|
|A|功能证据|PASS复用|原375安全/停止相位、33原回归、371安全服务miter、66799服务差分、采集差分、65536时间向量、262208饱和函数、32800 GP周期、41330运输周期及真实双DMA三场景；完整候选内部RTL未改|
|A|生成定义/旧ABI|PASS|干净规范及生成物检查；旧常量不重定义，R5S2严格单独识别|
|A|实际PS基线|PASS配置审核|仅HP1启用/64bit差异，其余原DDR/存储属性保持；不证明实物电压或训练|
|A|新固定管脚完整顶层P&R|PASS无负STA；FAIL严格>1ns|最终100MHz setup +0.078ns/hold +0.020ns，负违例端点0；Slice36670/ERAM69/DSP6/PAD9；16线程读回5次。见RESOURCE_REPORT；原rtl_path38+0.032/+0.020只属原候选|
|A|最终物理/发布资格|BLOCKED|SYN-5066、同步器/CDC、IO外部时序、实物速度、生产HOME、DDR drain均未关闭|
|A|GP/DMA/运动/采集/安全/Wi-Fi七模块|PASS编译与身份|wifi1同源码/输出/.config/Module.symvers；vermagic和全部导入CRC匹配|
|A|SAF2诊断软件|PASS模型79项|提取实际驱动函数，验证配置accepted/applied分别观察、IRQ保留/屏蔽、快照/资格拒绝/回读/不接管旧owner/无运动或心跳写；不是实板|
|A|R5S2软件适配|PASS模型23项|旧profile拒绝、RUN-off配置、RUN回读、配置错误及只读观察无副作用；不是有效反馈或DDR证明|
|A|诊断JSON格式|PASS宿主mock|u64十进制字符串、到期相等为stale、未见反馈为null、生产批准false；未触碰设备|
|A|Wi-Fi/HTTP|PASS离线|STA原4项、HTTP原4项、新路径/首页链接共5项；认证、拒绝、逐字节文件与旧功能保留；不是本候选LAN验收|
|A|七窗口/八SPI|PASS|实际七路译码460项；编译DT cells/ranges/GIC冲突审核；所有节点disabled|
|A|实际ext4内容|PASS离线|最终安装文件取出与直接源码/二进制逐字节比，11固件别名、账户/凭据/批准缺席、e2fsck通过；VM→Windows最终rootfs匹配|
|A|分区与配套启动链|PASS离线 / 发布BLOCKED|本次用户免除>1ns生成条件；新bit/HPF/FSBL/BOOT/DTB/wifi1/rootfs/SD一致链已生成，镜像实际两分区/启动文件/rootfs检查通过，根f0391b66-02；控制节点disabled，其余门禁保留|
|B|新SD根、内核/PL/profile、1GiB/CMA、IRQ空闲|NOT_EXECUTED|已生成SD文件，尚未写入实体卡，未接入COM4；配置审核不替代读回|
|B|受控快照、统一时间、IRQ与DMA空闲|NOT_EXECUTED|模型和预览DT不代替板端身份及静态接入|
|B|STA、电脑→板ping、认证HTTP、逐字节下载|NOT_EXECUTED本候选|2026-10-19首版SD加两修复已有通过记录；r3只有离线通过，均不冒充新候选|
|B|重连、用户冷启动、至少10分钟稳定|NOT_EXECUTED本候选|先完成同一启动链，再按原LAN脚本验收，记录丢包/方向及HTTP失败|
|C|配置commit/apply、owner/序号、超时、清错门、旧任务不复活|NOT_EXECUTED实板|当前诊断只支持快照/配置/明确无电机超时实验；完整健康循环、清错与恢复须受控执行后端及实体资格|
|C|无从机RS485超时运输|NOT_EXECUTED|可作为后续明确命令的运输诊断，不算保护健康反馈|
|C|真实RS485从机、实体安全输入|NOT_EXECUTED|已固定四路引脚/低有效；实际外部上拉、接线、固件与反馈资格仍待测试|
|C|DMA正常接收/长度/CRC/独占消费|NOT_EXECUTED实板|须精确N×64，保存原始包后COMPLETE；IOC/残量0不代替实际长度|
|C|取消/局部恢复/DDR静止/buffer释放|NOT_EXECUTED / BLOCKED|未经证明的中断RX保持quarantine，不添加validated drain属性，不靠PL drained释放|
|D|GPIO波形与机械运动|LOCKED|本次未授权HOME/ENABLE/START或示波器接管；生产参数、接线/门禁及当次条件明确后另行推进|

阶段B开始前必须得到同一新工程的合格启动链、当次SD身份与覆盖授权。先检查启动根/内核/PL三者身份，再显式装载受控驱动；不运行旧board_scope_ready/init脚本，不自动打开owner、轮询、REBASE、HOME、ENABLE或START。静态读取和快照也须记录实际profile/config ID及IRQ计数前后变化。

阶段C通过条件分别登记：真实485健康应答必须满足当前epoch/round、每轴正确0x3E和有效枚举/时基；输入测试记录逐路接点、电平、极性和最大响应；正常RX记录请求长度、IRQ锁存实际长度/错误、CRC、packet/gen以及数据保存/COMPLETE；中断RX另需HP1/DDR写静止资格、回调/描述符全静止和buffer所有权证明。任何一项失败不由另一项成功抵消。

当前任务状态：

- 板卡：本任务未连接、未读取实时状态。历史2026-10-19记录为已验收首版70d791a8-02加两修复、Wi-Fi/HTTP运行；这不是当前状态读回。
- 串口：本任务未打开COM4，未改变DTR/RTS，未操作板卡电源或示波器；端口当前是否被用户占用未探测。
- 服务：本任务未在板卡安装/启动执行后端、诊断或网络服务；现有网络/HTTP实际运行状态未知。
- DMA/buffer：本任务未在板卡加载新模块、申请coherent buffer或启动DMA；板上其他历史owner/buffer状态未读取，不能推断为已静止/释放。
- 存储：SD/eMMC/QSPI均未写。当前已验收Wi-Fi系统与scope回退文件保留，未覆盖用户AGENT.md/.gitignore/BACKUP.md及其他任务修改或日志。

本轮可交付范围是受控离线候选、完整启动链SD文件及复现/诊断/回退说明。镜像离线生成通过；完整工程发布、实板冷启动、无电机实板验收、机械运动许可仍分别受门禁控制，均不能由镜像生成或时序数字代替。
