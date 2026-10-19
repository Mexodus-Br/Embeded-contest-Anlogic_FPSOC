> 2026-10-19当前范围更新：用户授权最小静态HTTP诊断首页及只读认证下载，覆盖下方2026-10-18“不集成Web”的对应限制；不开发运动HMI。首版SD+两项持久修复已实板通过Wi-Fi、电脑ping、HTTP/下载、10分钟观察、重连与用户冷启动复测；板卡→电脑ICMP受阻仍单列未通过。r3新候选仅离线验证，未写卡。当前说明见 [http/README.md](http/README.md)，下方保留上一轮候选记录。

# Wi-Fi STA 专项（scope 硬件基线）

本轮日期 2026-10-18，Asia/Taipei。目标是路由器 STA 与局域网双向可达；本次板卡、SD 不可用，工作止于 SD 烧录前。**候选构建/脚本测试不代表 USB 枚举、Wi-Fi 联网或实板验收通过。** 当前状态及产物身份见 [BUILD_STATUS.md](BUILD_STATUS.md)。不集成 Web/AP/4G/安全/HOME/RS485/HP1，不自动加载运动客户端或运行任何运动程序，不操作 eMMC/QSPI。

## 已知输入与硬件链路

- 用户确认：SSID 不固定，预共享密钥；COM4 空闲，但板卡不在手边。实物模块标签、天线、板修订、当前板上镜像/进程和 USB ID 未确认。配置器当前支持 WPA2-Personal/RSN/CCMP；WPA3-only、WPA1/TKIP、企业认证不在已实现范围，不能将泛称 PSK 当作这些模式的验证。
- `HARDWARE.md §13`、厂商 `05-4_无线通信方案/WIFI.zip` 是来源。ZIP 中的老 ko/o/cmd 不提取、不加载。版本字段 `RWNX_VERS_NUM=6.4.3.0`；源码含多芯片 ID，供应固件目录仅 `aic8800D80`（主要为U02文件），只能作为本次 D80 候选，不能据此认定实物是 D80。
- 硬件手册 §13（印刷17页）说明 USB3320、Host/Slave 跳线和四口 Hub。其正文写 MIO29~39，管脚表和原理图还包括 **MIO28 DATA4**。PHY reset=MIO46，CLK=MIO36，DIR29/STP30/NXT31/DATA0..3=32..35/DATA5..7=37..39。
- 底板原理图 `MLK_F3P_DR1_250526.pdf` p8：U7 USB3320、X3 24MHz、VDDIO=1.8V；U9 CH442Q/CH9442Q 的 J18 1-2=高电平选择 S2 Host Hub，2-3=低电平选择 S1 Type-C。图示默认上拉，但必须在断电实物确认，不能从文档推定当前跳帽。U10 CH217K 的 EN 经 R76 下拉、VIN=5V、输出 ULPI_VBUS；不把未测的限流/使能和 VBUS 当作正常。
- 同原理图 p9：U11 FE1.1S Hub 上游接 HOST_D±；port1 通过 R83/R84 接 U12（图纸标 `SKI.WB800D80U.2`），U12 8脚=VCC_3V3，U13 为天线座；port3/4 到 J8/J9，port2 为 4G 支路（本次不操作）。板载 Wi-Fi 无需插入 J8/J9；外接模块则另核实其供电/天线和实际 ID。
- 已冷启动 scope HPF 的 USB0 Enable=1、PS IO28..39 复用、`USB0PS_ENABLE` 和生成初始化已存在；其匹配 FSBL/PL/U-Boot 原样复用。DWC2 节点 `0xf8180000`、SPI56，原 DTS `reset-gpios=portb14` 对应 MIO46，10ms，最终被 disabled 覆盖；本次只将最后的 USB0 status 改 okay。DWC2 platform.c 接受可选 PHY/clock、调用 reset-controller；PHY 类型由 core 硬件能力选择。本次未猜加时钟、PHY节点或改写 PS 寄存器。
- **Host 时钟/ULPI60MHz、PHY reset电平、J18实际位置、VBUS和Hub/模块3.3V仍需实板测量/枚举验证。** 若没有 root hub/设备，先保存 dmesg、DT 和供电/接线证据，定位 Host/时钟/复位；需要改 PS/HPF/FSBL 时另列最小改动并构建匹配链，不能反复换 Wi-Fi 驱动碰碰运气。

## 构建与产物

VM `uisrc@192.168.43.135`，密码交互或仅当前进程环境 `WIFI_VM_PASSWORD`，不固化脚本。任务默认 `/home/uisrc/embedded-bsp-wifi-20261018`；必须保留 `/home/uisrc/embedded-bsp-scope` 和本机 `bsp/artifacts/scope-release-final`。新一轮独立重建应改用新的 TASK；同一 TASK 的失败重试保留日志，新建日志名。不要运行旧 scope 的全目录身份/证据哈希脚本。

