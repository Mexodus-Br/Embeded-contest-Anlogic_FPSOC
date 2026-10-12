# SD启动与GP实板核对

## 2026-10-13 恢复修正版冷启动与完整验收通过

- 镜像afa13b144ff165d171d3b6c5c7ebe8403a2ef216bfc2bbca3f3de8f88420050d此前同一SD Windows完整无缓存读回通过；用户装卡冷启动。COM4 115200/8N1、DTR/RTS=false，完整FSBL→U-Boot→Linux日志19106B，SHA256 c67fbdfbd5a0529360fc7d4665ee20a7c9d86df5f13c712d960ff68f7c81db50。FSBL bit生成20:51:00/HPF导出20:53:02、DDR1024MB/1333Mbps、SD来源/PL加载及common reset释放，Linux新根PARTUUID a3d29e67-02、mmcblk0p2/type SD；1GiB映射、MemTotal1013512KiB、CmaTotal131072KiB。EXT4 journal recovery完成，无文件系统错误报告；不作为掉电或长期存储压力验收。
- 内核6.1.111-rt42-bsp-sd1、.config SHA81f7b75c...00dbf1，provider faf67264...387c63、client 8572344d...6e6cf、DMA app 057fff84...015cc及原GP模块/app哈希、vermagic和DTS资源门禁通过。GP0x80400000/4KiB/SPI82保持，DMA0x80500000/4KiB/SPI83/84、simple、mask32、BTT16匹配。GP VERSION1/CAPSf/FEATURES7/TICK_HZ1MHz；前后各41项通过。
- 两轮各222场景，共444：426正常传输、2161698B，在17种长度（1..65535B、非整拍及页边界）/4模式/重复传输中逐字节和guard通过、正常双回调各1。12次预期超时（RX无TX和TX无RX各6）、6次显式在途terminate；18异常均观测inflight，444次pair quiescent均1，累计errors0，每轮timeouts6、recoveries/generation222。异常后4097B正常包均通过；延迟检查无继续写入。第一次client卸载前再次确认停止后释放buffer，重载重新分配并重复全部场景通过。
- DMA GIC115/116 Level各426次，GP GIC114最终6次，Err0；独立只读收尾观察闲置一秒DMA计数无变化。GP epoch 47186631→65559292，DMA恢复及buffer重建未重置GP时间戳。最终三个模块加载、client无用户引用且无在途传输，coherent缓冲区由client保留。
- 提交8.010–16.770μs，提交至IRQ完成17.160–104.970μs、均值25.403μs；两轮聚合199.901/199.612MB/s、合计199.756MB/s。口径为payload/累计提交至IRQ完成时间，不是持续总线带宽；每次复位、guard等待和串口打印的开销不包含在该分母，生产FIFO吞吐另测。
- 原始验收日志198039B、SHA256 fcfda6c3025577dcf91c2fee2f298a27997a4295c818068fc46405c11dd003aa，脚本退出0/BSP_DMA_BOARD_ACCEPT_COMPLETE_NO_MOTION；metadata记录来源脚本、参数及收发字节。原始日志dma-board-accept-20261013-01.log、dma-idle-20261013-01.log、coldboot及.json保留；结构化dma-board-result-20261013.json由summarize_dma_board.py检查444条记录/场景/标记/IRQ/epoch。此前恢复失败原始证据保留，不改写为成功。

本批独立回环、受控双向恢复与GP回归目标通过。未接运动FIFO/电机；记录格式/包边界、持续吞吐/调度裕量、真实运动顶层时序/CDC/复位、欠流/STOP与停止排空需联合验证。物理DDR电压/颗粒/速度等级、长时DDR/CMA/存储压力未测。专用client双通道独占/同步串行提交及失败时quarantine规则保持，不宣称任意并发消费者/hot-remove安全。eMMC未操作。

当前暂停检查点：恢复修正版镜像afa13b14...420050d/根a3d29e67-02已经Windows完整写入/读回通过，尚未启动。用户因额度要求暂停；未打开第二次COM4采集。以下首版失败及通过项保留，不替修正版作通过结论。

## 2026-10-12 独立DMA首版：正常传输通过，恢复失败

