# 受控集成候选：离线交付入口

先读`REVIEW.md`和`ACCEPTANCE.md`。最终资源与时序见`RESOURCE_REPORT.md`；原候选与新固定管脚顶层分开登记。发布资格保持false，不将无负STA解释为全项目放行。

独立来源在`frozen/pl`和`frozen/software`。这些目录已经保存固定输入，日常复验不要重新复制产品工作树；`prepare.py`只用于重建一个不存在的冻结目录。首次完整重建顺序为：

```powershell
python integration/controlled_v1_20261021/prepare.py
python integration/controlled_v1_20261021/complete_inputs.py
python integration/controlled_v1_20261021/adapt.py
python integration/controlled_v1_20261021/add_dma_observation.py
python integration/controlled_v1_20261021/prepare_hardware.py
python integration/controlled_v1_20261021/audit_inputs.py
```

脚本拒绝覆盖已有冻结输入/工程。复验已交付目录时，只运行check/audit或使用新的独立副本/tag。TD命令如下；新工程须从相同原始完整输入重建，不复用本任务失败PROFILE0的数据库：

```powershell
td_commands_prompt.exe D:/Works/Embedded_contest/dev/integration/controlled_v1_20261021/hardware/run.tcl
```

脚本各阶段显式16线程并读回，原100MHz/10ns SDC逐字节保持，最终名义报告先清除内部优化预算。只有新实际顶层最终route报告才作本候选结果。没有bitgen步骤。

七路路由补测用`test_router.py --tag 新tag`；此Windows Icarus在受限沙箱内退出0xC0000005，同源码在获准非沙箱环境已通过460项。保留失败tag，不降低断言。不要将编译器异常或仅有VVP文件视为编译通过。

Linux构建VM采用`/home/uisrc/embedded-controlled-v1-20261021`，候选源码在其`candidate/`。认证通过本地交互或会话内凭据，不写入脚本/文档/Git。只需在新TASK目录放入本目录源文件，然后依序运行：

```sh
bash candidate/build_software.sh
python3 candidate/test_driver.py
python3 candidate/test_http_integration.py
python3 candidate/test_r5s2.py
bash candidate/build_wifi_modules.sh
python3 candidate/audit_software.py
python3 candidate/build_preview_dts.py
python3 candidate/build_offline_rootfs.py --tag complete
python3 candidate/audit_final_rootfs.py
```

既有依赖：原`embedded-bsp`的Linaro工具链/vendor输入，`embedded-bsp-wifi-20261018`的同一wifi1内核源码/输出和Buildroot host，已离线验证的干净`embedded-bsp-wifi-http-20261019-r3/output/rootfs-target`。Wi-Fi驱动从原vendor-input.zip只提取源码/固件并应用固定privacy patch，不带旧对象；全部七模块检查每个导入符号CRC。原rootfs仅作基础，最终安装文件从实际ext4提取逐字节比较，检查11个固件别名、账号/凭据/批准缺席及只读fsck。镜像不是仅检查暂存目录。

本机最终离线文件在`artifacts/`：rootfs-offline.ext4、preview-disabled.dtb、七模块、ARM saf2-diag/rs485-accept，以及实际使用的kernel.config/Module.symvers。DTB只是七窗口禁用预览，rootfs没有配套BOOT/bit/HPF/FSBL或SD分区，不能写卡启动。最终P&R已复核：100MHz setup +0.078ns/hold +0.020ns，无负STA，严格setup>1ns未达，signoff仍false。最小交付清单见`delivery.json`，最终资源见`RESOURCE_REPORT.md`；本轮交接和只读进度查询见`HANDOFF.md`与`status.ps1`。日志、数据库和整棵证据目录不哈希。

本任务先后发现并保留：新增驱动编译错误、生成器缺依赖、AIC跨模块符号核对缺项、测试夹具宏冲突、Windows沙箱Icarus异常，以及PROFILE0缩减运动逻辑导致的无效约束。修正后通过项与仍开放门禁分开，失败日志在本机`evidence/`、VM build及`hardware_profile0_rejected/`。

**只有以后配套启动链和阶段B身份门禁通过，才使用以下板端显式入口。本轮未执行。**

```sh
saf2-diag snapshot
saf2-diag config 1 7 2000000 2000000
saf2-diag watchdog-timeout --no-motor
integration-export
```

配置txn必须大于当前accepted值；1只是新epoch示例，不重用历史事务。timeout命令仅在停稳、EN失能、RUN关闭、无owner/新增联锁故障时尝试新OPEN，故意不喂狗，等待超时并检查锁存/owner撤销；命令退出、服务重启都不续喂或清错。快照中的config_valid不能当生产HOME批准。global和interlock是两次独立原子快照，各有ID与时间，不保证同拍。

`integration-export`仅本地root显式执行，原子发布脱敏稳定文件；包含生成定义解释的profile/config/IRQ、u64时间/owner/序号、反馈年龄与新鲜性以及现有RX owner的只读DMA生命周期观察。未绑定RX设备时明确记录未知。HTTP GET只读已发布文件；UID498不能控制设备、上传或执行shell。认证下载`/files/integration-snapshot.json`，与板端同一稳定文件逐字节比较，不哈希快照。网页链接在网络快照刷新后仍保留。

RS485现有显式`rs485-accept idle|diagnostic-timeouts|cancel|release`只用于后续匹配系统；超时模式会查询UART，不能隐式启动或作为真实保护反馈。先投精确RX再ARM，COMPLETE之前保存数据。取消/恢复失败保留quarantine，不卸载或复用buffer，不以PL drained解除DDR门禁。

后续无电机启动链须先具备受保护IP、最终实际P&R/有效约束、IO/CDC和PS/复位等对应发布资格，随后从同一个新实际工程生成bit/HPF，用该HPF重建FSBL并核对GP/HP0/HP1内部reset释放，生成匹配DTB，再组成BOOT、wifi1内核、最终rootfs及SD分区；重新审核最终分区/文件系统/启动文件身份。生产HOME与机械参数仍可保持阶段D门禁，不能用PROFILE2放行真实运动。中断RX的DDR静止资格属于独立门禁，未证明时保持quarantine，不妨碍具备其余资格后的静态接入或有界正常IOC检查。旧scope的BOOT/HPF/DT头仅用于历史回退/禁用预览，不能与本候选PL混装，也不能只换bit。

写卡前重新读取当次SD型号、容量、序列/身份、UniqueId及系统盘排除，并取得覆盖授权；本轮没有写卡授权对象，不沿用disk1。经审核后完整写入/无缓存读回并核对分区和PARTUUID。COM4仅确认未被用户占用后接入，115200/8N1、无流控、DTR/RTS=false；用户自行断电、装卡、上电。不写eMMC/QSPI。

回退首选保留当前已验收Wi-Fi SD，并使用另一张卡做新候选。其历史身份是70d791a8-02加U02别名与STA权限两项持久修复，不能当作原镜像文件逐字节相同。若以后必须覆盖这张已验收卡，先把当次实际启动链、有效分区及本地配置备份到Git外私有位置并验证回退，保护其中凭据；旧首版分发img不包含后补修复/本地凭据，不能代替当前卡的完整备份。r3根82e6e1bc-02只离线验证，没有本批冷启动验收。另保留scope回退镜像根8aea5f8d-02。若需要重写回退镜像，同样重新核对卡并确认覆盖；新镜像不含个人凭据，需本地重新配置和批准Wi-Fi/HTTP。