1. `python bsp/wifi/make_input.py <厂商WIFI.zip绝对路径> <独立vendor-input.zip路径>`，仅提取驱动直接源码和候选固件，不搬旧产物。把输出传入 VM `$TASK/input/vendor-input.zip`，把本专项和 `bsp/scripts/make_sd_image.py` 传入 `$TASK/bsp/`。
2. 现存依赖：`~/embedded-bsp/vendor/sources/linux` 完整厂商6.1.111/RT系列源码和 `output/kernel` 匹配输出、Linaro7.5；`~/embedded-bsp-gp/bsp/gp`；scope 的 provider/client/include、已审核 HPF/FSBL/U-Boot及 rootfs 工具；Buildroot2022.02.6 和下载缓存。`build.sh` 复制内核源码/输出、模块源码到独立 TASK；不改共享基线。仍需联网获取未缓存 Buildroot 源码时由其校验官方 package hash。
3. `TASK=$HOME/embedded-bsp-wifi-20261018 bash "$TASK/bsp/wifi/build.sh" > "$TASK/logs/build-attempt-N.log" 2>&1`。构建 `Image/modules`、GP/DMA provider/运动 client、两个 AIC ko；新 kernelrelease 为 `6.1.111-rt42-bsp-wifi1`。驱动使用 `make -C "$TASK/vendor/sources/linux" O="$TASK/output/kernel" M="$TASK/build/aic8800" ARCH=arm64 CROSS_COMPILE=<厂商前缀> CONFIG_PLATFORM_ROCKCHIP=n CONFIG_PLATFORM_UBUNTU=n CONFIG_USE_FW_REQUEST=n modules`。不使用 Ubuntu headers 或 vendor 默认 RK 工具链。
4. `kernel.fragment` 补 WLAN/CFG80211/RFKILL/密码基础；保留原 GP/HP0/GPIO/DMA 和内核其它配置。`stage.py` 生成独立 Buildroot配置：wpa_supplicant+nl80211+CLI、iw、iproute2、BusyBox lsusb与wifi-usb拓扑、wireless-regdb、Python3（用于板端安全录入），BusyBox udhcpc。无桌面网络栈。`driver-privacy.patch` 仅移除厂商连接/扫描日志中的 SSID 值，保留驱动逻辑；其它兼容补丁/失败见 BUILD_STATUS。
5. 固件候选按源码默认 `/vendor/etc/firmware/aic8800D80/` 安装；`CONFIG_USE_FW_REQUEST=n` 复用厂商直接文件加载行为，不能随意扁平复制教程的旧布局。两个重编 ko 在 `/opt/wifi-candidates/`，不在 modprobe 自动搜索路径。已匹配重建的 GP/provider/client 在新 release 模块目录，depmod 仅构建索引，不加载或运行。
6. `python3 "$TASK/bsp/wifi/verify.py" "$TASK"` 执行文件镜像/模块/DT/凭据缺席门禁。`make_sd_image.py` 已改成仅最终必要交付物的显式哈希白名单，禁止 release 递归哈希；不对日志、FAT中间镜像、临时文件或整棵证据目录生成哈希。`output/release/sdcard.img` 为512MiB文件镜像，不是物理写入命令；root PARTUUID 以本批 manifest 为准。

`python3 bsp/wifi/test_host.py` 是主机凭据/生命周期测试，模拟 ip/iw/wpa/udhcpc，不访问网络和设备。它不替代板测。

## 后续 SD 部署及回退

部署前先审阅 BUILD_STATUS、最终白名单 SHA256、verify结果和本 README。板卡/SD恢复后，只读 `Get-Disk`/`Get-Partition` 核对**当次**SD磁盘身份、容量、型号、序列号（读卡器序列不等于卡CID）、非系统盘和覆盖范围；取得当次写入授权后形成具体命令。不沿用历史 disk1/E:/dev/sdb，不在本专项脚本中预设目标。

按现有 `bsp/DEPLOYMENT.md` 流程整盘写入本批 `sdcard.img`，关闭并重新打开物理盘，完整无缓存读回前536870912B并与源最终镜像哈希比较；确认MBR、两分区和根 PARTUUID，镜像fsck结果必须通过。首次启动会修改rw根，不再要求整卡维持初始哈希。由用户断电核对SD拨码及Host跳线、装卡并上电；本任务不自动复位，不写 eMMC/QSPI。