Windows部署镜像6be6b27d...7617897，完整512MiB无缓存读回通过；用户装卡后COM4在115200/8N1、DTR/RTS=false采集完整FSBL→U-Boot→Linux，19009B，SHA2563721127e888ae430465f5943d69fd96c2210226fe50470ad952d795968470e41。FSBL bit生成20:51:00/HPF导出20:53:02、DDR1024MB/1333Mbps、SD来源及PL加载；Linux根PARTUUID a1604a87-02、实际mmcblk0p2/sysfs SD、1GiB/128MiB CMA及匹配内核/config/module/app/DTS门禁通过。原始证据evidence/dma-coldboot-20261012-01.log及.json。

GP VERSION1/CAPSf/FEATURES7/TICK_HZ1MHz，41项检查通过。DMA simple/32bit mask/BTT16及两通道绑定；17种长度×4模式×3轮共204正常回环、1043976B逐字节比较及guard通过，双回调各1次。GIC115/116 Level两路各204次中断，Err0。提交7.890–16.170μs，提交至IRQ完成17.190–103.620μs、均值25.317μs；按总payload/累计完成时间计算202.136MB/s，仅此测试口径，不是持续总线或运动链吞吐。

首个65535B S2MM无MM2S场景实际在途，预期超时后RX terminate等待HALTED超时：rx=-110、tx=0、pair post=-16，quiescent=0、errors=2/timeouts=1；程序退出1，DMA_ACCEPT_FAIL。coherent缓冲区与模块引用保留，无卸载/释放/重用。后续仅采集IRQ/dmesg/modules并运行GP41项，全部通过；证据dma-failure-diagnostics-20261012-01.log。发送无接收/显式在途terminate、异常后正常传输、buffer释放重分配及完整epoch比较未执行，不能报告恢复通过。解析结果见dma-first-board-result.json，原始验收日志SHA256292bf8ddab838a76b6a008d20bca98fc7193fe17fe0362a80e31b087663adbb0。

停止流程修正候选仅在bsp,loopback-pair simple专用域采用controller reset，并在释放任何当前描述符前确认两硬件方向HALTED和RUNSTOP/RESET清；client仍须双向terminate_sync、IRQ/tasklet/队列检查及延迟buffer稳定性后才允许释放。修正版构建/镜像和再次实板验收另记录，不以候选修正覆盖首版失败事实。运动FIFO/电机未接入。

2026-10-12 GP批次：最终GP镜像构建与SD完整读回通过，用户装卡上电后采集FSBL→U-Boot→Linux日志。SD根20ae01e9-02、1GiB和128MiB CMA确认，GP/IRQ/空闲四轴快照41项验收通过。实际范围见[gp/BUILD_STATUS.md](gp/BUILD_STATUS.md)。

用户曾因板卡不在手边结束任务，提交eb68206时尚未板测；随后明确装卡、接串口并上电，以下新增证据替代该历史NOT_TESTED状态。原PS-only结果单独保留。

## 2026-10-12 GP新镜像：一次冷启动和首轮验收

- COM4 115200/8N1、DTR/RTS=false；就绪后由用户上电，无自动复位或串口控制线切换。FSBL识别SD（mmc@0xf8049000/MSSD0）、读取1:/BOOT.bin并加载PL、释放GP common reset0；U-Boot读取boot.scr/DTB/kernel，Linux成功进入登录。Boot模式文字EMMC or SD本身不作为来源证据，结合明确SD识别和文件加载记录。
- Linux6.1.111-rt42-bsp-sd1、Buildroot2022.02.6；根mmcblk0p2、179:2、EXT4，sysfs type=SD，PARTUUID20ae01e9-02。Linux物理映射1048576KiB，MemTotal1013516KiB，CmaTotal131072KiB；只证明映射/预留，不是DDR/CMA压力验收。eMMC mmcblk1枚举但未挂载，未修改。
- 配套.config SHA256、模块/测试程序SHA256及vermagic门禁通过后显式modprobe bsp_gp。设备窗口0x80400000/4KiB，VERSION1/CAPS0xf/FEATURES0x7/TICK_HZ1000000匹配。树外模块taint提示为本次已知来源。
- gp-accept退出0、GP_ACCEPT_PASS checks=41：4种scratch写/读，软件拒绝运动opcode，NOP/SNAPSHOT应答及重复缓存保持、快照ID/valid一致性、空闲四轴0/invalid/NOT_READY状态、时间戳推进。20177tick/host0.020199秒只做粗略1MHz合理性检查。
- IRQ mask锁存、持续源W1C保持、poll唤醒、清源后W1C清除、无风暴、retrigger及ACK IRQ通过。实板Linux IRQ24/GIC INTID114（SPI82）、Level，验收结束计数3，Err0。命令/快照事件不表示运动完成；空闲快照不证明动态运动源原子性。
- 原始日志evidence/gp-coldboot-20261012-01.log、gp-board-accept-20261012-01.log；旁边JSON保存原始字节SHA256和串口参数，gp-board-validation.json汇总。冷启动接收被中断后重建元数据，明确未执行原finally；接受测试日志正常保存元数据。原始字节和终端回显不改写。

