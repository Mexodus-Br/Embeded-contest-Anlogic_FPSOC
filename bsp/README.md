# Buildroot 最小 SD 启动基线

2026-10-11（Asia/Taipei）。状态：**已构建，实体SD烧写及512MiB直接读回校验成功；已完成SD根启动及DDR/CMA只读核对，冷启动全链路待采集**。实板证据见[BOARD_VALIDATION.md](BOARD_VALIDATION.md)。后续部署实录见[DEPLOYMENT.md](DEPLOYMENT.md)。
2026-10-12 GP控制批次已按冻结契约集成PL控制顶层、匹配HPF/FSBL/BOOT.bin/DTS和platform/misc驱动及验收程序；SD512MiB完整读回通过，根20ae01e9-02。用户装卡上电后FSBL→U-Boot→Linux启动通过；1GiB/CMA128MiB、GP版本/读写/无运动命令、IRQ及空闲四轴快照41项检查通过。动态运动、DMA/HP0和电机仍未验证；详细状态见[gp/BUILD_STATUS.md](gp/BUILD_STATUS.md)。
范围是串口、DDR/CMA、SD/eMMC和驱动构建基础，以及最小GP控制验证。HMI、运动内核和独立AXI DMA硬件联调尚未集成。

## 交付物

本地 `bsp/artifacts/bsp-release.tar.gz`；虚拟机 `/home/uisrc/embedded-bsp/bsp-release.tar.gz`。
解包后包含：

| 路径 | 内容 |
|---|---|
| `release/sdcard.img` | 512MiB完整SD文件镜像，含MBR、FAT32启动分区和EXT4根分区 |
| `release/boot/` | BOOT.bin、boot.scr、system.dtb、uImage.lz4 |
| `release/rootfs.ext4` | 256MiB Buildroot根文件系统，已装入本次内核模块 |
| `release/system.hpf`, `system.bit`, `fsbl.elf`, `u-boot.bin`, `boot.bif` | 一致启动链及可审查输入 |
| `release/boot.cmd`, `manifest.json`, `SHA256SUMS` | SD根分区绑定脚本、版本/大小/哈希清单 |
| `debug/` | kernel/U-Boot/Buildroot `.config`、Module.symvers、System.map、vmlinux、展开DTS、DTS适配头 |
| `support/` | 内核生成头与工具、FSBL map/符号/反汇编/平台源码、源码包及下载哈希、配置和补丁 |
| `logs/` | 实际构建、首次失败、镜像验证和重复打包日志 |

Git只保存项目脚本、配置和小型证据，二进制交付物由上述本地文件和虚拟机目录保存。
哈希见 `evidence/manifest.json`。最终 `sdcard.img` SHA256：
`289f90f22cf5bbaa387004a837b192d8b94ba366875f9bb8fe475a1043636049`。
交付包SHA256：`43c4891b803110844350f64feef96cf6027bd5197975cc1fc901354693b17eac`。

## 已核对的环境、源码和适配

- 构建主机为用户提供的Ubuntu虚拟机 `uisrc@192.168.43.132`，实际Ubuntu18.04.4/x86_64、Linux4.15.0-91、4核、7.8GiB RAM；初始可用空间163GiB。它不是板端Ubuntu。
- Linux交叉GCC为厂商Linaro7.5.0；FSBL为厂商包内Arm GNU12.3.1。两者实际编译成功。Windows FD交叉GCC失败记录不作为本次可用工具链。
- 厂商Linux包：`uisrc-lab-anlogicM-V4.0.1.tar.gz`，SHA256 `7214035eea18e0df67a1aaa401ad9d024c4a5560cb5843af50e5f75e9c81d292`；Windows与虚拟机文件一致。包含Linux6.1.111及内嵌RT改动、U-Boot2021.01、Buildroot2022.02.6、DR1M三组defconfig和Linux/BM工具链。原始包无改动，另展开在 `~/embedded-bsp/vendor`。
- 当前TD：2026.1 SP2 / 6.2.2.200067；PS配置器内部报告2025.10，HPF工具报告2026.05，HPF格式202601。当前FD：2026.1 SP1。完整Master SDK经用户授权用SCP传入独立目录 `~/embedded-bsp/sdk/master_sdk`；传输包SHA256 `938b22dac5eb688df4d5d8404aef5dda06deef43a9d30e12a79f185e8c113ac4`。
- PS-only工程来自指定二次开发demo；无运动、显示、通用DMA或外部PL IO。TD实际完成布局布线及bitgen，0 LUT/0寄存器/1 SoC；派生PS时钟约50MHz、无有效PL数据时序路径，STA coverage=0%。这不验证100MHz运动内核。
- 项目内核补丁 `patches/0001-anlogic-dma-composite-module.patch`：将框架和AXI DMA/可选VDMA实现合成一个模块，子实现选项改为bool。解决实际modpost缺失7个共享符号的问题，并使厂商 `#ifdef CONFIG_AXI_DMA` 分支在框架为模块时也生效。测试驱动独立为模块；无自动加载。
- FD2026 SDK的平台头需要 `HAVE_*_DRIVER` HAL声明，TD2026 HPF没有这些声明；`build_fsbl.sh`仅补声明宏，不改变HPF外设路由/使能。平台必须置于SDK目录内，修复厂商make对SDK外路径错误归档源码的问题。FSBL采用EL3/AArch64/OCM，符号确认包含 `SoC_M90_DdrInit` 和 `__Soc_PlatInit`。
- `dts_from_hpf.py`以FSBL实际头文件的CPU/UART/MMC值覆盖TD生成DTS头中的不一致值，并桥接旧BSP的以太网宏名。CPU配置999.9MHz、UART400MHz、SD/eMMC IO上限49.995MHz是工具配置值，不是实板频率测量。TD原始DTS头将MMC上限算为199.98MHz、容量写为4096，不能原样作为本板容量/速率。内存节点明确1GiB。首批禁用网络、USB、CAN、NPU、ADC、PS AXI DMA/WDT/TC客户端；AHB DMA与QSPI沿用厂商声明，其时钟/传输未验收。相关扩展需另核对时钟与路由，不能将生成头内AXI/AHB频率声明当作实測值。

