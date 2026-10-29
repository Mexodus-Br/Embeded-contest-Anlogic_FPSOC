# 全功能镜像SD部署记录

2026-10-29，Asia/Taipei。镜像交付完成后用户追加“执行写卡”，并明确确认覆盖当前磁盘1的SD卡。本次授权取代此前本轮不写卡的限制，仅授权写卡，不表示上电或运动授权。

## 当前结果

**SD_DEPLOYMENT_VERIFIED_NOT_BOARD_BOOT_TESTED**。脚本退出0，原始磁盘/卷句柄已关闭并刷新写缓存。

- 目标：Windows USB磁盘1，Generic- SD/MMC/MS PRO，31,299,993,600字节；非系统/启动盘、可写。无卡独立序列号，UniqueId为`USBSTOR\DISK&VEN_RSUER&PROD_RTSUERLUN0&REV_1.00\0000:LAPTOP-JS7E5LFJ`。容量与上次记录不同，用户已按本次枚举信息单独确认。
- 原MBR根身份：f330c1cf-02。写前首512MiB完整私有备份，覆盖MBR和全部有效分区；第二次无缓存读取逐字节比对通过。备份位于`artifacts/private-rollback/live-f330c1cf-before-full-function-r1.img`，ACL仅当前用户、SYSTEM、Administrators；不上传、不入Git、不发布其中可能存在的凭据，未哈希备份或日志。
- 新镜像：full-function-20261029-r1；构建源码67c276b9757bcbc91fdedcf948754679d4b0cf36；镜像路径`artifacts/release-r1/sdcard.img`；536870912字节。PL最终WNS +0.312ns，hold +0.020ns，100MHz、threads=16。
- 写入24.485秒；全量无缓存读回18.204秒。
- 源镜像及实际SD读回SHA256均为`3340b2dd9a58d99ba2bc5004b498ca8705cabb451f69393e401ec0bee7d5edc5`。
- MBR、两分区起点/长度、根PARTUUID **3201cd3a-02**、FAT32和EXT4签名通过。Windows未额外运行fsck；源镜像已通过只读fsck，实际卡完整字节校验一致。
- 结束：2026-10-29T08:43:33+0800。原始记录`artifacts/sd-deploy-20261029-01.log`及JSON，未对日志计算哈希。

## 后续边界

用户可通过Windows安全弹出SD，板卡断电后插卡。未打开串口、未上电或重启板卡、未执行HOME/使能/运动，未操作eMMC/QSPI。后续隔离与实板验收按OPERATIONS.md，并需当次授权及用户负责断电、接线和上电。

发布manifest中的sd_written=false描述离线构建时状态，保持原始构建清单不变；后续实际写卡状态以本记录为准，不把写卡成功记为实板功能验收通过。
