# 实体SD部署记录

2026-10-12 GP批次重新部署成功。用户重新插接同一SD并明确授权格式化/烧写；核对读卡器序列号20121112761000000、61132800扇区及系统盘排除后，使用1MiB direct I/O整盘写入512MiB，重建镜像内MBR、64MiB FAT32和256MiB EXT4。完整直接读回SHA256为`87a6d3af15a0921847634e0801e1dab1277492b2464d70bb02311bed3f9126c7`，与镜像一致；fsck.vfat -n、e2fsck -fn均通过，脚本退出0，两分区最终未挂载。根PARTUUID为`20ae01e9-02`，启动分区为`20ae01e9-01`；剩余空间未分配。eMMC未操作。原始证据见evidence/gp-sd-rewrite.log及gp-sd-rewrite-transport.log。待用户装卡、确认板卡状态后采集完整冷启动并验收GP/IRQ/快照。

此前缓冲写入约44MiB后USB停止推进，按用户要求暂停；断开读卡器后旧进程退出。本次从头重写并全量校验，替代不完整卡内容。历史失败证据保留，不能据一次成功认定长期USB/存储稳定性。见[gp/BUILD_STATUS.md](gp/BUILD_STATUS.md)。

用户确认本次任务结束，板卡不在手边，冷启动及GP/IRQ/快照实板验收顺延。未打开COM4；当前两分区已卸载，可取卡。本次写入93.3569秒、完整直接读回87.4153秒。

日期：2026-10-11，Asia/Taipei。用户授权“sd已插入，进行格式化和烧写”，并指定参考虚拟机sdcard_image的三份shell脚本。状态：**实体卡烧写和主机直接读回验证成功；未实板启动**。

## 目标识别

- Ubuntu构建虚拟机中唯一USB可移除磁盘 `/dev/sdb`，读卡器型号 `SD/MMC/MS PRO`、USB序列号 `20121112761000000`。
- 固定设备链接 `/dev/disk/by-id/usb-Generic-_SD_MMC_MS_PRO_20121112761000000-0:0`。
- 容量61132800个512B扇区，共31299993600字节，约29.2GiB；USB序列号标识读卡器，不是SD颗粒/CID。
- 原有单个vfat分区挂载在 `/media/uisrc/0403-0201`。写入前卸载；根系统盘为 `/dev/sda1`，排除其父盘 `/dev/sda`。未操作其他磁盘、eMMC或QSPI。

## 参考与实际执行

读取了 `/home/uisrc/sdcard_image/common.sh`、`make_parted.sh`、`deploy_image.sh`。原流程创建100MiB FAT32和剩余EXT4，再复制boot文件与解包rootfs；本次不直接运行其交互脚本，以免改变已经审查的镜像分区布局/PARTUUID。

参考脚本SHA256：

- common.sh：`d9c79e8aaebf4b61cb7b81e53ea9dd1aab35fd09fea46e7281c380d8a32ff525`
- make_parted.sh：`16f7113a2531da19e0553aae2429490d58433bdb9a2add5cac2304f197ae01e7`
- deploy_image.sh：`3c91c5015403a35115fd17a795c76aaf7a34bcbde9e638b0bbc9a2b1f93b0a6c`

实际执行项目 `scripts/write_sd.sh`：核对USB序列号、容量、可移除属性、系统盘排除及源镜像SHA256，再整盘写入536870912字节。完整镜像同时重建MBR及两个已格式化文件系统；无需另行mkfs。写入使用fsync，随后刷新块缓存，以direct I/O完整读回前512MiB并比较SHA256。

## 实际结果

- 写入536870912字节成功，耗时570.095秒。
- 直接读回536870912字节，耗时75.7691秒。
- 镜像与读回SHA256均为 `289f90f22cf5bbaa387004a837b192d8b94ba366875f9bb8fe475a1043636049`。
- MBR签名 `0xd0e414b9`。
- 第1分区：起始2048扇区，131072扇区/64MiB，FAT32，bootable，LABEL=BSPBOOT，PARTUUID=d0e414b9-01。
- 第2分区：起始133120扇区，524288扇区/256MiB，EXT4，LABEL=bsp-root，PARTUUID=d0e414b9-02。
- fsck.vfat -n与e2fsck -fn均成功；后者完成5项检查。两分区最终未挂载，已sync。卡剩余空间保持未分配，不扩大首批根分区。

USB读卡器在缓存落盘期间反复复位，导致写入偏慢；完整证据见 `evidence/sd-transport.log`。没有据此认定板上SD控制器或DDR故障，也不能据最终哈希一致保证长期存储可靠性。写入/读回/分区/文件系统结果见 `evidence/sd-write.log`。

可以取出卡，在板卡断电时核对SD拨码011（ON/OFF/OFF）并插卡。待用户明确板卡供电/状态与串口可用后，再采集FSBL→U-Boot→Linux完整启动和只读root/DDR/CMA核对。本次没有打开COM4、上电/重启板卡或执行DMA/运动测试；1.35V供电/颗粒/训练、板上存储与运动时序验证项仍保留。

后续：用户确认已从SD上电后完成COM4只读核对，SD根/内存/CMA/内核配置证据见[BOARD_VALIDATION.md](BOARD_VALIDATION.md)。上述未实板启动状态为烧写完成时的历史记录。
