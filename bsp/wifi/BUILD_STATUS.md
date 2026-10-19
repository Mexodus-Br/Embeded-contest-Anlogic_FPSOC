# 2026-10-19 Wi-Fi + HTTP 当前进展（覆盖下方对应历史状态）

- 用户已授权本次新SD格式化/烧写；Windows重新核对31708938240B USB目标身份并完成512MiB写入、完整无缓存读回，源/读回一致。根PARTUUID `70d791a8-02`，镜像SHA256 `03a1ad579677026833863d3335e8d76d21074acb7c1dc577eb2594ba16e5bb65`。
- HTTP用户态独立候选/最终ext4检查通过，原内核/模块/启动链/DTB未变；4项VM HTTP安全/完整下载测试通过，不能当作实板LAN通过。
- 用户装卡/连接COM4并上电后，FSBL→U-Boot→Linux/SD根、1GiB/CMA128MiB、DWC2 Host/Hub和实际a69c:8d80通过。首次loader路径失败已留证；补同套U02平面路径别名后，chip_id=7固件下载、a69c:8d81和wlan0出现。原候选文件未包括这项实板后修复，部署态与文件镜像须分开标识。
- r2修正版含平面固件路径别名与相同模块/启动链，独立本机镜像 `bsp/artifacts/wifi-http-20261019-r2/sdcard.img`，根 `c7965caa-02`、SHA256 `d429f239584c35a8a5a9c185af0a5f864f301750d343a6cd3c9e27f256cc1d81`。离线验证通过，尚未写卡；不能把当前首版+板端修复的运行结果写成r2冷启动通过。
- 前期配置后实查Wi-Fi配置root:0600，但HTTP认证文件不存在，随后由用户补本地认证。发现最小BusyBox无stat，已用Python lstat最小修复STA权限检查并应用在当前SD。该阶段STA worker运行、SCANNING，扫描15个网络但目标不可见；后续用户补漏输的@后已关联，最终结果见下项。全程无运动操作。
- r3独立镜像 `bsp/artifacts/wifi-http-20261019-r3/sdcard.img`，根 `82e6e1bc-02`、SHA256 `db50bdcf1908977fc29fd09bdc9e75d28e79475799a8a2fb0f703359c08cc734`，包含固件路径与STA权限检查修复。最终EXT4/启动链/内核/模块/源码/固件别名检查通过；未写卡。当前首版SD+两项持久修复不能冒充r3。
- 最新实测：用户修正SSID漏输@后WPA2-PSK COMPLETED，DHCP 192.168.2.245/24，网关192.168.2.1；电脑WLAN192.168.2.244/24。HTTP以UID/GID498运行；绑定电脑无线源的首页200、二进制逐字节、脱敏快照重复下载及401/404/403/405预检通过，用户浏览器认证/下载通过。板卡wlan0→网关4/4、电脑→板卡10/10；板卡→电脑0/4，Public入站Echo未见放行，未更改防火墙。板端604秒稳定观察通过；电脑601秒117轮HTTP/下载无失败，独立ping601发600收丢1包约0.17%；受控重连及用户冷启动自动联网/HTTP/下载复测通过。板卡→电脑ICMP方向仍未通过，完整A–F不能写全部通过。最终板卡上电，COM4关闭释放，HTTP UID498运行；细节见http/BUILD_STATUS.md。
- 细节、路径、凭据/服务操作及电脑验收入口见 [http/README.md](http/README.md)。旧Wi-Fi候选与scope回退镜像保持。

---

# Wi-Fi STA 候选交付状态 — 2026-10-18（Asia/Taipei）

**OFFLINE_VERIFIED / 停于 SD 烧录前；未部署，Wi-Fi 未验收。** 用户明确板卡与SD本次不可用；COM4空闲但板卡不在手边。本专项未打开串口、访问物理磁盘、复位/上电板卡、操作eMMC/QSPI、加载板端模块或发出任何运动命令。当前板上镜像、供电、模块、buffer和进程状态未知，不沿用历史scope末态。

## 构建身份及位置