## DDR核对结果及限制

用户基线为1GiB、32bit、1333MT/s、1.35V，工具配置为两片x16/4096Mbit、DDR3_1333G、training=1。已在当前PS工具中设置真实IP配置并重新生成；父级设计参数与生成PS参数同步后导出含本次bitstream的HPF。

HPF报告、`soc_plat.h`及生成初始化已核对。默认 `DDR_INIT_V2` 使FSBL实际执行工具生成的 `SoC_M90_DdrInit`，并非只修改报告。**同版本工具的1.5V对照与1.35V生成的 `soc_plat.c` 字节相同**；`soc_plat.h`的DDRC_IO_VOL分别不同。旧SDK参数路径虽有 `.io_vol`，其初始化函数后续未消费此字段。不能宣称软件改变了供电或证明不同电压下的模拟配置已正确；见 `evidence/ddr-voltage-compare.json`。

HPF工具日志中的训练DONE是生成过程输出，不是实板训练结果。C115/C116非GND端电压、DDR颗粒丝印/DDR3L兼容性、板卡修订、冷启动训练、内存压力和温度裕量均未验证。保留厂商对电压字段与V2寄存器相同结果的解释核对项，不猜改PHY常量。

## 重建流程

先核对上述两个源码包哈希。每次完整独立重建使用新的Linux任务目录，保留已交付目录作为比较基线。不要删除或修改厂商原始资料。

Windows，工作区内先执行 `python bsp/scripts/prepare_hw.py`（已有work工程时会拒绝覆盖）。在 `bsp/work/soc_prj` 内用本机alps的 `-batch` / `-tcl ../../scripts/ps_regen.tcl`，参数为 `-component system_ARM_Processor_System_0`、当前TD ARM_Processor_System IP目录、`-device DR1M90GEG400`、当前work工程 `system/ip` 输出目录及 `-speed -2`。实际调用见工具日志；传入Tcl的路径用绝对路径。
接着执行 `sync_ps_design.py`，用 `td_commands_prompt.exe`运行 `build_hw.tcl`，完成后用hpfTool批处理运行 `export_hpf.tcl`（工程、PS、design和bitstream绝对路径对应work工程，bitstream状态latest）。工具脚本现按本工作区路径设置，迁移时统一更新路径。

**不要将XML重新序列化为不同namespace前缀**：厂商HPF解析器对此敏感。PS工具有UART整数转换警告；已检查生成值为0xffffffff及115207bps计算结果，实板串口仍待确认。

将HPF作为Linux构建的 `TASK/system.hpf` 输入，将项目 `configs/ scripts/ patches/` 传入 `TASK/bsp/`，Master SDK传入 `TASK/sdk/`。首次解包Linux包到 `TASK/vendor/` 并创建 `TASK/logs/extract.ok`。传输可用SCP；凭据仅交互输入，不存入脚本。

```sh
export TASK=$HOME/embedded-bsp-new
# TASK/vendor、TASK/sdk/master_sdk、TASK/system.hpf和TASK/bsp已备妥且哈希已核对
bash "$TASK/bsp/scripts/build_fsbl.sh"
bash "$TASK/bsp/scripts/build_linux.sh"
python3 "$TASK/bsp/scripts/make_sd_image.py" "$TASK"
bash "$TASK/bsp/scripts/verify_release.sh"
bash "$TASK/bsp/scripts/collect_release.sh"
```

`build_linux.sh`按厂商defconfig加项目fragment生成最终.config，保存匹配模块并通过overlay在rootfs生成前安装。当前首批构建在排错后另运行了 `finalize_linux.sh`，最终配套参数已合并回完整构建脚本。
构建固定SOURCE_DATE_EPOCH、Kbuild身份和版本；Buildroot启用REPRODUCIBLE。下载依赖按Buildroot各package `.hash`校验，实际下载哈希见support；依赖缓存保存在TASK/downloads。**已验证两次相同输入的SD打包SHA256相同；尚未完成第二次独立源码全量重建的逐字节比较**。不要把这两者混为一谈。

