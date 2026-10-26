# 完整软件接入镜像工作记录

**最终离线r4交付已完成并传回核验。** 镜像、提交、SHA256、版本、PARTUUID、检查结果和部署边界见[DELIVERY.md](DELIVERY.md)；最终本机文件在`artifacts/release-r4/`。XYZ/方向/RS485产品功能与实板验收仍未完成，不以镜像装配掩盖这些缺口。

起点 b9239a1，固定PL启动链取自4b2579e的controlled_v1_20261021，保留其他任务的未提交RTL、旧镜像、回退卡与全部失败记录。此目录制作新的系统文件镜像，不写实体卡、不连接板卡/串口、不操作eMMC/QSPI。CDC独立门禁保持已移除状态，不新增4G计划。

## 实现核对与当前缺口

|项目|处理|
|---|---|
|目标内核|使用VM原wifi1源码、输出、.config和Module.symvers；新增执行模块在原GCC7.5下W=1/-Werror构建；逐个核对安装模块所有导入CRC|
|C++运行库|Buildroot原rootfs未带libstdc++；用该Buildroot工具链构建用户态并补必要对应运行库；核对AArch64、解释器、全部DT_NEEDED闭包及每个库的版本要求|
|DT|从同批HPF生成的原DTB仅启用六控制节点，将SAF2 compatible换为execution；结构化反向修改后与原DTS逐字比较；地址/IRQ/内存不变，不添加DDR drain属性|
|设备权限|/dev/bsp-motion和/dev/bsp-saf2-exec为root:root 0600，CAP_SYS_RAWIO检查保留；镜像不安装SAF2诊断模块，避免两个绑定所有者|
|启动|只启动一个hardware服务；无自动OPEN/FEED/HOME/REBASE/ENABLE/START/RUN或重放。运动模块probe原有STOP和DMA静止检查保留，失败不回退模拟/不自动重启|
|HMI|安装实际网页/资源/任务与日志服务；新增显式--bind具体IPv4，默认loopback；保留准确Host/Origin、认证、CSRF及STOP独立容量；不接受wildcard绑定|
|本地命令|ps-local通过认证HTTP访问同一Service，不另开设备owner；本地持久会话与网页控制权互斥，交接用release。ps_control保留为独立行式适配器，不与服务同时运行|
|维护配置|saf2-maint复用诊断UAPI，目标为执行设备；与服务独占互斥，显式无电机config/timeout实验，不作为后台喂狗进程|
|真实XYZ与方向|尚无获准FK/标定/驱动旧目标一致性处理；保持未知，真实jog/teach拒绝，坐标预览不能执行。没有新增伪参考位置API，未改Golden|
|RS485服务发布|32B/64B尚未由唯一采集owner发布，driver_feedback=null；R5S2采集管理/RUN-off、raw副本/身份仍需实现，不能把SAF2保护资格当完整服务反馈|
|生产HOME|当前PL为PROFILE2夹具，方向101与用户确认+Z不一致，参考100/-200/300步非实物标定；最终后端入队前明确拒绝HOME。生产配置需要PL变更与受影响验证|
|权限隔离限制|当前设备所有者HTTP进程为root；原UID498诊断HTTP不具控制权，不能把其低权限资格套用到新HMI。局域网服务仅本地显式配置后开启|

**因此：镜像可完成系统软件装配和离线检查，但不能登记为真实坐标/方向/RS485产品功能全部完成，也不能把第2阶段总记PASS或直接进入第3/4阶段运动。** 缺口不是“仅剩上板验证”。分阶段操作、通过标准与停止点见[ACCEPTANCE.md](ACCEPTANCE.md)。

## 与cf764ad逐项对照

cf764ad实际写入的是MOTOR3125，不能按早期scope默认5µs理解。对应证据为bsp/motor_test/prepare.py、CONFIG.json及独立system_wrapper.v；完整PL参数在controlled冻结system/hdl/system_wrapper.v:240。

