# 最终离线交付：r4

2026-10-26，Asia/Taipei。**离线系统装配与检查完成；真实XYZ/方向/RS485产品接入仍有明确缺口，不能登记完整功能交付完成。** 供第2阶段有条件静态验收准备，第2阶段未执行、第3/4阶段运动保持阻塞。不把镜像生成当作写卡或运动许可。

## 文件和身份

- 本机镜像：`D:/Works/Embedded_contest/dev/integration/full_system_20261026/artifacts/release-r4/sdcard.img`
- 大小：536870912字节（512MiB）。
- 最终镜像SHA256：`e0d5abb1235b74665752396c3faff9beca49c084803bd5d4f4b095e232db90de`
- 源码提交：`1ff2e40bd91ae57c4cfb6c7abbff43b87315c0c8`；无工作树源码覆盖。交付文档后续提交不改变此编译身份。
- 版本：`full-system-20261026-stage2-r1`；根PARTUUID：`f1beebfc-02`。
- VM最终工作根：`/home/uisrc/embedded-full-system-20261026-r4`；不覆盖原controlled、scope、Wi-Fi或motor3125目录。
- 同目录含BOOT.bin、system.bit、system.hpf、fsbl.elf、u-boot.bin、uImage.lz4、system.dtb、rootfs.ext4、boot.cmd/scr及manifest.json、SHA256SUMS。仅对这11项必要最终交付物哈希；日志、审计、临时FAT、源码快照归档均未哈希。
- PL/HPF/FSBL/BOOT为4b2579e受控候选的同批固定输入；wifi1内核、原内核源码/输出与Buildroot GCC7.5匹配；本次未改PL、未重跑P&R、未修改其他任务脏RTL。
- r1失败、r2/r3前序候选与下载文件保留。**以release-r4为最终交付，不使用artifacts/release里的r3。**

## 已完成离线验证

|检查|结果|
|---|---|
|目标执行模块|原wifi1内核树与GCC7.5、W=1/-Werror构建通过；修复首次if/break缩进警告，保留原失败现场|
|全部安装模块ABI|212个模块、3556个导入符号CRC逐项匹配；vermagic=6.1.111-rt42-bsp-wifi1 SMP preempt mod_unload modversions aarch64|
|ARM程序|ps_server/ps_control用该Buildroot GCC7.5构建；AArch64和/lib/ld-linux-aarch64.so.1核对通过|
|运行库|补入对应libstdc++，检查每个DT_NEEDED依赖闭包及逐库版本要求，包括GLIBC_2.25、GLIBCXX_3.4.22、CXXABI_1.3.9；未用Windows7.4产物替代|
|DT|启用六控制节点，SAF2改execution compatible；反向还原后DTS与原同批DT逐字比较通过；地址/IRQ/1GiB内存保持，不添加validated HP1 drain|
|rootfs|最终ext4内12个新增/更新安装文件逐字节读回一致，e2fsck只读检查通过；不存在预置Wi-Fi凭据/HMI令牌或LAN绑定批准|
|SD文件|512MiB MBR、两分区全字节读回比对、FAT四启动文件读回通过；FAT/EXT4只读fsck通过；本机MBR/PARTUUID再次核对通过|
|传回身份|本机11项最终交付物大小/SHA256全部与VM manifest一致|
|宿主行为|18项真实后端假板卡场景和真实schema通过，含未批准HOME在入队前拒绝；执行驱动41项实际C函数模型通过|
|HMI与本地入口|服务14项、边界5项、显式非默认IPv4绑定/Host/Origin/认证、本地持久会话/同boot/STOP/release通过；最终网页四项方向边界回归与语法通过|
|脚本|VM系统sh与Python3.6对最终启动/本地入口语法检查通过|
|实际运行边界|未在ARM实体上执行应用，未实板启动、接串口、写SD/eMMC/QSPI或运动；ELF/ABI和宿主测试不能替代这些实测|

原始离线审计在本机 `artifacts/r4-audits/`，不哈希。额外失败记录：早期后台启动未实际启动；沙箱localhost受限、默认Python缺jsonschema；一次JS测试工作目录错误。分别用明确工作根、已有隔离依赖/沙箱外localhost及正确ps_app工作目录复测通过，不把失败改写为通过。

## 启动与运行边界