- 本轮起点 Git `a222f0d`；保留用户未提交 `AGENT.md`（含最新§11.5哈希限制）、其它agent文件、log/和工具日志。源码提交范围仅 `bsp/wifi/` 与打包器 `bsp/scripts/make_sd_image.py`。
- 硬件沿用已冷启动scope：冻结PL源码 `df17b4e`、GPIO封存 `1ae5ce1`，scope HPF `609639dec28432912e7bcbddee90328edbeaca1a1ee46193d657e8cffa79103b`。最终 BOOT.bin 与原scope逐字节一致；没有重新生成PS/HPF/FSBL/PL，也未集成安全/RS485/HP1。`bsp/telemetry/BUILD_STATUS.md` 的不可部署门禁未解除。
- VM `192.168.43.135`，独立目录 `/home/uisrc/embedded-bsp-wifi-20261018`；Linux完整源码 `vendor/sources/linux`、配套输出 `output/kernel`、模块直接源码 `build/modules` 和 `build/aic8800` 均保留。共享baseline/scope源码与产物未覆盖，下载缓存复用 `~/embedded-bsp/downloads`。
- 内核 `6.1.111-rt42-bsp-wifi1`，厂商Linaro GCC7.5，MODVERSIONS/aarch64；`-rt42` 是厂商版本后缀，不表示PREEMPT_RT验收。
- 本机交接包：[wifi-sta-scope-candidate.tar.gz](artifacts/wifi-sta-scope-candidate.tar.gz)，147609744字节；SHA256 `24c5a24ecf96e926c2a144064b41bacb3badf36bbc22b408754651d0ed08f24a`。VM同名包在任务目录下。
- 本机可烧录候选文件：[sdcard.img](artifacts/final/release/sdcard.img)，536870912字节；SHA256 `4f82a98fb6bd970bbe2a8d51265c173221afee338fdf73f24c597a2c362af943`；根 PARTUUID **`4fa65f13-02`**。候选已完成离线审核，实际模块/USB ID仍是上板选型门禁，不能当作已可用的联网系统。
- [manifest.json](artifacts/final/release/manifest.json)、[SHA256SUMS](artifacts/final/release/SHA256SUMS) 只含12个明确最终交付文件的身份；没有对日志、FAT中间文件、临时文件或整棵证据目录哈希。包及解包后12个最终文件已在Windows再次校验，全部一致。Git不保存大二进制，保留在上述本地与VM目录。

## 变更及离线验证

| 检查 | 结果与边界 | 证据 |
|---|---|---|
| USB完整链路资料审查 | 手册/原理图/PS pinmux/FSBL输入/DWC2/reset源码已核对；Host时钟、J18和供电实际状态待板测 | README的硬件链路与排查顺序；原始PDF路径见下方 |
| 内核配置 | WLAN、CFG80211/WEXT、RFKILL、CCM及regdb签名依赖；新localversion；原USB Host保留 | [kernel-config-diff.txt](evidence/kernel-config-diff.txt)，交接包debug/kernel.config |
| DTS | 与scope编译DT规范化比较，**仅USB0 status disabled→okay**；GP/HP0/GPIO/IRQ/内存/CMA其余保持 | [verification.json](evidence/verification.json) |
| GP/provider/运动client匹配重建 | PASS编译；vermagic一致、导入符号CRC分别31/48/42项全部匹配；未加载/运行 | verification.json模块条目；原始build.log |
| AIC两个ko | PASS编译/modpost；vermagic一致；loader69/fdrv222项导入CRC全部匹配；fdrv依赖aic_load_fw；不在modprobe搜索路径 | verification.json；`/opt/wifi-candidates/` |
| 驱动兼容修复 | 此厂商6.1.111树不需内核API兼容补丁；关闭vendor RK/Ubuntu平台路径，用匹配树/输出/工具链编译 | build.sh、prepare_driver.py；不能外推其它6.1树兼容性 |
| 驱动日志隐私 | 最小driver-privacy.patch移除SSID值的连接/扫描打印，无协议/运动修改 | driver-privacy.patch |
| 用户态 | wpa_supplicant/nl80211/CLI、iw、iproute2、BusyBox lsusb/udhcpc、wifi-usb、wireless-regdb、Python3安装到最终ext4 | verify.py逐文件与Buildroot target比较；无udev/桌面网络栈 |
| 凭据/启动门禁 | 分发镜像无SSID/PSK配置、无driver-approved/autostart；通用supplicant模板无network；无运动自启动 | verification.json；板端TTY录入尚待实板执行 |
| 主机脚本回归 | 4项PASS：标准PSK向量/无明文、注入与字节长度、异步start及认证前自启动拒绝/重连/停止、无线限定DHCP及掩码门禁 | [host-tests.log](evidence/host-tests.log)；模拟工具，不是无线连接 |
| 文件镜像门禁 | PASS：512MiB/MBR/分区范围、FAT和rootfs分区逐字节比较、FAT只读fsck、EXT4只读fsck、已安装工具/模块、无凭据 | 原始finalize-1.log、verification.json；未写SD |
| 本机移交校验 | 包SHA及明确12项最终文件SHA全部PASS | 本机artifacts/final及本记录身份 |