|项目|cf764ad MOTOR3125|本镜像复用完整SAF2 PL|
|---|---|---|
|时钟|100MHz|100MHz|
|A0 STEP/DIR/EN|J12-3/4/5；Y12/Y13/T9|相同|
|A1 STEP/DIR/EN|J12-6/7/8；U10/T5/U5|相同|
|A2 STEP/DIR/EN|J12-9/10/11；V6/W6/U7|相同|
|STEP高/最低低|3125/3125拍，31.25µs|500/500拍，5µs|
|最高步频参数|16000Hz|100000Hz；不是本次允许运动速度|
|DIR setup/hold|500/500拍，5µs|相同|
|EN setup/disable guard|500/500拍，5µs|相同|
|普通运动DIR逻辑|正步数DIR=1，负步数DIR=0|相同；不是机械XYZ正向证明|
|EN|高有效；驱动HOLD可能忽略EN|高有效，增加安全层失能，仍需实物核对|
|M4|配置0，无实体输出|相同|
|首步guard|3127拍|1002拍；不能复用旧波形oracle|
|安全/采集|裸motion，无完整SAF2/R5S2|SAF2联锁/看门狗/反馈与独立HP1采集|

仅软件集成无需重新布局布线；本批不改变PL/bit/HPF/FSBL/kernel。5µs与31.25µs差异会影响第3阶段资格，必须先确认实际驱动脉宽要求并实测本镜像波形。若确定要改脉宽/生产HOME参数，另做独立PL工程，显式16线程，重做受影响RTL/完整P&R、同批启动链、离线检查和波形验收，不用旧bit配新标识。

## 构建与部署边界

本机运行prepare.py生成最小源码快照，VM新建独立目录解包后运行python3 -u build_vm.py。复用~/embedded-controlled-v1-20261021的只读固定输入和~/embedded-bsp-wifi-20261018匹配内核/Buildroot；不覆盖旧镜像或重新冻结当前脏RTL。每个失败尝试保留，新尝试使用新目录。

build_vm.py依序编译执行模块/ARM程序、检查模块CRC/ELF/库ABI、组装rootfs/DT、从实际ext4取出安装文件比对、只读fsck、组装512MiB SD文件并读回两分区与FAT启动文件。仅对明确最终部署文件计算SHA256，不递归哈希、不哈希日志/中间文件。

最终交付为release-r4，对应源码1ff2e40；r3仅为前一软件装配候选，最终批次增加HOME拒绝以防误用PROFILE2。最终manifest包括源码提交、启动链来源、版本、PARTUUID、最终交付文件SHA256和功能限制。板端/etc/full-system-identity.json保存软件/PL来源与限制，不冒充实时硬件身份。

部署必须先取得当次SD覆盖授权，再完整写入与读回。用户断电装卡上电；串口仅确认可用后接入。无Wi-Fi个人配置、HTTP个人凭据或预设HMI令牌。默认localhost观察服务；本地明确配置IPv4后维护重启，使用板卡LAN地址:18083，令牌在板端root权限读取，不能发送到日志或Git。

## 已执行检查与失败

- Windows本机构建ps_core/ps_server/ps_control通过；新增显式绑定、wildcard拒绝、Host/Origin/认证检查通过；原服务14项、边界5项通过。
- 新执行模块41项实际C函数寄存器模型复测通过；宿主警告与内核编译结果分开记录。
- 首次沙箱回环测试无法连通，默认Python缺jsonschema；使用现有隔离依赖并在沙箱外仅运行localhost后通过，不把环境失败记为业务通过。
- VM r1执行模块在-Werror=misleading-indentation失败；仅拆分if/break行，原失败目录保留。r2/r3目标模块、用户态、模块CRC、全库ABI、DT反向结构比较、ext4安装文件比对、fsck和SD两分区/FAT启动文件读回通过。最终r4增加HOME拒绝后重新构建，以上检查及传回身份全部通过，见DELIVERY.md。

用户后续确认的RS485反馈来源、原厂实际模型、HOME +Z/退离-Z及缺少的标定见[POSITION_RS485_REVIEW.md](POSITION_RS485_REVIEW.md)。没有把这些方向确认扩展为生产参考/距离/速度批准。
