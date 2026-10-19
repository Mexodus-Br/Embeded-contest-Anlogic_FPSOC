# Wi-Fi HTTP 当前实测状态 — 2026-10-19 Asia/Taipei

**未完成LAN验收。当前停在Wi-Fi扫描/目标AP匹配；不是待烧录，也不是联网通过。**

| 层 | 当前结果 | 证据/边界 |
|---|---|---|
| A 启动身份/USB | 当前首版SD通过 | 6.1.111-rt42-bsp-wifi1，SD根70d791a8-02，DWC2/Hub、a69c:8d80；原scope启动链/PL |
| B Wi-Fi | 部分通过 | chip_id7/U02固件下载、a69c:8d81、wlan0、主动扫描通过；STA持续SCANNING，未关联/未DHCP |
| C 双向ping | 未执行 | 无板卡无线IPv4；电脑WLAN最近172.20.10.4/28，未沿用有线结果 |
| D LAN HTTP | 未执行 | 用户报告HTTP认证已保存；板端实查root:0600。未启动服务/未从LAN获取200 |
| E LAN下载/拒绝测试 | 未执行 | VM loopback四项安全/二进制测试通过，仅离线证据；真实网络/启动快照尚未生成 |
| F 10分钟/重连/冷启动 | 未执行验收 | 做过一次STA停止重启读取配置，仍SCANNING；不计作联网恢复通过；未开启自启动 |

## 实板修复与当前状态

最初loader在非Android配置请求平面固件路径，文件仅在D80子目录导致失败。增加同套11文件的相对符号链接后成功，未改固件文件名/内容、未用旧ko。STA最初依赖镜像未提供的stat命令，改为已存在Python3的lstat权限检查；0644拒绝/0600接受及生命周期主机回归4项通过。两项修复已写当前SD，原PARTUUID不变。物理标签仍未确认，不能把USB/固件证据写成标签已核实。

用户两次在本地配置后，已查两份配置root:0600；不读取/回显密码。第一次STA启动和重新读取配置后均为SCANNING。最后主动扫描19个网络，已处理iw非ASCII转义，配置目标SSID仍不可见；扫描正常返回0。配置country=CN，驱动self-managed域00，此差异尚待进一步确认。尚无认证失败证据，不能归因为密码错误。

板卡保持上电；本任务COM4连接已关闭（115200/8N1，无流控，DTR/RTS=false），交给用户核对目标AP/配置。STA worker/wpa_supplicant后台扫描；HTTP未运行、未开启自动联网/HTTP。没有加载或运行运动程序，没有REBASE/ENABLE/START，未写eMMC/QSPI，未自动复位。

## 镜像身份

- 已部署首版：`bsp/artifacts/wifi-http-20261019/sdcard.img`，根70d791a8-02；完整写入/读回通过。板端已补两项修复，不能与原镜像文件内容混同。
- r2未部署：根c7965caa-02，补固件别名。
- 最新r3未部署：`bsp/artifacts/wifi-http-20261019-r3/sdcard.img`，536870912B，根82e6e1bc-02，SHA256 db50bdcf1908977fc29fd09bdc9e75d28e79475799a8a2fb0f703359c08cc734。独立VM `/home/uisrc/embedded-bsp-wifi-http-20261019-r3`。补两项修复，最终EXT4源码/账号/无凭据/无假快照、11项固件及别名、旧内核/模块/启动链、分区逐字节及只读fsck通过；Windows传输校验通过。
- 旧Wi-Fi根4fa65f13-02及scope根8aea5f8d-02保持。部署新镜像仍需当次SD身份核对；不能沿用旧磁盘号。

最终关键移交以r3的sdcard.img和manifest.json为入口；镜像无个人SSID/PSK、HTTP认证或自启动批准。程序源见同目录及上级driver.sh/sta.sh；构建/操作/回退见README。日志和诊断文件不计算哈希。

必要原始记录在本地bsp/evidence/wifi-http-{cold,identity,driver,connect,sta-fix,network,radio,reconnect}-20261019-*.log；保留首次失败，部分底层原始输出含设备标识，发布时使用脱敏摘录。当前关键证据为radio-03、connect-04、reconnect-01及SD写入记录。离线身份/主机回归在bsp/wifi/evidence/http-20261019-r3-verification.json及http-r3-host-tests.log。
