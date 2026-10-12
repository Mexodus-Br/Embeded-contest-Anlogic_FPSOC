# GP BSP 构建检查点

2026-10-12，Asia/Taipei。**最终GP镜像已构建并通过主机检查；同一SD重新烧写、512MiB直接读回及FAT/EXT4检查通过。用户因板卡不在手边结束本次任务；冷启动/GP/IRQ/快照实板验收未执行。**

| 项目 | 实际结果 |
|---|---|
| 共享契约 | ca50bbf；PL交付cc16fe2，AXI3 GP0 A33/D32/ID12，0x80400000/4KiB，full地址译码后AXI-Lite，f2p_irq[0]，SPI82/INTID114，level-high |
| Linux软件 | 匹配原内核树W=1构建模块，验收程序-Wall/-Wextra/-Werror；11项软件安全门检查通过 |
| rootfs | 256MiB EXT4重新打包，模块、gp-accept和修正readonly-check文件内哈希一致，e2fsck通过 |
| PS实际端口 | alps配置后另执行xmlipgen，新增真实GP/IRQ/reset端口；直接实例生成raw PS，未依赖旧版无GP端口wrapper |
| 板级实现 | H16/LVCMOS33/100MHz，共同时钟及两级复位；真实PS＋GP完成布线/bitgen，无电机输出或DMA连接 |
| 路径时序 | 参考speed=2、10ns，完整重建route setup +3.211ns、hold +0.030ns，PS捕获路径纳入，STA coverage 99.99%；参考speed=2，不代表实物等级已确认 |
| HPF/FSBL/BOOT | HPF内bit字节匹配本次bitgen；隔离SDK平台生成FSBL，bootgen生成BOOT.bin；SDK/平台源码、map、符号、反汇编已保存 |
| DDR | HPF实际1.35V/32bit/1333MT/s，两片x16/4096Mbit；与已启动基线的soc_plat.c差异仅新增GP normal-access保护写，DDR初始化不变 |
| DTS | GP地址/IRQ格式检查通过，status=okay；内存1GiB/CMA128MiB沿用；GP模块仅安装，尚未板上加载 |
| SD部署/启动 | 完整512MiB写入和直接读回SHA256匹配，FAT/EXT4检查通过，根20ae01e9-02；未冷启动或打开COM4，原SD基线结果不替代新镜像结果 |
| GP/IRQ/快照 | 尚未板测。首轮仅NOP/SNAPSHOT、空闲四轴快照；事件完成不等同实际运动完成 |

## PS时钟警告定位与修复

首轮TD报告USR-6113，GEN_PL_GP0S未被时钟驱动。厂商示例final_timing.rpt的5900–5901行明确其路径为master_gp0_axi_aclk→GEN_PL_GP0S，这是启用master GP0的内部捕获时钟。单变量副本给slave ACLK接100MHz后警告仍在；derive_clocks查询返回no valid pll inst specified，没有成功推导时钟。这些失败证据保留。

根因是直接实例生成raw PS绕过了custom-wrapper的IP属性加载。修复保留厂商生成Tcl的四项GBE/IOPLL/P2F属性数值，只将实例路径映射到实际ps/DR1_PHY_PROCESSOR_SYSTEM_Inst，并纳入read_sdc。TD自动建立GEN_PL_GP0S 100MHz，真实PS→PL和PL→PS路径进入报告，无人工clock或false-path。PL任务只读复核认可此模型接入；随后正式完整重布线/bitgen通过，没有critical-warning，route setup +3.211ns、hold +0.030ns，STA coverage 99.99%。

首轮证据保留为../evidence/gp-hardware-build.log.initial等；最终为gp-hardware-build.log、gp-route.timing、gp-route.check、gp-clock-properties-fix.log、gp-ps-properties.tcl及gp-hardware-audit.json。厂商disabled HP端口位宽等继承warning仍在日志中，未视为已启用DMA。

## 最终镜像与匹配资料

完整交付包本地`bsp/artifacts/gp-release.tar.gz`，VM同名包SHA256 `b0730d3a1790a674034bc8e83816794887af22c07ec6ce0cfde9730a0912e7ba`；传输和23个发布文件均已本地验证。

VM任务目录：`/home/uisrc/embedded-bsp-gp`，构建机`uisrc@192.168.43.133`。原任务`/home/uisrc/embedded-bsp`及原发布包保留。新任务仅复用工具链、SDK工作副本与匹配内核树，不修改厂商原始档案。

`output/release/sdcard.img`为512MiB完整镜像：SHA256 `87a6d3af15a0921847634e0801e1dab1277492b2464d70bb02311bed3f9126c7`，SD根PARTUUID `20ae01e9-02`。GP节点okay，boot.scr绑定此UUID；后续重新打包仍以新manifest为准。此前GP disabled候选已被最终版替代，不用于部署。

HPF SHA256 `402615ba459d423cbbda80c42033ab5cdddc05fcc8dce74572fdc99c7d6350ff`，bitstream `e4de04369ea4496c718bb28236c53f2f085c5462a329fd3aa2d7ff9f30a42b42`，FSBL `c220f42e7c92f88f9d98e0a4a9b2fe4336df13f3236c4a67f7223f626f642f0b`。rootfs SHA256 `82b3d9e6dd40fdaff146a29db2f26afe6972d28ec68a7f3f79584c026faf4883`。镜像内readonly-check不再写死旧UUID，核对cmdline与实际SD根PARTUUID，支持传入manifest UUID做独立断言。

