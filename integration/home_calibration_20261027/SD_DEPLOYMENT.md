# 本次SD替换记录

2026-10-27，Asia/Taipei。用户在确认裸scope三轴基础运动成功后，明确要求将当前SD替换成最新系统镜像；撤销此前“暂不写卡”的限制，仅授权本次卡覆盖，不表示运动授权。

## 目标与结果

- 当次目标：USB Disk1，Generic- SD/MMC/MS PRO，31,708,938,240字节；非系统/启动盘、可写、online。读卡器UniqueId与当次确认值匹配；无独立卡序列号。写前重新核对旧启动身份70d791a8-02、MBR及两分区范围。
- 原卡：2026-10-19 Wi-Fi/HTTP，历史持久修复与本地配置需随实际rootfs保存。写前将首512MiB完整保存，覆盖MBR及所有有效分区；第二次直接读取原卡逐字节比较通过。未拿旧分发img代替实卡备份。
- 私有备份：`artifacts/private-rollback/wifi-http-live-70d791a8-before-home-r2.img`。仅当前用户、SYSTEM、Administrators可访问，不入Git、不上传VM、不发布凭据；备份按字节核验，未哈希日志或中间文件。
- 新版本：home-calibration-20261027-r2，编译提交6bec51644cca5a8699a318b3ab2fe13650ddfc86；新根PARTUUID=a61e22d5-02。
- 镜像：`artifacts/release-r2/sdcard.img`，536870912字节。写入29.391s；完整无缓存读回17.984s。
- 源及实际SD读回SHA256均为：`335a509643f57fe6753c5f596fc7e7f0d84cff7b9c8febc584fcc6779e85f69d`。
- MBR签名、两分区起点/长度、根PARTUUID、FAT/EXT4签名通过。Windows未运行fsck；最终源镜像已只读fsck且实际卡全字节一致。
- 最终状态：**SD_DEPLOYMENT_VERIFIED_NOT_BOARD_BOOT_TESTED**，结束时间2026-10-27T19:37:36+0800。
- 原始记录：`artifacts/sd-deploy-20261027-01.log`及其JSON。不哈希日志。

## 后续边界

所有原始磁盘/卷句柄已关闭、写缓存已刷新；用户安全弹出SD，板卡断电后插卡。必须先隔离驱动STEP并核对串口实际端口/占用，配合接线和上电，再依次按[ACCEPTANCE.md](ACCEPTANCE.md)执行。尚未打开串口、启动板卡、执行HOME或普通运动，未操作eMMC/QSPI。

重点：静止启动与真实后端身份；实际安全停止/心跳/485；精确脉冲和DIR/EN时序；隔离HOME异常路径；经用户确认后的近限位HOME、参考计数及编码器采集；HMI与日志。普通XYZ/方向/示教/任务运动仍关闭，HOME完成不使真实XYZ有效。旧scope已通过不继承为这些项目通过。
