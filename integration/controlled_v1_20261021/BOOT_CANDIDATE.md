# 离线启动镜像候选

2026-10-21后续决策：用户移除CDC及同步器资格的独立门禁，保留工程检查和已知问题跟踪；其他门禁不变，signoff仍false。下述生成授权及镜像manifest是生成时记录，当前门禁以REVIEW.md为准。本次仅调整政策记录，镜像未重建、未部署。

2026-10-21用户要求“生成启动镜像，本次忽略setup大于1约束”。该授权用于生成本次离线候选，保留100MHz/10ns、setup/hold非负条件；严格>1ns的历史目标仍记录为未达。其余资格未豁免，signoff=false，未取得任何当次SD覆盖对象或实板/运动许可。

本机文件：`artifacts/boot_candidate_v1/sdcard.img`，536870912字节（512MiB）。SHA256：`82852c8b6f2b1df213c57f2e620856dbddd7c05083761d204f6927fb2bed5fbf`。预期根PARTUUID为`f0391b66-02`。同目录保存BOOT.bin、system.bit、system.hpf、fsbl.elf、system.dtb、wifi1 uImage.lz4、u-boot.bin、rootfs.ext4及boot.cmd/scr/bif和manifest.json；详细身份见manifest。不得与scope BOOT或其他批次DT/驱动混装。

|内容|来源与检查|
|---|---|
|PL|本任务完整固定管脚最终route.db；100MHz +0.078/+0.020ns，bitgen明确16线程并读回；未重做布局或修改RTL|
|HPF|实际同工程PS组件导出并包含新bit；bit逐字节一致，556项PS配置与实际工程一致（具体计数见boot-hardware.json）|
|PS/DDR/存储|与已验收scope的生成头值一致，仅导出时间变化；实际soc_plat.c仅新增HP1复位释放和64bit宽度两项，原DDR/存储初始化逐字节保持；1GiB/32bit/1333MT/s/1.35V配置保持，不冒充实物测量|
|FSBL|独立SDK副本、新平台及新demo目录，用新HPF的soc_plat.c/h重建；仅既有HAVE声明兼容及common-reset补丁；反汇编检查GPPortEnable/P2F release及GP/HP0/HP1掩码0x33，非DMA-only恢复资格|
|DTB|用新HPF生成头，从原内核DTS源码重新CPP/DTC；USB Host开启，七窗口八SPI审核通过，所有PL控制/采集/DMA/安全节点disabled；1GiB/CMA128MiB保持|
|Linux/U-Boot|wifi1内核与已匹配七模块保持；U-Boot复用前核对新HPF的CPU/UART/MMC/DDR启动关键宏相同|
|rootfs|已审计的最终无凭据ext4逐字节保持；正确U02别名、STA权限修复、低权限认证HTTP及只读下载；旧scope/运动入口排除，不自动OPEN/轮询/HOME/REBASE/ENABLE/START|
|SD文件|FAT32 64MiB从LBA2048开始，EXT4 256MiB从LBA133120开始；MBR身份、两分区完整字节、镜像内四个启动文件读回一致，FAT/EXT4只读fsck通过；VM到本机最终交付文件校验一致|

新HPF原厂工具保留DDR调试输出于hardware/hpf-export.log，该输出不是实板训练记录。HPF初次验证曾误把PS组件Design.xml当完整顶层XML逐字节比较；已改为核对全部PS参数并独立保持完整顶层源码证据。首轮头文件核验遇到CRLF/LF规范化，原日志保留后按既有生成器换行行为核对。所有失败和告警保留，不改写成发布通过。

复现需要同版本本地TD和VM依赖。已有目录不覆盖：在新独立工作根重建，或先保留现有候选后为新一轮修改明确的tag/工作根。

1. 按README的冻结输入及完整P&R流程生成同一完整route.db；检查无负STA、资源、约束和门禁记录。
2. 在Windows执行`python integration/controlled_v1_20261021/build_boot_hardware.py`。脚本拒绝覆盖既有bit；只检查已生成文件时用`--verify-existing`。原TD路径失败日志保留在hardware/bitgen-path-failed.log。
3. VM工作根为`/home/uisrc/embedded-controlled-v1-20261021`，同级保留candidate/和build/。将build_boot_vm.sh、build_boot_dts.py、verify_boot_vm.py放candidate/，新HPF放boot_candidate_v1/system.hpf。将本任务boot_inputs/build_fsbl.sh、dts_from_hpf.py、make_sd_image.py放boot_candidate_v1/bsp/scripts/；kernel.dts放bsp/configs/；0001-gp-common-reset.patch放bsp/gp/fsbl/。登录口令不写入文件或Git。
4. 执行`bash candidate/build_boot_vm.sh`。它复制SDK到独立目录，从新HPF重建FSBL/DTB，使用相同wifi1内核和已审计rootfs生成SD文件。依赖原有工具链、Buildroot工具、vendor bootgen、dtc/fdtget、mtools、dosfstools、e2fsprogs及build/dts-preview/audit.py；不改共享SDK/内核或其他实验。
5. 执行`python3 candidate/verify_boot_vm.py`；仅校验明确最终交付物，分区和rootfs采用逐字节比较。将output/release的12个最终文件及manifest传回，校验最终文件身份，保存审计JSON和日志。日志/数据库/boot.vfat/中间目录均不加入哈希清单。工具版本固定可复现流程和输入；HPF导出时间不同会改变文件身份，不承诺跨次生成字节完全相同。

当前仅完成离线生成和审计。SYN-5066、外部IO时序、电气/接线和实物速度/DDR资格仍开放。CDC/同步器保留工程检查与问题记录，不再作为独立门禁。生产HOME/驱动参数、真实485保护反馈、中断RX后的DDR静止保持各自门禁。禁用节点不能用于宣称受控快照或DMA验收通过；后续静态接入须在资格满足后形成明确启用的同批DT，重新审查并记录镜像身份，不通过动态任意MMIO绕过。

部署仍按README执行：先读当次SD型号/容量/序列/UniqueId并取得覆盖授权，优先另一张卡，保留已验收Wi-Fi卡及scope回退；不沿用旧磁盘号。用户断电/装卡/上电，COM4确认可用后115200/8N1且DTR/RTS=false。不写eMMC/QSPI。本任务未连接板卡/串口、申请DMA或改变buffer，实时状态未知。