启动自动装载匹配provider/motion/SAF2执行模块，0600设备仅root访问，启动一个hardware服务默认127.0.0.1:18083。服务启动仅观察/快照；驱动probe会STOP并做DMA静止检查，不自动OPEN/FEED/HOME/REBASE/ENABLE/START/RUN，不重放历史任务，设备缺失直接失败。错误/不确定性允许保守STOP，不切换模拟、不自动重启服务。当前HMI设备所有者进程仍需root/CAP_SYS_RAWIO；未宣称继承旧UID498诊断网页的低权限资格。

本地命令 `ps-local state|telemetry|stop|release|action NAME|request` 访问同一Service，不打开第二个硬件owner。`saf2-maint`是服务退出后的独占配置/无电机诊断入口，不与服务并开；无无条件后台喂狗。

最终HOME API明确返回PRODUCTION_HOME_UNAPPROVED，网页禁用HOME。当前PL PROFILE2方向101、参考100/-200/300和退离参数是测试夹具，与用户确认+Z生产HOME不一致；需生产参数定稿后独立PL与匹配启动链/受影响验证。不能以更改软件标识解除。

## 剩余限制和阶段停止点

1. RS485的0x30是单轴编码器候选来源，0x33是有符号接收命令脉冲。采集白名单和解码已有；唯一owner原始32B/64B发布、RUN-off/采集管理尚未接入服务。driver_feedback与xyz_estimate保持null，不能把SAF2 feedback_qualified当作服务已取得每轴反馈。
2. 按用户补充，用PL已发增量↔0x33接收增量↔0x30实际变化核对符号、脉冲倍率与跟随。XYZ还需原厂实际模型的FK、每轴编码器参考/方向/传动映射和异步采样规则。原固件的-0.48rad/(0,0,-140)直接赋值不是新系统机械零点。
3. cf764ad为MOTOR3125：STEP高/低31.25µs、16kHz参数；本PL仍5µs、100kHz参数，DIR setup/hold均5µs、引脚与普通DIR逻辑一致。未做新PL，因此必须在第3阶段前确认实际脉宽适配并实测；若需修改则重做受影响PL与启动链。
4. SYN-5066受保护IP、外部IO、电气/安全输入、实物速度/DDR、实际STP并发反馈和HP1中断RX的DDR静止仍按原实际影响保留。CDC独立门禁未恢复。未知RX写保持quarantine，不用延时/PL drained解禁。
5. 第2阶段只能在当次卡/串口/隔离/启动授权后逐项开始；心跳/真实反馈与完整恢复子项仍受上述缺口影响，不能总记PASS。第3/4阶段运动不放行；日志/任务存储与网页只读部分可在第2阶段条件满足后独立记录。

详见[位置/方向核查](POSITION_RS485_REVIEW.md)与[分阶段命令、标准和停止条件](ACCEPTANCE.md)。

## 部署步骤（尚未授权执行）

1. 准备独立候选SD，保留cf764ad及现有回退卡。重新读取当次卡的型号、容量、序列/UniqueId、系统盘排除和当前内容身份；向用户明确申请覆盖许可。2026-10-26只读枚举曾看到Disk1 Generic- SD/MMC/MS PRO，31708938240字节、USB、非系统盘；SerialNumber为空，UniqueId指向读卡器，不足以独立证明哪张SD。**不能据此直接写Disk1或认定它不是回退卡。**
2. 取得该卡覆盖许可后才完整写镜像，执行覆盖长度完整无缓存读回，核对MBR及根f1beebfc-02。写卡过程另行记录，不写eMMC/QSPI。
3. 用户负责断电、脉冲隔离/接线、换卡和上电。当前只读串口枚举为COM9、COM10，没有历史COM4；它们的板卡归属/是否被占用未确认，本任务未打开任何串口。
4. 确认当次正确空闲串口后，以115200/8N1、无流控、DTR/RTS=false查看启动。对照/etc/full-system-identity.json、uname、cmdline、设备权限、ps-local state/telemetry及IRQ登记静态身份。
5. 默认loopback。若要LAN访问，由用户本地配置已批准Wi-Fi和/etc/ps-hmi/bind-ipv4，按验收清单维护重启服务后使用准确地址:18083；HMI令牌只在板端root读取。不会自动沿用旧凭据或放宽认证/Host/Origin。
6. 严格按第2→3→4阶段推进，问题先定位修复再复测受影响项。当前未取得当次SD覆盖许可，未确认串口可用和实物隔离，不继续板端操作。
