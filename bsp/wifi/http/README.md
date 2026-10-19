# Wi-Fi + 最小只读 HTTP，2026-10-19

本轮用户授权增加静态诊断首页及认证下载，覆盖上一轮“不集成Web”的对应限制。仍无运动HMI、上传、shell、API动作或日志管理系统，不集成SAF2/R5S2、RS485/HP1或新PL。

当前实板进展以 [BUILD_STATUS.md](BUILD_STATUS.md) 顶部为准：修正漏输@的SSID后，Wi-Fi/DHCP、电脑无线ping、HTTP/下载、10分钟观察、受控重连与用户冷启动复测已通过；板卡→电脑ICMP受阻仍未通过。下方失败经过保留作追溯。

## 实现与本地配置

旧Buildroot BusyBox的 `CONFIG_HTTPD` 未启用。复用已安装Python3标准库，不增加内核配置/大型框架/在线安装依赖。固定IPv4端口8080，监听socket设置 `SO_BINDTODEVICE` 为已配置无线接口，再清空附加组并降权至 `wifihttp` UID/GID498。DHCP地址变化后监听仍绑定无线设备，不需固定旧地址。只允许GET，单进程/请求5秒超时、HTTP/1.0关闭连接，不提供目录列表、CGI或命令入口。

板端先完成Wi-Fi配置及手动接入：`wifi-configure`、`wifi-sta start`、`wifi-sta status`。HTTP独立认证用本地TTY运行 `wifi-http-auth`，设置非root用户名与独立12..128字符口令，隐藏输入。认证文件 `/etc/wifi-http/auth.json` 为root:0600，目录0700，存PBKDF2-SHA256随机盐校验值；分发镜像不含认证文件/自启动批准，不复用默认root口令。所有HTTP路径（含首页和测试文件）使用Basic认证；按本轮授权不要求HTTPS。口令只在本地配置和客户端内存使用，不放命令参数/URL/Git/日志。

`wifi-http start|stop|restart|status|autostart-on|autostart-off` 管理服务。status报告进程UID/GID、无线地址和 `http://<无线IPv4>:8080/`。start在服务接收请求前，以本地root脚本 `wifi-http-export` 生成一次稳定脱敏快照；HTTP请求本身不执行任何采集命令。路由器未连接或采集失败时保留旧稳定文件、启动失败退出，不发布半成品。`S46wifi-http` 的自动启动在后台有限重试，不阻塞系统启动/串口；先验证手动网络和HTTP，再显式启用网络及HTTP的自启动。

页面 `/srv/wifi-http/public/index.html` 和专用导出目录 `/srv/wifi-http/exports` 都由root维护、服务仅可读。固定GET白名单：`/`、`/index.html`、`/files/test.bin`、`/files/network-snapshot.txt`。其它文件返回404，编码路径/穿越返回403，上传/删除等方法405，缺少认证401。通过dirfd和O_NOFOLLOW读取，拒绝符号链接、硬链接、多链接文件、FIFO和大于8MiB的文件，不公开根目录、凭据或整个/var/log。

`test.bin` 为262144字节，内容是 `bytes(range(256))*1024`；板端校验原文件与该序列相同，电脑再逐字节比较下载文件与相同参考序列，确认长度和内容。真实 `network-snapshot.txt` 只在板卡联网后生成，包含版本/SD根PARTUUID/uptime、无线状态/IPv4/掩码/路由及USB ID，不含SSID、PSK、HTTP认证、MAC、串口原始日志或任意启动参数。未将VM快照冒充板卡快照放入镜像。快照文件和日志均不计算哈希。

## 构建、部署历史与镜像身份

独立VM `/home/uisrc/embedded-bsp-wifi-http-20261019`，前提为上一版Wi-Fi任务及其Buildroot host工具仍在。将本目录、`bsp/wifi/driver.sh`、`bsp/wifi/sta.sh`、`bsp/wifi/package.py`、`bsp/scripts/make_sd_image.py` 传入对应TASK路径；`mkdir -p "$TASK/build" "$TASK/logs"`，执行 `python3 "$TASK/bsp/wifi/http/build_http.py" "$TASK"`，再 `python3 "$TASK/bsp/wifi/http/verify_http.py" "$TASK"`。rootfs从旧Wi-Fi target复制到独立目录，内核、模块、BOOT/HPF/FSBL/PL/DTB逐字节保留。最终ext4实际内容由debugfs取出与直接源码比较，验证账号及凭据缺席；不是只检查暂存目录。

2026-10-19首次候选：本机 `bsp/artifacts/wifi-http-20261019/sdcard.img`，根 `70d791a8-02`，SHA256 `03a1ad579677026833863d3335e8d76d21074acb7c1dc577eb2594ba16e5bb65`。已按本次新SD授权核对Windows目标身份，并写入/完整无缓存读回536870912B通过。写入25.703秒、读回18.281秒；证据 `bsp/evidence/wifi-http-sd-20261019-01.log(.json)`。旧Wi-Fi候选根4fa65f13-02及scope回退根8aea5f8d-02保留。

实板首轮：FSBL→U-Boot→Linux、SD根70d791a8-02、1GiB/CMA128MiB和Host/Hub通过；实际Wi-Fi boot ID a69c:8d80，chip_id=7。首次固件加载因非Android loader使用平面路径失败，原记录保留。为同一套U02文件加准确相对路径别名后，loader下载成功，runtime ID a69c:8d81、wlan0出现。runtime驱动仍从aic8800D80子目录读取配置；没有改固件名称/内容。`driver.sh`及本轮构建源已补入别名规则。当前运行SD有此板端持久修复；首次候选文件自身尚不含这项后续修复，不能把两者身份混为一谈。修正版已另存 `bsp/artifacts/wifi-http-20261019-r2/sdcard.img`，根 `c7965caa-02`，SHA256 `d429f239584c35a8a5a9c185af0a5f864f301750d343a6cd3c9e27f256cc1d81`；最终ext4/旧内核及模块/HTTP源码内容验证与Windows镜像传输校验通过，尚未写卡或作为本批冷启动身份验收。