原始完整构建与最终化日志在本机 `bsp/wifi/artifacts/logs/build.log`、`finalize-1.log` 及VM `logs/`；不入哈希清单。[build-summary.txt](evidence/build-summary.txt) 是必要诊断摘录，不是完整告警列表。保留了首次后台派发未持久化、初始usbutils因udev依赖未被选择、Python3.6主机兼容适配和后续finalize过程；初始候选不是最终交付身份。Expat上游下载404后Buildroot源码镜像回退成功并通过package hash；没有忽略源码校验失败。内核ELF栈帧、BusyBox未使用返回值、host fakeroot格式和厂商DTS unit-address/simple-bus告警仍保留，未借构建成功宣称硬件已通过。

## 驱动、固件与实物资格

资料来源：`D:\Works\Embedded_contest\docs\Analogic\01_start\02_start_Linux\05_application_demo\05-4_无线通信方案\WIFI.zip`，源码 `aic8800/aic_load_fw`、`aic8800/aic8800_fdrv`（RWNX版本字段6.4.3.0）。厂商教程同目录PDF；硬件手册为 `hardware_MLK_F3P_CZ02_DR1_20250526/01_硬件手册/MLK_F3P_CZ02_DR1开发板硬件使用手册.pdf` §13；底板原理图为同资料根 `02_原理图/MLK_F3P_DR1_250526.pdf` p8–9，已渲染视觉核对。

图纸U12标 `SKI.WB800D80U.2`，经U11 Hub port1到USB3320/PS USB0；这不是实物型号结论。实际型号、芯片revision、USB VID/PID、天线、焊接/接线和供电仍待板卡恢复后核对。仅提供 `a69c:8d80` boot / `a69c:8d81` runtime **D80候选**的显式本地批准流程；其它芯片ID不能复用本候选固件资格。

固件源ZIP `aic8800D80/` 原样装至 `/vendor/etc/firmware/aic8800D80/`。文件包括 `fmacfw_8800d80_u02.bin`、`fmacfw_8800d80_h_u02.bin`、`fw_adid_8800d80_u02.bin`、`fw_patch_8800d80_u02.bin`、`fw_patch_table_8800d80_u02.bin`、校准/RF测试候选及两份不含网络凭据的配置。源码也有U01/IPC/其它芯片路径，但供应文件并不覆盖所有分支；**USB ID确认后仍须从loader原始输出核对silicon revision和所请求文件。缺失U01/其它固件时停止，不改名伪装为匹配。** 当前USB_BT及非IPCAM默认配置复用厂商组合固件路径，没有启动用户态蓝牙服务。

## 实板验收矩阵

| 层 | 本批结果 | 恢复实物后所需证据 |
|---|---|---|
| A USB Host/VID/PID | **NOT EXECUTED** | 当前启动身份、Host/root hub/Hub拓扑、模块VID/PID；必要时测时钟/复位/电源和核对J18 |
| B 驱动/固件 | **NOT EXECUTED** | 模块标签和silicon revision、重编ko加载/固件请求与成功、无持续reset/错误 |
| C 扫描/关联/认证 | **NOT EXECUTED** | 脱敏扫描；目标AP本地配置；wpa_state=COMPLETED |
| D DHCP IPv4/掩码/路由 | **NOT EXECUTED** | 无线接口地址、DHCP租约/掩码、本接口路由；当前无线地址：**未知** |
| E 无线到网关/电脑及电脑反向到板卡 | **NOT EXECUTED** | ping绑定无线、源/目的地址与路由，电脑反向结果；不关闭防火墙/隔离来凑通过 |
| F ≥10分钟/受控重连/用户冷启动 | **NOT EXECUTED** | 两目标各120次ping丢包、关联及USB事件、重连后复测、人工冷启动自动关联/DHCP/反向可达/本地服务状态 |

后续执行、可变SSID的本地TTY录入、start/stop/status/reconnect、自启动批准、SD当次身份与覆盖授权、完整读回和scope回退步骤都在 [README.md](README.md)。由于本次无板/SD，未请求重复释放COM4或沿用任何历史磁盘号。

## 结束状态

VM构建、finalize和主机测试已结束；测试STA/wpa/DHCP进程已退出。候选文件已移交到Windows本地；原scope回退镜像保持。SD未写，COM4未打开，板卡状态未知，板端没有由本专项启动的后台进程或运动操作。后续需要板卡/SD恢复、确认实物标签/USB ID/供电与Host跳线、提供实际目标SSID/当地country code（密钥仅板端录入）及同LAN电脑；写卡前再核对当次SD身份与授权。**离线准备完成不等于联网成功；A–F尚无本批实板通过项。**
