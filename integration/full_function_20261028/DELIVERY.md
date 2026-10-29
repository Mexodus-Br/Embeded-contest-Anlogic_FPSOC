# 除 NPU 外首版全功能镜像交付

状态：**已实现并离线构建/校验完成，实板未验收**。基线 a21751d；软件实现提交421b3ea、c8be1b5；最终构建输入提交67c276b。版本 full-function-20261029-r1。当前工作区其他任务脏RTL未混入。

镜像：`D:\Works\Embedded_contest\dev\integration\full_function_20261028\artifacts\release-r1\sdcard.img`（536870912字节）。同目录包含11个必要最终产物、manifest.json和SHA256SUMS。VM来源：`/home/uisrc/embedded-full-function-20261028-r3/output/release`。

镜像SHA256：`3340b2dd9a58d99ba2bc5004b498ca8705cabb451f69393e401ec0bee7d5edc5`。完整11项校验清单见`artifacts/release-r1/SHA256SUMS`；下载后逐项重算全部一致，没有哈希日志或中间目录。

构建源码：`67c276b9757bcbc91fdedcf948754679d4b0cf36`。精确CONFIG_ID：`4af692d07e401144a177ad0c3c37ac0ae3ed4fc2ca49f97ec81d5d249979a45f`。根分区PARTUUID：`3201cd3a-02`。

## 实现与运行资格

已接通真实 Service→LinuxBoard→SAF2/MOTION/RS485/DMA，全功能HMI及统一Web/本地命令入口，XYZ空间直线、加减速、方向、多点/重复、示教、参数/任务持久化、有界日志查看下载、原始反馈与独立HP1历史。真实设备缺失报错；测试假板卡不编入镜像。NPU未实现；已取消/暂缓项未恢复，未恢复CDC独立门禁。

机器XYZ来自三轴0x30→标定角度→验证FK，显示零为正式HOME退离姿态。Golden几何/原厂齿比保持不变；Golden目标与PL HOME计数显式映射，触点-150/退离0不代表机械零。工作XYZ只通过PS偏移平移；设零不写硬件、不REBASE/使能/运动，原预览失效，机器边界固定。

网页模板不预填机械测量值。先HOME，再填写机械参考、编码器映射、机器工作区/XY包络/禁区、逐轴机械角界与余量并保存新版本，再显式验证。保存本身不建立位置有效性，反馈缺采/陈旧/身份变动/偏差超容差撤销资格。HOME、真实标定、边界和执行资格分别检查。首次速度/加速度后端上限20mm/s、20mm/s²，可降低；指定时长不可执行则拒绝。首段、循环返回、方向路径均保留XYZ/角度/IK/脉冲检查。

启动仅观察，不自动HOME/ENABLE/运动/接管旧owner/恢复任务；不确定RX buffer保持quarantine。普通STOP后允许可靠停稳位置设零，下一次执行须显式恢复运输。故障、取消、失联、重启不能复活任务。

## PL与启动链

独立工程hardware6取自已核对完整冻结PL输入，任务候选只分离DIR寄存器控制的等价逻辑、开放具备资格的普通运动，并保持确认的时序/HOME参数。DIR变更对冻结版逐拍比较32场景15427周期，STEP/DIR/EN/计数/有效位/会话/状态完全一致。接口、MOT2和冻结遥测语义不变。完整输入清单见hardware6-inputs.json。

TD Release_2026.1_SP2，threads=16。完整P&R后选择refined6.db，最终恢复原始100MHz约束：setup WNS **+0.312ns**，hold **+0.020ns**。最新用户要求本次优化后WNS>0ns即通过；该结果也满足此前0.2ns要求。未降低时钟、未增加假路径。

|资源|使用/总量|占比|
|---|---|---|
|LUT6|29134/52480|55.51%|
|Slice|37232/52480|70.95%|
|Slice寄存器|37515/104960|35.74%|
|ERAM|69/280|24.64%|
|DSP|6/240|2.50%|

同工程bit/HPF逐字节一致，556项导出PS参数与工程一致。新FSBL由该HPF生成，GP/HP0/HP1复位掩码0x33。PS/DDR配置与原验证基线逐项比对，DT头及可执行PS初始化保持一致。

内核为既有匹配6.1.111-rt42-bsp-wifi1的精确uImage，未重新编译无修改的内核；本批重编译SAF2/485驱动与ARM应用，并审核212个模块的vermagic/3556项导入CRC、DT往返及ELF运行库闭包。rootfs/BOOT/DT/SD文件重新组装，不混用旧HOME-only应用。分发无个人Wi-Fi凭据或认证令牌，默认loopback；现场配置具体LAN地址后使用认证HMI。

## 验证范围与保留问题

完整功能清单、实现/离线/实板分栏及证据见ACCEPTANCE.md；后续分阶段步骤见OPERATIONS.md。离线通过不能替代电气/机械/真实DMA验收。原始HP1历史为512记录有界窗口，公开截断、缺序号和陈旧状态，不称完整历史，也不以latest缓存补齐。

保留厂商保护IP SYN-5066警告（不可据此宣称保护IP等价证明通过）；约束报告仍有5项输入/2项输出延时待电气确认，以及保护IP内部2类悬空复位节点。实际速度等级、DDR、电气时序、485保护/急停、HOME与机械XYZ/角度映射均未实板验收。延时、HALTED或PL drained均不是HP1/DDR写静止证明；不确定buffer保持quarantine。manifest的signoff_pass=false表示未获得完整物理实板签核，不表示本次WNS门槛失败。

本次不写卡、不访问实机、不操作eMMC/QSPI。交付后本轮结束。


## 最终验证证据

镜像制作已通过新HPF/FSBL/BOOT关联、模块CRC、DT往返、运行库ABI、ext4 fsck、14个安装文件逐字节读回、512MiB镜像分区逐字节读回及FAT文件读回。`artifacts/release-audits`保留VM日志、模块/ABI/FSBL审计和本地11产物哈希匹配记录，均未作为中间目录执行哈希。

最终软件测试：核心7项/Golden基准10项、标定6项（108空间点FK/IK及独立几何残差）、HTTP14项、边界5项、真实后端假板卡24场景、浏览器完整交互（包括非零位置设零和断网STOP）、本地命令与串口行协议。内核实际函数测试安全45、provider65、RX所有权/CRC/取消32；RTL安全32场景、HOME54、普通运动门禁410、互锁79、解析等价68728、owner投影20480、真实100MHz时序24项/3007517周期、DIR候选逐拍等价15427周期。测试假板卡只用于离线测试，没有在发布rootfs中替代真实后端。

已实现且离线通过；**实板通过项为零**。剩余是上述明确列出的真实电气/机械/反馈/DMA验收证据及现场参数输入，没有把缺失功能记作“仅待上板”。本轮未写卡，未上板执行HOME或运动，未操作eMMC/QSPI。


2026-10-29 后续追加：用户已明确确认本次SD目标并授权写卡，现已完成512MiB写入及完整无缓存读回，SHA256一致。此项取代本文先前“未写卡/本轮不写卡”的阶段状态；实板仍未启动、未执行HOME或运动。详见[SD_DEPLOYMENT.md](SD_DEPLOYMENT.md)。
