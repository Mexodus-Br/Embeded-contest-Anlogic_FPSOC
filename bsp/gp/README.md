# GP最小控制软件

2026-10-12。权威契约为 `pl_interface/schema.json` 的 `gp_control_probe_v1`（确认提交ca50bbf），不是本目录另设地址表。用户已确认platform驱动＋字符设备方案。软件已在虚拟机192.168.43.133、原配套内核树实际构建。PL交付cc16fe2已集成，真实PS＋GP完成bitgen、含bitstream的HPF与匹配FSBL、BOOT.bin及完整SD镜像；**PS内部时钟模型已修复，完整重布线通过，最终GP节点okay；同一SD烧写、512MiB直接读回及文件系统检查通过。用户结束本次任务，冷启动/GP/IRQ/快照实板验收未执行**。详细实际结果和重建步骤见[BUILD_STATUS.md](BUILD_STATUS.md)。

## 软件与访问边界

`prepare_gp.py`从共享生成头提取内核可用常量，并从唯一profile生成候选DTS；节点始终disabled。`bsp_gp.ko`只匹配本probe compatible，校验4KiB窗口、level-high触发及VERSION/CAPS/FEATURES/TICK_HZ。`devm_ioremap_resource`取得设备映射，内核使用readl/writel；用户态不获得MMIO映射、物理地址或DMA接口。

`/dev/bsp-gp`为0600，open要求CAP_SYS_RAWIO，单writer；ioctl使用固定大小整数结构与copy_from/to_user，命令和快照由mutex串行化。仅NOP/SNAPSHOT可提交，运动opcode在软件中拒绝，不向总线写入。禁止用devmem或非法寄存器试探AXI SLVERR（可能造成CPU abort）。外部模块必须使用原配套.config、generated headers及Module.symvers，不能按相同release字符串任意替换。

命令编号从LAST_TXN_ID继续，u32耗尽停止；100ms超时不自动重提旧动作。重复调用只允许当前连接刚成功完成的同一无动作命令。SNAPSHOT读ID/VALID、全部64bit字段、再读ID/VALID。completed仅为NOP/快照操作完成；位置为实际STEP命令计数，不是编码器位置或运动终点。首轮PL源为空闲四轴0/invalid，变化源原子性须结合PL自检，不能由静止板值单独证明。

IRQ线程读取pending&mask并屏蔽全部输出，保存事件位和单调计数后唤醒poll，避免持续源造成中断风暴。用户通过受限IRQ_CONFIG请求内核解除测试源、W1C、读回并重新启用指定ACK/TEST位；事件清除不撤销ACK/快照。mask寄存器与IRQ线程受spinlock保护；新事件在copy_to_user期间到达仍保留给下一次poll。关闭连接清测试源/屏蔽并清pending，不复位时间戳。设备解绑使后续文件访问返回ENODEV，IRQ同步释放，文件引用维持对象生命周期。首轮不支持运行中PL复位/热重配置，必须先停访问并解除驱动。

## 构建与检查

Windows先运行：

```powershell
python pl_interface/generate.py --check
python bsp/scripts/prepare_gp.py
python bsp/scripts/check_gp_contract.py
```

将本目录传到VM `~/embedded-bsp/gp-software`，构建脚本为 `bsp/scripts/build_gp_software.sh`。它检查原kernel .config和Module.symvers哈希，以W=1构建模块、以-Wall/-Wextra/-Werror构建AArch64验收程序。实际日志见 `../evidence/gp-software-build.log`；GP模块vermagic为 `6.1.111-rt42-bsp-sd1 SMP preempt mod_unload modversions aarch64`。

候选DTS已与原BSP设备树离线cpp/dtc编译通过：reg=`<0 0x80400000 0 0x1000>`，interrupts=`<0 82 4>`，status=disabled。继承的工厂DTS格式警告保留；这只核对格式，不证明SPI映射、时钟或实际PL decode。

`contract.template.json`为集成证据清单模板，不是新的契约。`check_gp_contract.py --require-evidence --evidence ...`必须获得实际GP端口、转换器、完整地址译码、IRQ映射、共同复位/时钟、自检和STA、地址图及HPF/bitstream哈希证据。哈希保证可复查输入身份，不替代人工审查真实报告和电气验收。证据不足时保持disabled；不将现有PS-only HPF作为GP工程。

已通过stage_gp_rootfs.sh重新打包256MiB rootfs，安装本次模块和gp-accept、运行depmod，并安装已经修正的 `bsp/scripts/board_readonly_check.sh`；现有完整Linux构建及finalize脚本已安装该检查脚本。直接读取EXT4文件内的三份新增/更新产物哈希已匹配，e2fsck通过，见../evidence/gp-rootfs-stage.log与gp-software-manifest.json。最终镜像绑定新SD根PARTUUID=20ae01e9-02，原发布镜像仍为d0e414b9-02；最终启用GP重新打包后必须以新manifest为准，不能沿用旧UUID。保留原发布包及eMMC原系统。

## 首轮板上流程（尚未执行）

1. 新PL自检和实际系统时序/地址/IRQ/DDR审查通过，生成匹配HPF→FSBL→bitstream→BOOT.bin及DTS，才启用probe节点。审查镜像后核对目标SD身份并按已有授权部署；目标不明或换卡先确认。
2. 明确板卡状态、串口空闲后启动 `python bsp/scripts/capture_serial.py --log bsp/evidence/<唯一名称>.log --seconds 300`。该脚本COM4/115200/8N1、DTR/RTS=false，只接收原始字节。就绪后由用户冷启动，保存FSBL→U-Boot→Linux，核对PL实际版本、加载输入及SD根PARTUUID。
3. 执行修正版bsp-readonly-check，然后显式加载bsp_gp；probe身份不符立即停止，不猜改地址或强行访问。
4. 执行 `gp-accept /dev/bsp-gp`：身份、测试读写、NOP/快照ACK、重复快照、时间戳推进、空闲四轴快照、mask时事件锁存、持续源W1C保持、poll触发、解除源/W1C/无风暴/retrigger，以及ACK事件清除与缓存保持。记录stdout、串口原始输出、/proc/interrupts前后及dmesg。
5. 分别报告构建、部署、启动、GP、IRQ、快照；不把idle快照通过视为运动或变化源的完整原子性验收。运动DMA、实体电机、DDR/CMA压力与供电实测仍另阶段执行。