COM4 接入前确认板卡在场及用户已释放端口；115200/8N1、无流控、DTR/RTS=false。保存 FSBL→U-Boot→Linux 原始启动输出，核对本批 `/proc/cmdline` PARTUUID、`uname -r`、SD根身份、1GiB/CMA128MiB及 scope PL/GP资源。不要运行旧 scope ready/init/move/accept脚本，也不要调用 REBASE/ENABLE/START。本专项无需加载 GP/运动模块或运行 delta-scope。UART/当前进程状态没有实测时写未知。

回退：`wifi-sta autostart-off; wifi-sta stop`（如需撤销驱动批准 `wifi-driver revoke`）；关机/断电由用户操作，换回保留的 scope SD，或重新对当次已确认/授权的SD写原 scope `66d1b0cf...a6ff6` 镜像、完整读回并验收根 `8aea5f8d-02`。本轮新 PARTUUID 不应套用旧值。保留回退镜像不等于已执行回退。

## 手动 STA 与验收次序

1. **A / Host与USB**：`uname -r; cat /proc/cmdline; lsusb; wifi-usb`；逐个读取 `/sys/bus/usb/devices/*/idVendor,idProduct` 并保存控制器/Hub父子关系和错误日志。没有枚举先核对 J18、PHY/Hub供电和复位，再测 ULPI时钟。实际ID/模块标签与资料不符则停止选型，源码虽有DC/DW/D80X2 ID，但当前未提供它们的配套固件资格。
2. **B / 驱动固件**：仅实物确认为D80且看到 `a69c:8d80`（boot）或 `a69c:8d81`（runtime）时，显式 `wifi-driver approve-d80 --physical-label-confirmed`，再 `wifi-driver load`。观察固件下载/重新枚举、接口出现，无持续reset/firmware错误。这不是当前已经批准；其它ID必须另审核；loader报告的silicon revision及请求文件也必须匹配，当前固件主要覆盖U02，缺失U01/其它分支时停止，禁止改名伪装。`modinfo /opt/wifi-candidates/*.ko` 对照本批 vermagic，保存 dmesg 必要脱敏输出。不要加载资料旧ko。
3. **C / 扫描关联**：`wifi-sta scan` 输出隐藏SSID值；`wifi-configure` 在**板端本地TTY**隐藏输入SSID和密钥，再输入安装所在地country code。配置器将SSID编码为hex、口令导出PSK，原子写入root目录0700/文件0600；PSK仍是秘密，禁止cat/命令参数/日志/提交/交接包。无固定SSID/密码在可分发镜像；换路由器先 `wifi-sta stop`，重跑配置器（撤销自启动资格）。`wifi-sta start; wifi-sta status`，必须 `wpa_state=COMPLETED`。默认 `wlan0`，实际接口不同时以 `WIFI_INTERFACE=<已确认无线接口>` 调用；不将eth0作为无线。
4. **D / DHCP**：status 应显示正确IPv4/掩码/本接口路由；`udhcpc` 仅在认证完成后运行并持续续租，掉关联会清理该无线接口的地址/路由。网关和目标主机应与路由器DHCP设置一致；不改全局DNS、不删除有线路由。
5. **E / 双向LAN**：`WIFI_INTERFACE=wlan0 wifi-accept <网关IPv4> <电脑IPv4>` 会显示绑定无线接口的route并用 `ping -I` 探测两目标。同一LAN电脑同时 `ping <板卡无线IPv4>`、保存电脑源接口/路由/时间结果；确认回复源是无线地址。电脑到板方向不能由脚本自证，板端有线成功也不能代替本项。AP隔离/电脑防火墙阻挡时保留证据并标未通过，不擅改安全设置。互联网不在验收条件中。
6. **F / 稳定、重连和冷启动**：accept脚本120轮、每轮sleep5秒，至少600秒，记录每个ping结果/丢包、关联丢失和USB/固件事件前后快照（按内核时间戳比较；ring buffer绕回时另行持续采集）；USB事件需人工判读，脚本退出0不单独签核F。随后 `wifi-sta reconnect` 进行一次受控断线/重新认证/DHCP，重新验证双向地址。手动成功后 `wifi-sta autostart-on`（仅COMPLETED+IPv4允许），再由用户断电冷启动；启动脚本在后台加载**本板已批准的**驱动、最多等接口30秒并启动STA，路由器离线/认证失败时不阻塞系统启动。记录冷启动身份、自动关联/DHCP、电脑反向可达及本地控制服务未受影响。STA worker会尝试重连/重新DHCP；USB拔出/接口重命名/驱动失败需显式恢复，不声称已通过热拔插验收。

只采集必要的脱敏原始输出；SSID统一用目标AP别名，扫描输出已过滤SSID，MAC/邻居AP信息按移交需要脱敏。不要开启 wpa `-K/-dd` 或保存凭据配置、shell trace、无线数据包。最终记录模块、串口、后台worker/DHCP/wpa、SD部署与板卡状态，不把2026-10-13 scope最后状态当作当前实板状态。