尚未验证：反复冷/暖启动、长期存储/DDR/CMA、实物DDR1.35V/颗粒/速度等级、动态快照、运动DMA/HP0/CDC、实际运动和实体电机。结束时串口关闭，模块保留加载，测试文件关闭清源/屏蔽；未进行自动重启、DMA或电机操作。

## 历史：2026-10-11 PS-only基线

2026-10-11（Asia/Taipei）。用户确认板卡从SD启动、COM4可进入后，通过COM4/115200/8N1连接，DTR/RTS=false。收到root shell；本次没有重启、加载模块、MMIO访问、DMA/内存压力或主动存储写测试。运行系统自身的rw挂载不等同只读挂载。

## 已确认

- Linux `6.1.111-rt42-bsp-sd1 #1 SMP PREEMPT`、Buildroot2022.02.6，双核上线。
- cmdline为`root=PARTUUID=d0e414b9-02 rootwait rootfstype=ext4 rw`；实际根为`/dev/mmcblk0p2`、179:26、EXT4；sysfs父设备type=SD、name=MSSD0、61132800扇区。eMMC为mmcblk1/IS008G，根未进入eMMC，eMMC分区未挂载。
- Linux物理内存范围0x0–0x3fffffff，启动日志1048576KiB；MemTotal=1013516KiB。128MiB CMA位于0x17c00000，CmaTotal=131072KiB、CmaFree=130656KiB；只确认预留成功，未验证DMA/CMA压力分配。
- `/proc/config.gz`解压内容SHA256为`81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1`，与交付debug/kernel.config完全一致。CONFIG_PREEMPT=y、PREEMPT_RT未启用、MODVERSIONS=y、ANLOGIC_DMA=m、AXI_DMA=y、AXI_DMA_TEST=m及UIO配置符合构建。
- anlogic-dma-engine和axi-dma-test位于本次kernelrelease目录，vermagic均为`6.1.111-rt42-bsp-sd1 SMP preempt mod_unload modversions aarch64`。仅查询modinfo，/proc/modules为空；未验证模块加载与硬件传输。
- SD与eMMC均由SDHCI/ADMA枚举，SD高速度模式；本次dmesg未见MMC timeout/CRC/I/O错误。PS AHB DMA枚举8通道，FPGA manager枚举fpga0；不作为PL AXI DMA/HP0成功证据。

## 脚本修正与证据

镜像中的bsp-readonly-check第一次在findmnt的MAJ:MIN尾随空格处失败，导致sysfs路径错误。源脚本改为移除空白，并增加根分区PARTUUID断言。修正版通过串口送入sh标准输入执行，退出0；没有覆盖板上文件或重打包已交付镜像。下次重建rootfs时纳入修正，当前卡上原脚本仍保留此问题。

原始串口日志：evidence/board-console-initial.log、board-readonly.log（失败）、board-supplement.log（完整dmesg）、board-readonly-corrected.log（成功及配置哈希）。

## 保留项

- QSPI日志`found gd25q256, expected gd25lb256e`：实际驱动识别32MiB gd25q256，工厂DTS声明尚有型号差异，未访问/写入QSPI；后续核对颗粒与声明。
- PS AHB DMA日志提示Device release未定义、运行中不安全unbind；本次未解绑。pl353-smc显示no matching children，未作为存储路径使用。
- 已在上电后进入控制台，未采集BootROM/FSBL/U-Boot阶段；用户报告SD启动和Linux SD根已确认，但首阶段来源/所用FSBL与PL bitstream尚缺完整冷启动日志。没有自动重启。
- DDR1.35V供电、具体颗粒、控制器训练及长期稳定性仍待实测。当前结果只验证Linux可使用1GiB映射和128MiB CMA预留。
- SD读写持久性、反复/冷启动、DDR/CMA压力、独立GP/IRQ/AXI DMA/HP0及CDC、运动100MHz时序验收仍未完成；HMI暂缓。
