# Wi-Fi HTTP 当前实测状态 — 2026-10-19 Asia/Taipei

**实板核心目标已通过：Wi-Fi/DHCP、电脑无线ping、认证HTTP及两文件下载；受控重连与用户冷启动复测通过。完整A–F仍有C的板卡→电脑ICMP方向未通过，不能写成全部通过。**

| 层 | 当前结果 | 证据/边界 |
|---|---|---|
| A 启动身份/USB | 当前首版SD通过 | 6.1.111-rt42-bsp-wifi1，SD根70d791a8-02，DWC2/Hub、a69c:8d80；原scope启动链/PL |
| B Wi-Fi | 关联/DHCP通过 | chip_id7/U02固件下载、a69c:8d81、wlan0通过；修正SSID漏输@后WPA2-PSK COMPLETED，DHCP 192.168.2.245/24，网关192.168.2.1 |
| C 双向ping | 部分通过 | 板卡wlan0→网关4/4；电脑WLAN 192.168.2.244→板卡10/10；板卡→电脑0/4，Public防火墙无Echo入站放行，未更改策略 |
| D LAN HTTP | 通过（含重连/冷启动） | 板端HTTP UID/GID498，电脑绑定WLAN源获取200；用户浏览器认证/首页通过；未授权401 |
| E LAN下载/拒绝测试 | 通过（含重连/冷启动） | 262144B二进制与板端同一参考序列逐字节一致；BOARD_LOCAL_COLLECTION快照重复下载一致；404/401/403/405预检通过；浏览器两文件下载通过 |
| F 10分钟/重连/冷启动 | 完成并记录丢包 | 板端604.06秒/61次关联及网关失败0，USB/固件异常0；电脑601.234秒/117轮HTTP下载失败0；独立ping 601发600收、丢1包约0.17%，最大532ms；受控重连与用户冷启动后LAN复测通过 |

## 实板修复与当前状态

最初loader在非Android配置请求平面固件路径，文件仅在D80子目录导致失败。增加同套11文件的相对符号链接后成功，未改固件文件名/内容、未用旧ko。STA最初依赖镜像未提供的stat命令，改为已存在Python3的lstat权限检查；0644拒绝/0600接受及生命周期主机回归4项通过。两项修复已写当前SD，原PARTUUID不变。物理标签仍未确认，不能把USB/固件证据写成标签已核实。

早期目标SSID不可见/SCANNING原始失败保留。用户核对发现漏输@；重新本地配置后认证及DHCP成功。两份配置root:0600，不读取/回显密钥或HTTP口令。电脑现已连接同一目标AP，WLAN地址192.168.2.244/24；Windows WLAN API只读确认目标频道40，板卡也能扫描5GHz。配置country=CN，驱动self-managed域00，此差异仍列已知限制。首个命令行预检在missing_file断言退出，旧脚本未记录实际响应码，不能推断具体原因；改为明确预检记录后重跑通过。

板卡保持上电；本任务COM4已关闭释放（115200/8N1，无流控，DTR/RTS=false）。冷启动后STA worker PID195、wpa_supplicant PID203、udhcpc PID763、HTTP PID257/UID498在运行；网络及HTTP本地自启动批准已启用。新版driver脚本已更新到当前SD并依据已验证USB/固件/wlan0保存本地D80批准。没有加载或运行运动程序，没有REBASE/ENABLE/START，未写eMMC/QSPI，未自动复位。

## 镜像身份

- 已部署首版：`bsp/artifacts/wifi-http-20261019/sdcard.img`，根70d791a8-02；完整写入/读回通过。板端已补两项修复，不能与原镜像文件内容混同。
- r2未部署：根c7965caa-02，补固件别名。
- 最新r3未部署：`bsp/artifacts/wifi-http-20261019-r3/sdcard.img`，536870912B，根82e6e1bc-02，SHA256 db50bdcf1908977fc29fd09bdc9e75d28e79475799a8a2fb0f703359c08cc734。独立VM `/home/uisrc/embedded-bsp-wifi-http-20261019-r3`。补两项修复，最终EXT4源码/账号/无凭据/无假快照、11项固件及别名、旧内核/模块/启动链、分区逐字节及只读fsck通过；Windows传输校验通过。
- 旧Wi-Fi根4fa65f13-02及scope根8aea5f8d-02保持。部署新镜像仍需当次SD身份核对；不能沿用旧磁盘号。

最终关键移交以r3的sdcard.img和manifest.json为入口；镜像无个人SSID/PSK、HTTP认证或自启动批准。程序源见同目录及上级driver.sh/sta.sh；构建/操作/回退见README。日志和诊断文件不计算哈希。

必要原始记录在本地bsp/evidence/wifi-http-{cold,identity,driver,connect,sta-fix,network,radio,reconnect}-20261019-*.log；保留首次失败，部分底层原始输出含设备标识，发布时使用脱敏摘录。最终结构化记录为bsp/evidence/wifi-http-acceptance-20261019.json。关键原始证据为stability-01、pc-continuous-01、reconnect-04-sanitized、cold-03-sanitized、post-boot-01、final-state-01及三个LAN验收目录；发布副本移除MAC/指针，原始本地记录保留。离线身份/主机回归在bsp/wifi/evidence/http-20261019-r3-verification.json及http-r3-host-tests.log。

板端墙钟尚未校时，HTTP Date及快照collected_utc为1970，不作为真实验收时间；以电脑证据时间和板端uptime关联。该版未建设NTP或完整时间服务。日志/快照不计算哈希。

## 重连与冷启动最终证据

受控wifi-sta reconnect后约3秒内重新认证，HTTP PID前后均2315，未重启服务；电脑绑定WLAN源ping4/4，认证首页/两文件下载与安全预检再次通过。随后同步SD，由用户断电等待后重新上电；只读核验未执行手动网络或HTTP start。冷启动SD根仍70d791a8-02，runtime USB a69c:8d81，实际频率5200MHz、信号-37dBm。自动生成快照uptime12.27秒，UID/GID498服务已运行，网关ping4/4；电脑ping4/4、认证下载和用户浏览器刷新/下载再次通过。

首次快照788B和冷启动快照786B分别与板端稳定原文件逐字节比较通过，未哈希。每次二进制262144B与板端已验证的同一参考序列逐字节一致。认证文件及个人网络配置仅在板端，未进入Git/镜像。

HTTP初次自启动最多后台重试约180秒；路由器首次离线超过该窗口时，Wi-Fi连接后需手动wifi-http start。已有HTTP进程在STA受控重连后恢复已验证，实际DHCP换地址情形未专项实测。该版只适用于已测WPA2-PSK/CCMP，WPA3-only等未验收。