内核名称实际为 `6.1.111-rt42-bsp-sd1`，但 `CONFIG_PREEMPT_RT`未启用，`CONFIG_PREEMPT=y`；-rt42来自厂商源码树，不是RT能力验收。CMA配置由DTS指定128MiB，不将池地址冻结为DMA buffer。

## 模块与后续GP/中断/DMA

`anlogic-dma-engine.ko`、`axi-dma-test.ko`及GP/UIO模块已构建；MODVERSIONS开启，vermagic是本次内核且包含modversions/aarch64。rootfs模块目录按同一kernelrelease安装。
完整配套Linux源码/输出树保留在虚拟机 `TASK/vendor/sources/linux`、`TASK/output/kernel`。support中的生成头及符号用于身份核对，单独解包并不替代完整源码/构建树。外部模块在该配套树以 `ARCH=arm64 CROSS_COMPILE=... make -C <source> O=<output> M=<module> modules` 构建；不使用通用Ubuntu headers，也不向旧#8 Buildroot或#17 Ubuntu镜像复制这些模块。

后续独立Anlogic AXI DMA采用已确认HP0、64bit stream、simple、每记录一个packet和DMAengine。先独立GP读写/IRQ与双向回环；运动地址、GIC SPI、时钟、复位/CDC、dma mask、Lite/DDR位宽、DRE/SG和TLAST均与新PL工程共同核对后才生成DTS。当前没有AXI DMA设备节点，不会因模块存在而访问厂商显示/以太网的地址。`axi-dma-test`厂商测试的尺寸/参数需另审，不能视为80B/128B记录协议测试。运动内核100MHz时序尚未验收，未集成。

## 部署：必须先确认目标SD

首次构建没有操作实体SD；用户后续插卡并明确授权格式化/烧写，已完成唯一USB SD目标的写入与直接读回验证，见DEPLOYMENT.md。eMMC/QSPI未操作。以后部署其他卡仍须确认**设备路径/Windows磁盘号、型号、序列号、容量以及可覆盖内容**。仅凭盘符、/dev/sdb、历史设备名或大小不确定目标。

1. 解包并核对交付包SHA256，进入release执行 `sha256sum -c SHA256SUMS`；Windows可用Get-FileHash。需整盘写入sdcard.img，不能只复制boot四文件到任意已有分区：boot.scr绑定本镜像MBR根分区PARTUUID `d0e414b9-02`。
2. 只读列盘：Windows `Get-Disk` / `Get-Partition`；Linux `lsblk -d -o PATH,MODEL,SERIAL,SIZE,TRAN,RM`，并核对所有挂载分区。目标至少512MiB，建议1GiB以上。等用户确认后再形成该设备的具体写入命令，卸载其分区、写入全盘、flush。
3. 首次启动前，对目标卡前536870912字节做完整读回SHA256，须与sdcard.img相同；此后Linux首次挂载会修改文件系统，不能要求启动后整卡哈希仍一致。剩余空间本批不自动扩容。
4. 板卡断电状态下核对拨码；资料SW1/SW2/SW3为SD=011、ON/OFF/OFF（ON=0）。插入已确认卡，核对供电和实物修订后由用户上电；保存FSBL→U-Boot→Linux完整串口日志。
5. PS UART115200/8N1、无流控；仅板卡状态明确且COM4实际可用时连接，DTR/RTS保持false。2026-10-11用户确认板卡状态后已连接COM4，见BOARD_VALIDATION.md。启动后运行 `/usr/bin/bsp-readonly-check`，核对cmdline的PARTUUID、实际root MAJ:MIN对应sysfs type=SD、1GiB/128MiB CMA、mmc错误和模块身份。
6. 验收冷启动、反复启动、DDR/CMA压力与分配、SD读写/断电持久性、驱动加载后独立DMA等另行实施。第一步只读核对不运行devmem、DMA、memtester或存储写测试，不自动运行运动。eMMC保留原系统。

任一镜像加载/根UUID校验失败，脚本打印BSP_ERROR并返回U-Boot；不改回mmcblk1p2。成功root在SD也不单独证明BootROM第一阶段来源，须结合拨码与FSBL/U-Boot启动日志验收。

## 实际结果

主机端哈希、MBR分区、FAT32只读fsck、EXT4只读fsck、uImage/boot.scr头、DTB的1GiB和128MiB CMA、SD/eMMC aliases、模块vermagic、U-Boot无持久环境及FSBL DDR初始化符号已检查。厂商DTS仍有unit-address/simple-bus格式警告，见evidence/verify.log；本批未据此宣称设备板上工作。
实体SD写入、512MiB直接读回及文件系统检查已通过。COM4实板核对确认Linux/Buildroot、SD根PARTUUID、1GiB映射、128MiB CMA及完整内核配置哈希匹配。DDR供电/颗粒/训练、长期存储可靠性、CMA/DMA压力与传输、IRQ/GP/HP0/CDC和运动时序均未验证；仍需完整冷启动串口证据。