早期过程记录（后续通过结果见本页末尾及BUILD_STATUS）：串口采集工具首名serial.py曾与pyserial导入冲突，未打开COM4即失败；已改名uart.py。第一段等待上电接收超时且0字节，第二段成功采集冷启动到login后仅终止本任务接收进程释放端口，原始记录保留。COM4工具 `uart.py` 不哈希日志、不切换DTR/RTS；冷启动捕获先接收再由用户上电。旧capture_serial.py/serial_exec.py会哈希日志，本轮未调用。只停止本任务接收进程，不抢占用户终端；本次凭据配置后实查：Wi-Fi配置root:0600；HTTP认证文件尚未生成。最小BusyBox缺stat，原STA权限检查因此失败，已改用已有Python3的lstat检查，板端持久修复并重新运行。STA进程启动后仍为SCANNING，主动扫描成功看到15个SSID但不含配置目标；未取得IPv4。安装country配置CN，驱动self-managed域仍00，此差异尚未完成联网后资格验证。当时COM4关闭交还用户核对并补认证，未抢占终端；后续用户补完整SSID并完成实板通过项，见最终记录。离线4项HTTP测试本身只是在VM loopback执行。


2026-10-19 r3另存 `bsp/artifacts/wifi-http-20261019-r3/sdcard.img`，根 `82e6e1bc-02`，SHA256 `db50bdcf1908977fc29fd09bdc9e75d28e79475799a8a2fb0f703359c08cc734`。在r2基础上补STA的Python权限检查；独立VM目录同名r3。最终ext4直接源码、11项固件内容/别名、BOOT/内核/模块、分区内容与fsck检查通过，Windows最终镜像传输校验通过。STA主机4项回归包含0600接受/0644拒绝；不代表无线联网通过。此镜像未写卡，不含凭据和自启动批准；首版SD已有两项持久修复但其PARTUUID仍70d791a8-02。

## 电脑验收入口

浏览器访问 `http://<无线IPv4>:8080/`，在浏览器认证框输入本地HTTP账户，检查版本与链接并下载两文件。命令行可用 `curl.exe --user <用户名> --noproxy "*" --fail --dump-header headers.txt --output test.bin http://<无线IPv4>:8080/files/test.bin`；curl交互输入口令，不在参数中放密码。不存在文件应404，未授权应401，越界/写操作必须拒绝。

完整重复验收用 `python bsp/wifi/http/lan_accept.py --board <板卡无线IPv4> --source <电脑无线IPv4> --user <用户名> --seconds 600 --output <本地证据目录>`，客户端交互隐藏输入口令；可使用用户指定且位于Git工作区以外、限制访问权限的本地凭据文件替代。它强制使用电脑的指定源地址，忽略系统代理，检查固定文件逐字节和快照稳定重下载、认证/越界/非法方法，并保存ping及每轮结果，不哈希日志快照。板卡到网关/电脑的无线绑定ping需另由串口执行，浏览器结果也需单独记录，不能以localhost代替LAN。

最后执行受控 `wifi-sta reconnect` 后复测，再由用户断电冷启动并复测三项。遇电脑防火墙/AP隔离只记录失败和证据，不擅改。回退用原保留SD或经当次目标核对/授权写旧镜像；不写eMMC/QSPI，不运行REBASE/ENABLE/START和运动验收。

板端尚未校时：HTTP Date与快照collected_utc可能为1970，应使用电脑验收时间及uptime关联，不能将其当作实际墙钟。受控重连后需本地运行wifi-http-export刷新诊断快照；HTTP GET自身不会采集。

## 2026-10-19最终可用入口与边界

当前已测板卡地址 **http://192.168.2.245:8080/**，电脑WLAN192.168.2.244/24，网关192.168.2.1，实际板卡无线频率5200MHz。HTTP用户名uisrc，口令由用户板端本地配置；DHCP地址可变，以wifi-sta status或wifi-http status查询为准。下载路径为/files/test.bin与/files/network-snapshot.txt，均要求认证。

电脑601.234秒/117轮HTTP及下载无失败；独立连续ping601发600收、丢1包约0.17%，最大532ms。板端604.06秒内61次关联/网关探测无失败、无USB/固件异常。重连保持同一HTTP进程，冷启动后自动认证/DHCP、UID498服务和新快照（uptime12.27秒）均已验证，电脑认证下载及浏览器再次通过。原始逐字节二进制/快照比较及各响应码见bsp/evidence/wifi-http-acceptance-20261019.json和对应LAN目录；不哈希日志/快照。

现存限制：板卡→电脑ping0/4，电脑Public入站Echo未见允许规则；未修改防火墙或路由器。配置CN但vendor自管理地区域仍00，地区/信道资格未完整验证。HTTP首次自启动在后台重试约180秒，路由器长时间离线后需手动wifi-http start；已有服务STA重连恢复已测，实际DHCP换地址未专项测试。板卡墙钟未校时。

当前板卡为已部署首版70d791a8-02加板端持久修复及本地凭据/批准，保持上电；COM4已关闭释放，网络和HTTP后台运行，运动模块未加载。**r3（82e6e1bc-02）分发镜像仅离线验证，未将当前板测冒充r3烧录/冷启动通过。** 重新写r3会清除本地凭据，需重新配置、批准并验收；原Wi-Fi及scope镜像保持回退。