完整发布包包含release启动文件、debug配置/Module.symvers/System.map/vmlinux/展开DTS，以及support的生成头、补丁、GP源码/UAPI、FSBL源码和符号信息。内核.config SHA256保持`81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1`，Module.symvers保持`ccc69b7dbd1968066b6ce46d5e5a741f55045f7cc9663db722c3959c1cb548a3`；不能按版本字符串换模块。U-Boot复用前已检查新HPF的CPU/UART/MMC/容量关键值与原值一致，保持ENV_IS_NOWHERE，不写eMMC环境。

## 重建和后续部署步骤

Windows依次运行prepare_gp_hardware.py（已有目录拒绝覆盖）、regenerate_gp_ps.py、integrate_gp_hardware.py、build_gp_hardware.py、regenerate_gp_ps.py --export-hpf。硬件构建脚本拒绝任何ERROR/critical-warning，并要求GP和GEN_PL_GP0S 100MHz有效fanout及非负setup/hold。

经SCP/SFTP上传HPF和BSP输入。在VM设置TASK=$HOME/embedded-bsp-gp，PLATFORM_NAME=project_gp_control、GP_RESET_BOOT=1运行build_fsbl.sh。build_gp_software.sh和stage_gp_rootfs.sh基于原匹配内核/Buildroot输出。stage_gp_boot.sh在隔离DTS目录编译，默认disabled，boot-critical HPF值改变会拒绝复用U-Boot。make_sd_image.py只生成文件镜像；collect_gp_release.sh通过GP_STATUS=okay、BUNDLE_NAME=gp-release.tar.gz收集最终包。

已填写integration.review.json实际证据哈希并通过check_gp_contract.py --require-evidence；BSP人工审查标记REVIEWED_FOR_PROBE_BUILD后，以GP_STATUS=okay生成最终节点。source/DTS核对不替代实板IRQ路由验证。用户已确认读卡器中为此前授权覆盖的同一SD，USB序列号/容量匹配；用户重启VM后分区读取已恢复，旧基线PARTUUID匹配，已按明确授权开始写入，但约44MiB后进度停止；用户要求暂停，已终止流程并发送kill信号，dd处于D态，USB会话取消也可能等待，需实际断开故障读卡器才能完全解除内核I/O。USB序列号标识读卡器，不等于卡CID，换卡或目标不明仍需确认。

最终卡写入后对512MiB做直接读回哈希和文件系统检查。用户配合冷启动，COM4 115200/8N1、DTR/RTS=false先保存FSBL→U-Boot→Linux原始日志；核对FSBL reset标记、SD根新PARTUUID、1GiB/128MiB CMA，然后加载bsp_gp并运行gp-accept，保存中断计数及dmesg。身份不符或总线错误立即停查，不猜地址。

DDR实物供电/颗粒/训练、实物speed grade、长期DDR/CMA/存储稳定性、动态运动源快照、运动DMA及实体电机均未验证；HMI暂缓。

## 历史暂停检查点（已恢复并重写成功）

用户2026-10-12明确要求无法完成写入即暂停。完整512MiB已提交到主机缓存，落盘未完成，直接读回/分区fsck未执行；当前SD内容不完整，不能用于启动，恢复后必须重新烧写并全量校验。已停止烧写shell，向dd发送TERM/KILL并尝试仅取消目标USB会话；D态内核等待可能仍需物理拔下读卡器解除。临时USB power/control=on及Realtek ss_en=0未解决故障，未解绑其他设备。

镜像、源码和匹配资料已保存；本批未上板、未验收GP/IRQ/快照，未提交Git，恢复完成后再提交。暂停证据见../evidence/gp-sd-write-paused.log和gp-sd-transport-paused.log。

## 2026-10-12 SD重新部署通过

用户重新插接后明确授权格式化并重新烧写。VM中旧写入进程已退出；同一USB读卡器20121112761000000及61132800扇区匹配，系统盘sda排除。write_sd.sh改用bs=1M/oflag=direct，进度反映已完成块写入，保留conv=fsync；完整镜像重建MBR/FAT32/EXT4，无需另行mkfs。512MiB写入及完整direct读回成功，SHA256均为87a6d3af15a0921847634e0801e1dab1277492b2464d70bb02311bed3f9126c7；FAT/EXT4只读检查通过、脚本退出0。SD根PARTUUID为20ae01e9-02，两分区最终未挂载。

成功原始证据为../evidence/gp-sd-rewrite.log、gp-sd-rewrite-transport.log，部署元数据更新至gp-release-manifest.json；不可变交付包及其哈希未改变。完整512MiB写入93.3569秒、直接读回87.4153秒。本次未见新的USB复位或块I/O错误，但不视为长期可靠性验收。

用户随后明确本次任务结束，板卡不在手边。本批交付范围结束于镜像构建与SD主机部署通过；未打开COM4，完整冷启动、GP寄存器/命令、GIC IRQ触发/清除/恢复以及时间戳/四轴快照实板验收均未执行。eMMC保留。首轮板上步骤和受限验收脚本已准备，留待后续任务执行；本批按此实际范围提交Git。
