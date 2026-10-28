# 硬件资料核对记录

2026-10-28三轴RS485地址补充：用户确认已设置为接收A0 STEP/DIR的驱动器=0xE0、A1=0xE1、A2=0xE2，与当前采集/安全联锁及HOME标定r2镜像一致。地址分配/设置不再待定；§14中的“实物地址待定”保留为历史。该结果为用户报告，本轮未读取驱动器或进行通信/运动；各地址应答及PL脉冲↔0x33↔0x30逐轴对账仍须实板记录，编码器符号/比例/机械参考不由此自动确认。无需为本次地址设置重建镜像。

2026-10-22当前规划：Wi-Fi STA连接路由器的局域网Web HMI为首版，HDMI/Qt暂缓。用户确认板卡没有可用的4G模块，4G扩展计划已移除；主线使用现有Buildroot核心BSP。§13中厂商4G资料和后续扩展表述保留为历史，不再构成项目待办。无线资料、配置差异和验证边界见§13。

2026-10-11后续实板补充：用户确认SD启动与COM4可进入，只读核对确认Linux6.1.111-rt42-bsp-sd1、根为SD mmcblk0p2/PARTUUID=d0e414b9-02、1GiB物理映射及128MiB CMA预留；运行.config哈希与交付匹配。完整冷启动FSBL/U-Boot、实物DDR供电/颗粒及压力/DMA/运动验收仍未完成，详见[bsp/BOARD_VALIDATION.md](bsp/BOARD_VALIDATION.md)。

2026-10-11 BSP构建补充：已在用户提供的Ubuntu18.04.4/x86_64虚拟机独立构建目录完成Buildroot最小SD文件镜像，详见[bsp/README.md](bsp/README.md)与[bsp/evidence/manifest.json](bsp/evidence/manifest.json)。后续经用户授权完成实体SD烧写，前512MiB直接读回哈希与镜像一致，FAT32/EXT4检查通过，详见[bsp/DEPLOYMENT.md](bsp/DEPLOYMENT.md)。未实板启动；本批未操作串口。厂商原始资料未改动。

- 当前TD2026.1 SP2重新生成PS-only bitstream与HPF，DDR配置1GiB/32bit/1333MT/s/1.35V，当前FD2026.1 SP1 Master SDK及BM GCC12.3.1实际重建FSBL。HPF默认DDR_INIT_V2，FSBL符号及反汇编确认包含生成的SoC_M90_DdrInit；HPF工具日志训练DONE不是板上训练证据。
- 同版本工具对照显示1.35V与1.5V的生成soc_plat.c完全相同，仅头文件电压参数不同；不能据电压字段宣称模拟配置或供电已验证，继续保留厂商语义核对、实测供电/颗粒/修订/训练项。不猜改PHY常量。
- 完整SD镜像512MiB，FAT32启动分区64MiB、EXT4根分区256MiB；root=PARTUUID=d0e414b9-02，启动脚本只接受SD控制器mmc0，不沿用eMMC root=/dev/mmcblk1p2。U-Boot禁用持久环境读取。BootROM首阶段来源仍待拨码与完整上电日志共同核对。
- 内核实际6.1.111-rt42-bsp-sd1、CONFIG_PREEMPT=y而PREEMPT_RT未启用，不能据-rt42后缀报告RT验收。CMA设备树128MiB、内存1GiB均已主机端检查，板端DDR/CMA/存储/驱动未验收。保存匹配.config、生成头、补丁、Module.symvers、System.map、vmlinux与FSBL符号资料。
- Anlogic DMA实际模块构建经补丁将框架与AXI实现合并，通过modpost；模块vermagic包含本次kernelrelease和modversions/aarch64。没有运动DMA节点和硬件，不将厂商以太网/显示DMA复用为运动DMA。
- 两次相同构建输入的SD打包哈希一致；未进行第二次独立全量源码重建比较。主机端文件系统/分区/哈希通过不等同实板启动通过。连续运动100MHz时序待验收，HMI暂缓，本批最小PL不集成运动。

核对日期：2026-10-06起；2026-10-08补充COM4实板运行快照（§11）；2026-10-09确认项目BSP按1.35V DDR电压基线开发（§10.3）。状态：资料与运行基线已核对；用户确认双核 ARM 平台、PS Linux；完整实物配置及项目接口尚未冻结。
资料根目录：D:\Works\Embedded_contest\docs\Analogic\hardware_MLK_F3P_CZ02_DR1_20250526。
本记录区分资料描述、原理图连接、实物待核实项；不能作为未经验证的接线或引脚约束文件。

## 1. 与 AGENT.md 的关系

保持既有职责边界：PS 承担任务、轨迹、插补、Delta IK、统一网络命令/Web HMI服务及诊断管理；PL 承担四轴 STEP/DIR/EN、运动安全响应、RS485 Master、时间戳与遥测采集。RS485 是三线控制的半双工总线。NPU 不直接控制执行器。
不生成 RTL、约束工程或冻结寄存器/报文格式。

用户已确认使用双核 ARM 平台。指定两份手册均将此选项对应到 MLK-CZ02-DR1M90 / DR1M90GEG400，配 MLK-F3P 底板，作为当前资料型号基线。用户进一步确认DDR3为1GB、32bit、1.35V、速率1333，eMMC为8GB、QSPI Flash为32MB；存储容量已确认。完整实物丝印/速度等级、存储颗粒型号及BSP时序/训练配置仍待核对。

## 2. 器件与资源

| 项目 | 资料描述 | 来源及待核实项 |
| --- | --- | --- |
| 核心板 | MLK-CZ02，底板 MLK-F3P | 支持多个选焊配置；实物型号、修订版待确认 |
| 主芯片选项 | DR1M90GEG400 / DR1V90GEG400 | 开发板手册 PDF p6、p8；不可仅凭资料包名称选定 |
| DR1M90 PS | 双核 ARM，手册标称最高 1GHz；ARMv8-A | 开发板手册 p6；UG1214 PDF p19；实际频率及速度等级待确认 |
| DR1V90 PS | 单核 RISC-V，手册标称最高 800MHz | 开发板手册 p6；实际工具链与 BSP 待确认 |
| PL | 94,464 LUT；104,960 DFF；280 个 20K ERAM（总计 5600Kbit）；1340Kbit DRAM；240 DSP；8 PLL；1 ADC | 开发板手册 p6、p8 |
| DDR | 用户确认1GB、32bit、1.35V；手册配置两片GDP2BFLM-WB、每片512MB | 用户确认及开发板手册p8-9；容量/位宽/电压已确认，具体颗粒与训练配置待核对 |
| DDR 速率 | 用户确认1333；统一按1333MT/s数据传输率记录 | 核心板参数表写1333Mbps，开发板另有“1333MHz”写法；不作为1333MHz CK，BSP控制器/PHY时钟与时序/训练参数待核对 |
| eMMC | 用户确认8GB；手册型号IS21EF08GA-JCLI，SD1，板级D0-D3四线、CLK/CMD；手册标称50MHz | 用户确认及开发板手册p11；具体颗粒型号/运行频率/启动镜像待核对 |
| QSPI | 用户确认256Mbit（32MB）；手册型号GD25Q256DYIGR，3.3V，x1/x2/x4 | 用户确认及开发板手册p10；具体颗粒/运行配置待核对，不把容量写成256MB |
| NPU | Hard NPU 512 MAC；最高 400MHz、400 GOPs，int8/uint8；Soft NPU 承担部分算子并访问 HP | UG1214 PDF p64-67（印刷 p47-50）；不能视为完全不占 PL/DDR 资源，模型工具链及资源预算待确认 |

### 2.1 指定硬件手册的资料基线

2026-10-06 按用户再次指定的 01_硬件手册 目录核对文字与参数表页面：
- MLK_CZ02_DR1核心板硬件使用手册.pdf：16页，p2版本表最新一项为V1.3 / 2024-09-27（兼容DR1）；p6为硬件配置，p7-8为处理器/PL/DDR，p10-11为Flash/eMMC/时钟。
- MLK_F3P_CZ02_DR1开发板硬件使用手册.pdf：25页，p2为V1.0，列核心板硬件版本2024-09-27、底板硬件版本2025-05-26；p6-7为整板参数，p12为PL时钟，p19为HDMI，p21为CAN/RS485，p23为GPIO，p24为电源。
- 开发板p6双核ARM主频栏写1000MHz（-2），只能记录其资料标称与条件，不将CPU运行频率或实物速度等级冻结为1GHz/-2。
- ARM缓存资料为每核32KB指令缓存、32KB数据缓存，512KB L2；核心板p5列可引出38个PS MIO和125个PL IO。125是核心板总引出资源，包含底板外设占用，不能当作125根空闲运动GPIO。
- 存储配置见上表；两份手册p5说明DDR/eMMC存在选焊配置，当前项目容量已由用户确认，不再列为容量待定。DDR速率1333统一按MT/s记录，手册的“1333MHz”写法不能直接用于时钟配置；具体BSP时序/训练参数及遗留ZYNQ名称继续保留核对项。

### 2.2 与当前项目有关的底板资源

| 接口 | 手册能力与连接 | 设计时需要核对 |
| --- | --- | --- |
| HDMI | 一路PL直接驱动输出，资料标称最高1080@60fps；p6、p19 | 显示时序、输出IP、DDR帧缓冲/带宽和实际显示器；不是本项目刷新率已冻结 |
| RS485 | 一路，PL BANK33、3.3V；管脚见§4 | 半双工换向、总线电阻及驱动器转换模块 |
| 普通GPIO | J12，2×13、2.54mm，24根信号；p23 | 当前3.3V运动候选；2.00mm排线转接/输入数量见§5、§8 |
| FEP | 48根IO/24对差分；p6、p22-23 | BANK32可调电压、子卡与连接器，不能默认与J12电平相同 |
| 调试/启动 | UART+JTAG Type-C；TF卡与QSPI/eMMC启动资源；p6、p13、p16、p18-19 | PS/PL串口区分、当前启动介质与驱动；预留TF1与eMMC资源有关，不能当作独立已安装存储 |
| 以太网/辅助设备 | PS和PL各一路千兆网；USB2.0、EEPROM、RTC、LED/按键；p6 | 仅记录可用资源，启用时核对引脚复用与驱动；板级RTC不替代PL统一时间戳 |

HDMI高速输出对经手册p19和管脚表核对为D2=D19/D20、D1=F16/F17、D0=M14/M15、CLK=K17/K18。DDC/热插拔辅助信号的资料差异见§7；此记录不直接生成约束文件。

## 3. 时钟、电源、复位与启动

- PS 参考时钟：33.333333MHz，核心板 X1，PS_CLK=E7。
- PL 板载参考时钟：100MHz，底板 X1，H16，BANK33，手册 IOSTANDARD=LVCMOS33；用户已确认采用该100MHz输入作为PL基础时钟。时间戳已确定为64位无符号数，每次PL上电初始化完成后从0开始累加；计数频率/单位、初始化完成条件、采样标记、回绕、软复位/PL重配置及跨域读取仍待定，不默认100MHz每拍加1。运动周期与其他时钟域仍未冻结。
- BANK11：核心板固定 3.3V。BANK32：VCC_ADJ1，可调。BANK33：VCC_ADJ2，在本底板原理图接 3.3V。
- 底板原理图 p3 明确 VCC_ADJ 默认发货 1.8V；开发板手册 p5 又写 BANK32 默认 3.3V。实际跳线与电压必须核实，不能直接冻结 BANK32 为 LVCMOS33。
- 核心板输入 5V；底板输入 12V。手册 p6 写底板 12V@3A，p24 写配套电源 12V/2A；电源规格以实物适配器与负载核对。
- 上电复位 TPS3106；外部复位 PS_SRST_B 由底板复位按键控制。PL 内部复位、各时钟域释放与运动输出默认状态仍待设计。
- 启动拨码按手册 SW1/SW2/SW3 顺序：JTAG=000；QSPI=001；SD=011；eMMC=111。ON=0，OFF=1。实物丝印与当前启动介质待核实。

来源：开发板手册 p11-13、p24；核心板手册 p6、p11-13；核心板原理图 p5；底板原理图 p3。

## 4. 通信接口

| 信号 | 芯片球位 | 电平与方向 |
| --- | --- | --- |
| PL_CLK | H16 | 输入，100MHz，3.3V |
| RS485_TX0 | L17 | PL 输出，3.3V |
| RS485_RX0 | N16 | PL 输入，3.3V |
| RS485_DE0 | N15 | PL 输出；0 接收、1 发送 |
| PL_UART_TX | J16 | PL 输出，3.3V |
| PL_UART_RX | K16 | PL 输入，3.3V |
| PS_UART_TX/RX | MIO48 / MIO49 | PS 调试串口；不可套用 PL 的 3.3V 约束 |

- RS485 U21=SP3485EN-L/TR；DE 与低有效 /RE 共同接 N15。板上 R120=120Ω 跨 A/B，原理图未显示终端跳线或可切换控制，也未在 p14 显示独立外部偏置电阻。
- J11 本项目使用的RS485接线：4=GND、5=RS485 A、6=RS485 B；接线前核对实物针序和设备 A/B 定义。其他针脚不作为本项目已分配接口。
- 固定终端电阻影响共享总线拓扑；确认控制板是否处于总线端点、从机终端与线长。
- N16、N15、F19、F20、J16、K16 是 ADC 复用 IO，见核心板原理图 p4。硬件手册要求避免将这类 IO 用作高速 IO；实际通信速率及 IO 性能需按器件工具配置验证。100MHz 输入 H16 不属 ADC 复用组。

来源：开发板手册 p12、p16、p21；底板原理图 p3、p14；核心板原理图 p4；PL-RS485 管脚表 A3:C5；UG1214 PDF p34。

## 5. 四轴输出及输入的候选扩展接口

J12：2×13、2.54mm GPIO，24 根信号引至 DR1 BANK11，固定 3.3V；底板原理图 p16 信号通路有 33Ω 串联电阻。
p16 显示 VCC_CEP1 默认通过 L13 接 3.3V，5V 路径 L11 标 NC；这仅描述连接器电源针，不表示 GPIO 可承受 5V 或工业电压。

| J12 针号 | DR1 球位 | J12 针号 | DR1 球位 |
| --- | --- | --- | --- |
| 1 | VCC_CEP1 | 2 | GND |
| 3 | Y12 | 4 | Y13 |
| 5 | T9 | 6 | U10 |
| 7 | T5 | 8 | U5 |
| 9 | V6 | 10 | W6 |
| 11 | U7 | 12 | V7 |
| 13 | U9 | 14 | U8 |
| 15 | V11 | 16 | V10 |
| 17 | Y7 | 18 | Y6 |
| 19 | Y9 | 20 | Y8 |
| 21 | V8 | 22 | W8 |
| 23 | W10 | 24 | W9 |
| 25 | W11 | 26 | Y11 |

J12 可作为十二根 STEP/DIR/EN 的候选接口，尚未分配轴号。其余 GPIO 能否容纳 Homing、Limit、Alarm、急停，取决于输入数量及外部接口板设计，不视为已够用。

2026-10-13 示波器隔离测试补充：用户集中确认下表测试映射、J12 实物针1标记/针2=GND 的针序核对、九针无其他占用及仅接示波器、不接驱动器/电机条件。A0..A2 是运动内核测试轴，不冻结为最终 M1..M3 机械映射；M4 禁用且不绑定 IO。原 GPIO 总表、底板原理图 PDF p16 的连接器/33Ω串阻，以及核心板 PDF p4 的 DR1_400P BANK11 球位、p6 的 VCCIO_11=3.3V 已相互核对。实物 speed 未确认，构建继续明确使用参考 speed2；此次不下载、不改 BSP 或启动镜像。

| 测试轴 | STEP（J12针/球） | DIR（J12针/球） | EN（J12针/球） |
| --- | --- | --- | --- |
| A0 | 3 / Y12 | 4 / Y13 | 5 / T9 |
| A1 | 6 / U10 | 7 / T5 | 8 / U5 |
| A2 | 9 / V6 | 10 / W6 | 11 / U7 |

以上均为 BANK11/LVCMOS33；J12-2用于示波器共地，J12-1是电源针，不接探头地。独立 scope-test 参数为100MHz、STEP高/低及DIR/EN建立/保持/失能各5μs、最高STEP100kHz、测试EN高有效，不能视为SERVO42C或产品参数。维护REBASE到[-1090,-1090,-1090]仅初始化无电机测试命令坐标，不能称为机械回零。RTL端口和交接见 `pl_motion/GPIO_HANDOFF.md`；原理图/表格核对与用户确认不代替实体输出电压、脉宽或线缆针序的实测。
U23 FEP：48 路 IO/24 对差分，DR1 BANK32，可调 VCC_ADJ；管脚表保留了 Zynq BANK34 的旧网络名，实际 DR1 BANK32 对照表已确认。输出电平、子卡供电和连接器选型待确认。

来源：PL-GPIO 连接器管脚表 A1:K16；PL-FEP 连接器管脚表；ZYNQ&DR1_BANK 对应表；底板原理图 p15-16；核心板原理图 p4。
手册“BANK11 为7020独有”的文字与 DR1 核心板原理图及管脚表不一致，不能据此否定 J12 的 DR1 BANK11 连接。

## 6. PS/PL 互连资源

- UG1214 PDF p34-35、p72-73（印刷 p17-18、p55-56）：2 路 PS GP master、2 路 PS GP slave、2 路 HP slave；M90 有 ACP，V90 对应 FAHB。
- GP 数据位宽 32bit；HP 支持 32/64bit，PL master 可通过 HP 访问 DDR/OCM；ACP 为 M90 专有、64bit。
- PS/PL AXI 接口是异步时钟关系，CDC、复位和缓冲行为需明确。
- 文档写支持 AXI4，但 A*Len 位宽为 4bit；不要直接套用未经确认的其他 FPGA 厂商 AXI/DMA IP。
- 用户已确认通路方向：GP上的AXI4-Lite寄存器负责控制/状态；轨迹与遥测由FIFO缓存，经HP/DMA访问DDR。已找到GP/中断、HP0双向DMA示例及Linux DMA源码（§10）；具体IP、端口、内部流接口、地址、点/遥测格式与DDR ring buffer结构仍未冻结，等待候选选型与验证。
- 用户已确认PS→PL使用四轴绝对目标步数，PL内部以已输出STEP累计的命令位置为基准计算剩余增量执行；命令位置不等同编码器实测位置。数值位宽、坐标原点、初始化及中断恢复行为仍未冻结。
- NPU 软核与遥测 DMA 可能共享 PL/HP/DDR 资源，需要资源与带宽预算。

## 7. 资料冲突及版本问题

1. BANK32 默认值：手册 p5 为3.3V，底板原理图 p3 为1.8V；等待跳线与实测。
2. BANK11：手册出现“7020独有”，DR1 原理图与型号对照表明确有 BANK11；按完整器件与工程核对。
3. KEY1/KEY2：手册 p21 为 K14/J14；Excel 表为 K19/J19。底板原理图 p3 显示 J20、R528/R529 可把 K19/J19 按键网络联到 K14/J14，而 K14/J14 同时承担 PL Ethernet MDIO/MDC。不能只择一管脚，须确认 J20 与功能复用。
4. PL LED1/LED2：表中 T19/R19 电压为 ADJ（BANK32），手册统一写 LVCMOS33；随 VCC_ADJ 核实。
5. 部分手册/网络名仍用 ZYNQ、BANK13/34/35、BANK501；依据 DR1 对照表和原理图转换，不复制旧约束。
6. 文件名不是精确的页内版本：底板 p3 日期为2025-11-05，核心板 p4 为2025-04-16，目录名仍含20250526；与实物修订匹配后再冻结。
7. 版本说明 txt 写 PLETH RX/TXDLY 修改为上拉；以后启用 PL 以太网时应核对对应 PHY 初始化。
8. 两份手册覆盖存储选焊配置；当前项目容量已由用户确认为1GB DDR3、8GB eMMC、32MB QSPI Flash，DDR3速率1333MT/s。仅具体颗粒丝印/控制器配置待核对，不继续把容量列为未确认。
9. HDMI辅助信号：开发板手册p19与底板原理图p11一致为FSCL=E18、FSDA=E19、FHP=G20；PL-HDMIO管脚表Sheet1的A12:B14却列FHP=E18、FSDA=E19、FSCL=G20。实际实物/示例约束核对后再冻结，不能直接复制Excel的FHP/FSCL分配。该电路有电平转换/热插拔相关器件，不将连接器侧5V直接视为PL输入电平。
10. DDR IO电压：已查Linux/培训示例HPF设DDRC_IO_VOL=1.5，当前用户/手册基线1.35V；不能原样复制初始化参数。详细来源、工具/时钟及软硬件地址差异见§10.3。

## 8. 本机软件与外部驱动器资料线索

用户已确认 PS 采用 Linux；2026-10-06按用户指定路径核对到对应DR1M90G的板级示例、启动镜像、设备树及完整Linux构建包，详见§10。BSP资料已具备，不再列为等待用户提供。本机查询日期2026-10-06：

| 工具 | 检查结果 | 证据 / 路径 |
| --- | --- | --- |
| TangDynasty | 2026.1 SP2，发行说明构建号 6.2.2 200067 | PATH 解析到 D:\Anlogic\TD_Release_2026.1_SP2.200.067\bin\td.exe；该目录 doc/release_note.pdf p5 |
| FutureDynasty | 2026.1 SP1 | PATH 解析到 D:\Anlogic\FD_2026.1_SP1\fd.exe；该目录 doc/FD_Release_Notes.pdf p3 |
| Icarus Verilog | 12.0 (devel)，s20150603-1539-g2693dd32b | D:\iverilog\bin\iverilog.exe -V 实际运行成功；vvp 同在该目录 |
| FD 内置 Master SDK | 发行说明列 BM_2026.1.sp1.release，commit 69adfad1；SDK 目录存在 | D:\Anlogic\FD_2026.1_SP1\data\embeddedsw\master_sdk；尚不替代用户板级 BSP |
| FD 内置 Linux 交叉 GCC | 文件存在，发行说明列 Linaro GCC 7.4.1；当前直接运行 --version 失败 | D:\Anlogic\FD_2026.1_SP1\toolchain\gcc\aarch64_linux\bin\aarch64-linux-gnu-gcc.exe；Windows 返回“无效的系统 DLL 重定位”，不能标为可用 |

此次只查询版本/安装内容，没有运行 TD/FD 工程、检查许可证、编译硬件工程或验证板级兼容性。
厂商构建包的Linux/U-Boot/Buildroot版本及板级文件已核对，项目最终采用版本和部署方式尚未冻结；工作站Linux/虚拟机是否可用、交叉编译器实际运行与NPU运行库继续待验证。包内另有Linux主机用的aarch64交叉工具链，其存在不代表已经安装或运行成功。保留Windows版GCC启动失败记录，不在本任务内擅自修复安装环境。

用户于2026-10-06补充的执行器与接线约束：
- M1-M3 暂定 Makerbase MKS SERVO42C，计划采用 TTL 版本并各自加装 TTL↔RS485 模块。具体硬件/固件版本与转换模块型号待确认。
- M4 驱动器与机构尚未确定，不阻塞当前需求整理和四轴通用接口设计；不得假定 M4 与前三轴使用相同协议，也不得将其未接入状态视为第四台在线从机。
- STEP/DIR/EN 电平3.3V；验证阶段使用杜邦线，后续计划使用2.00mm排线。J12本身为2.54mm，2.00mm排线的转接与针序尚待设计。
- 需要在 STP 脉冲运动期间通过 RS485 轮询状态。这是用户要求，尚未证明实际固件的并发兼容性与时序性能。
- CHECKSUM-8 已由用户确定，按参与校验的帧字节累加后取低8位；p11示例为 (0xE0+0x30)&0xFF。帧边界/校验覆盖范围及字节序仍需在协议规范冻结，不假定 Modbus RTU。
- TTL↔RS485 模块必须支持3.3V逻辑及一主多从半双工；DE/RE控制或自动换向、末字节发送完成到总线释放延迟、终端/偏置、掉电与失能状态的总线占用待确认。

本地 V1.1.2 手册核对（来源：docs/MKS-SERVO42C/User Manual/MKS SERVO42C User Manual V1.1.2.pdf）：
- p8：CR_vFOC 是闭环脉冲接口模式，CR_UART 是串口控制模式；模式配置与实际固件待验证。
- p9：Protect 堵转自保护默认 Disable，启用后检测堵转会释放电机。应在配置与验收中明确启用/回读/堵转试验；不能将默认关闭的能力视为已生效。
- p12-13 提供编码器、已接收脉冲数、角度误差、EN状态、保护状态等查询；轮询项目、频率与阈值未冻结。解除保护命令是状态改变命令，不属于正常轮询。
- p25：0xF3 串口使能命令位于要求 CR_UART 的章节，不能未经验证用于当前 STP 模式的恢复过程。

安全职责由用户确认：SERVO42C 负责单轴闭环与堵转自保护；FPGA PL 负责 Delta 整机回零、限位、联锁和停止策略；外部电路负责最终急停失能。具体安全输入、故障门槛和响应时间仍待冻结。

重新使能风险已核实：[Makerbase V1.1 release note](https://github.com/makerbase-mks/MKS-SERVO42C/releases/tag/MKS-SERVO42C-V1.1)。其描述失能后手动从A转到B，再使能时若脉冲/角度参数未正确处理可能回到A，并说明固件重新使能时清零参数。这是特定版本及串口命令情境，不证明当前待选固件/EN引脚路径行为相同。
恢复规范必须覆盖驱动内部目标、控制器坐标、当前位置可信性及待执行轨迹的一致性；清除驱动内部参数不等同 Delta 已完成机械回零。用户明确暂不冻结人工确认或自动恢复的具体策略，先记录风险和验证要求；具体命令和顺序须按实际固件试验。

用户确认同步验收指标为对应STEP边沿偏差＜50μs；对应边沿映射和测量位置尚待冻结。经讨论，用户同意将当前Delta功能明确为“PL确定性多轴同步执行与脉冲分配”；固定比例主从电子齿轮移至M4或外部跟随任务明确后的扩展评估。

## 9. 待用户确认

完整器件/板卡版本、具体存储颗粒与BSP时序/训练配置（特别是示例DDR IO电压1.5V与当前记录1.35V的差异）；已有Linux BSP/设备树的项目适配与可用构建环境；外部接口板、2.00mm转接与实际针序；
驱动器固件/转换模块、脉冲与串口并发兼容性、协议剩余字段与时序；无线接入与Web接口；
对应STEP边沿的匹配规则及测量位置、脉冲分配算法、负载验收范围、回零/限位/报警/急停输入与停机/恢复策略；
AXI/点/遥测/DDR格式；时间戳计数频率/单位、初始化完成条件、采样标记、回绕、软复位/PL重配置及跨域读取（64位无符号与上电初始化后从0累加已确认）；寄存器/错误码/配置管理、生成文件边界；竞赛时间。
项目功能目标与用户确认状态统一见 PHASE0_CONSTRAINTS.md。

## 10. 厂商示例与Linux BSP核对

核对日期2026-10-06。用户指定资料根目录 `D:\Works\Embedded_contest\docs\Analogic\03_demo` 与 `D:\Works\Embedded_contest\docs\Analogic\04_培训demo`。本次只读检查工程、源码、HPF内部配置、镜像文件和压缩包内容；未解压落盘、执行厂商脚本、编译或烧写。

结论：已有资料足以支持当前Phase 0接口研究和板级启动开发，不再等待另行提供BSP。可重复构建、实板启动、DDR稳定性及本项目数据链性能仍需验证；示例参数不自动成为项目冻结参数。

### 10.1 资料索引与用途

以下相对路径基于 `D:\Works\Embedded_contest\docs\Analogic`：

| 资料 / 示例路径 | 已检查内容 | 本项目用途与限制 |
| --- | --- | --- |
| `03_demo\3-4_ex_soc_linux\01_ex_linux_base_F3P_DR1M90G\Linux Base Appendix\Chapter 3` | `soc_prj/system.al`、`soc_hw/system.hpf`、FSBL源码/SDK、kernel/uboot两组DTS；`boot`内有BOOT.bin、boot.scr、system.dtb、uImage.lz4、uInitrd.lz4 | Linux启动和TD→HPF→FD/FSBL→系统打包参考；镜像存在，未证明能在当前实板启动 |
| `03_demo\3-4_ex_soc_linux\02_ex_linux_drive_F3P_DR1M90G\Sourcecode` | 1–23章工程；包含设备树平台驱动、MISC、输入/中断、Timer/Watchdog、RTC/UART/I2C、文件读写、阻塞/非阻塞/异步IO | Linux驱动与日志/事件通知参考；章节示例互相独立，不能直接当作一套已集成系统 |
| 上述Sourcecode下 `16.plint`、`17.axi_gpio` | PL中断platform_driver与request_irq；AXI GPIO驱动ioremap/ioread/iowrite；DTS及硬件工程 | GP寄存器和PL→PS事件通知参考；GPIO示例硬编码0x80000000/0x80100000等地址，不复制为机器人寄存器地址 |
| 上述Sourcecode下 `19.axi_uartlite` | 独立PL UART-Lite工程、DTS及Linux串口应用 | UART/IP接入参考，不替代PL RS485 Master的轮询、DE、CHECKSUM-8与时间戳逻辑 |
| `03_demo\3-2_ex_fpsoc\3_2_01_sdk_base\17_axi_DMA` | `soc_sdk/axidma_s2mm_mm2s/main.c`中S2MM/MM2S及HP0↔DDR↔AXI-Stream；包含DMA IP和硬件工程 | 通用轨迹下发/遥测回传的优先研究候选；当前应用是裸机HAL，不直接作为Linux驱动 |
| `03_demo\3-2_ex_fpsoc\3_2_02_sdk_adv` | 有03_pl_fdma、04_pl_fdma_video_1080P等工程目录 | FDMA与显示相关补充索引，未逐一验证所有工程 |
| `04_培训demo\01_fdma_vdma_20251010` | 六组：fdma_test、fdma_imx415、fdma_video_tpg、fdma_vdma_adc、fdma_vdma_imx415、fdma_vdma_tpg | 数据采集、DDR写入与HDMI帧缓冲参考；日期为20251008/20251010的具体工程名按原目录保留 |
| 上述培训包下 `fdma_test_20251008`、`fdma_vdma_tpg_20251010` | `soc_prj/*.al`、`soc_hw/soc_prj.hpf`、SDK main.c；TPG程序设置1920×1080@60、三帧地址及VDMA中断 | SDK裸机示例，FB_BASE_ADDR=0x10000000，每帧间隔0x02000000。Linux内不能假设这些物理地址空闲；须按DMA/CMA/保留内存方案适配。源码与HPF的VDMA/VTG地址还有需核对的差异，不复制零散常量 |
| `uisrc-lab-anlogicM-V4.0.1.tar.gz`（Analogic根目录） | 只读完整遍历152407个tar条目，检查关键源码/配置/脚本；包含sources、boards、scripts、tools | 对应DR1M的完整Linux构建参考包；无须把大量厂商文件拷入本项目Git |

### 10.2 构建包的可复核基线

压缩包内部根目录为 `uisrc-lab-anlogic/`：

- `sources/linux/Makefile`：Linux **6.1.111**；`sources/u-boot/Makefile`：U-Boot **2021.01**；`sources/buildroot/Makefile`：Buildroot **2022.02.6**。这些是该包源码版本，不推定每个旧demo的预编译镜像或当前实板正在运行相同版本。
- `scripts/drcfg.sh`默认选择DR1M与Buildroot。包含rootfs、U-Boot、kernel、镜像生成脚本；`boards/DR1M/configs/defconfigs`含三者的板级defconfig，另有TF FAT/EXT4、HDMI、Qt启动参数文件。
- `tools/aarch64-linux/bin/aarch64-linux-gnu-gcc`存在，文件头为64bit x86-64 ELF，是Linux主机工具，不是Windows exe。Buildroot defconfig选择外部GCC 7、glibc、C++；尚未运行版本查询或编译。
- `boards/DR1M/configs/defconfigs/anlogic_dr1_buildroot_defconfig`配置Qt5 GUI/Widgets及CPIO/LZ4根文件系统选项。Qt配置存在不等同HDMI HMI已经实现。
- 内核有 `drivers/dma/anlogic/{anlogic_dma.c,axi-dma.c,axi-dma-test.c,axi-vdma.c,axi-vdma-test.c}`。测试代码使用dma_request_chan、dma_alloc_coherent和DMAengine；已有Linux DMA源码参考，不必从零编写整套DMA驱动。该目录Makefile使用CONFIG_ANLOGIC_DMA/AXI_DMA/AXI_DMA_TEST/AXI_VDMA等开关，检查的DR1M kernel defconfig未出现这些开关；集成时须核对Kconfig依赖、最终.config、DTS、IP版本和中断。
- DR1M kernel defconfig已有CMA/DMA_CMA、UDMABUF、PL GPIO/UART-Lite及帧缓冲相关配置；项目DMA缓冲所有权、cache同步、映射和ring buffer仍待接口设计，不能只据功能开关认为一致性已解决。

来源教程：Linux基础入门篇PDF p17–24说明HPF、FSBL、系统打包和TF启动；p17指定TD_6.2.1_Engineer_168116与FD_2025.1_SP1。

### 10.3 适配前必须核对的差异

1. **DDR电压**：Linux Chapter 3的 `system.hpf`、培训fdma_test和fdma_vdma_tpg的 `soc_prj.hpf` 内 `HPFs/static/data/ddr.js` 均为DDR3、1333Mbps、32bit、x16/4096Mbit、DDR3_1333G、training=1，但 **DDRC_IO_VOL=1.5**，与当前用户/手册基线1.35V不一致。保留项目已确认配置并标注差异；核对实板颗粒、供电和当前工具对该参数的含义后，再生成匹配的PS初始化，不能原样烧写或未经核对只改显示值。
2. **工具版本**：Linux示例system.al记录6.2.168116，AXI DMA示例6.2.170161，培训工程6.2.175876，均早于本机TD2026.1 SP2。Linux HPF还标注version=202501、生成时间20250812。教程/工程/HPF不是严格同一时刻快照；迁移时需恢复/重生成IP、重新导出HPF并匹配FSBL/bitstream/DTS，而非只打开旧工程即宣称兼容。
3. **时钟**：核对的Linux HPF报告p2f_clk0=49.995MHz；培训TPG HPF的VDMA输入133.32MHz、VTG输入49.995MHz。项目已确认100MHz PL基础时钟不变，AXI/显示域与100MHz运动域的CDC/复位另行设计，不把demo所有时钟直接替换为100MHz。
5. **DMA与显示**：通用AXI DMA和厂商uifdma/视频VDMA属于不同候选；后者帧切换语义不直接成为运动点消费语义。训练TPG源代码写入地址与HPF摘要有差异，后续以重新生成的一致硬件/软件定义核对。具体IP选型和Linux应用API本次未冻结。

建议下一步验证顺序：匹配板级配置与工具→可重复Linux启动→GP寄存器与PL中断→通用AXI DMA双向回环→在该基线上接入运动FIFO/遥测。HDMI、CAN和NPU另按各自接口验证；当前任务仅完成资料核对。

2026-10-09 DDR电压决策与证据补充：

- **用户明确决定：本项目按1.35V开发BSP。** 后续TD/FD板级配置应选择1.35V，并核对重新导出HPF中的`DDRC_IO_VOL=1.35`及所生成DDR控制器/PHY初始化参数；重新生成匹配的PS初始化/FSBL，不仅修改HPF报告中的显示值。本次只更新记录，尚未修改工程、生成BSP或烧写镜像。
- 原理图依据：`02_原理图/MLK_CZ02_DR1_240926.pdf`的P11_POWER中，U8=MP2143DJ，R31=200kΩ、R32=160kΩ，标称输出`0.6×(1+200/160)=1.35V`，网络名`DDR_1V35`；P07_DDRX2_PS两片DDR的VDD/VDDQ与P06_BANK_PWR的SoC DDR I/O供电使用该网络。资料按1.35V设计，仍需核对实物修订与颗粒。
- 示例差异可复现：二次开发`01_start/02_start_Linux/04_secondary_developmemt/demo/soc_hw/system.hpf`、Linux基础Chapter 3的`system.hpf`、培训fdma_test与fdma_vdma_tpg的`soc_prj.hpf`均已重新只读检查；HPF为ZIP格式，内部`HPFs/static/data/ddr.js`第23行字段`DDRC_IO_VOL`、第24行值`1.5`。这是厂商示例配置证据，不是实板模拟电压读数，不能据此改用1.5V。
- **实测状态仍为未测量。** §11串口采集未确认DDR供电电压；2026-10-09复查串口时主机找不到COM4，未取得新板端证据。后续可核对核心板C115/C116非GND端对地电压及颗粒丝印；两片DDR3L支持双电压并不等同现有板卡可仅靠软件任意切换供电。

### 10.4 厂商二次开发系统与SD启动路径

2026-10-08按用户指定位置只读核对：`D:\Works\Embedded_contest\docs\Analogic\01_start\02_start_Linux\04_secondary_developmemt`。目录实际拼写为developmemt，保留原路径。包含8页二次开发Buildroot教程、demo.zip及已展开demo。

- 教程p1–5给出TD导出包含bitstream的HPF、FD由HPF建立平台并编译soc_fsbl；p6要求将soc_fsbl.elf、system.bit和kernel-dts/uboot-dts放入Linux构建环境boards/files；p7给出move_files、rootfs/U-Boot/kernel构建及create_image流程；p8为SD启动拨码ON-OFF-OFF。示例system.al为DR1M90GEG400/-2、TD6.2.168116。
- `demo/boot`实际包含BOOT.bin、boot.scr、system.dtb、uImage.lz4、uInitrd.lz4；不是仅有一个根文件系统。kernel DTS声明1GB内存、128MB CMA，并include构建包中的anlogic-dr1m90.dts；新增PL外设仍需匹配设备树、驱动、地址、中断与时钟/复位。
- 读取的demo HPF报告DDR3/1333Mbps/32bit、training=1、DDRC_IO_VOL=1.5，p2f_clk0=49.995MHz；与§10.3中的电压及项目100MHz运动域差异仍存在，不能原样移植PS初始化参数。
- 已只读检查根目录uisrc-lab-anlogicM-V4.0.1.tar.gz内脚本：move_files.sh将boards/files里的soc_fsbl.elf复制为output/fsbl.elf，并复制system.bit和两组DTS。create_image.sh调用create_dr1m_image.sh；后者生成boot.bif，明确将fsbl.elf、destination_device=pl的system.bit和u-boot.bin打包，调用Anlogic的albg产生BOOT.bin。仅向SD根目录增加或替换一个system.bit不属于这条加载流程。
- demo FSBL的alfsbl_partition_load.c包含加载PL分区和PCAP配置逻辑；脚本与源码共同支持“启动时由FSBL加载自定义PL配置”。PS-only reset分支会跳过PL重载，不推定每次PS重启都会重新初始化PL时间戳。
- parameter-tf-fat.txt及demo boot.scr从启动分区加载uImage.lz4、uInitrd.lz4和system.dtb，再bootm；此配置使用RAM中的根文件系统。构建包另有EXT4启动参数可供后续评估。机器人程序/自启动服务可通过rootfs构建集成；持久日志和参数需另有明确的SD/eMMC存储路径，不能假设RAM根文件系统写入会掉电保留。
- 可以沿厂商基线制作包含本项目PL的SD系统。首次建议完整重建并验证一致的一组HPF/FSBL/bitstream/U-Boot/DTB/kernel/rootfs；此后仅改PL逻辑且PS配置及软件接口不变时，可复用匹配的FSBL/U-Boot/kernel/rootfs并重打BOOT.bin。新增设备节点、驱动或应用时，分别更新DTS、kernel/模块或rootfs，不必每次PL修改都重编全部系统。

本次仅确认可行路径并记录证据，没有制作项目镜像、运行打包/分区脚本或操作SD卡。项目选择哪种启动/rootfs配置与构建环境尚未因此冻结；教程中的sdb只是例子，实际部署目标必须按设备识别。

## 11. 实板串口运行基线

采集日期：2026-10-08（主机Asia/Taipei日期）。按用户授权通过COM4、115200、8N1连接；当前已有root shell，`id`确认uid=0。使用本机System.IO.Ports.SerialPort完成只读查询，DTR/RTS均保持false，无流控。未重启、烧写、挂载新分区、配置网络、操作MMIO或加载PL/模块；完成后关闭COM4。AGENT.md已有未提交修改未纳入本次记录变更。

### 11.1 系统、存储和启动

| 项目 | 实际观测 | 含义 / 限制 |
| --- | --- | --- |
| OS | `/etc/os-release`为Buildroot2022.02.6 | 与构建包版本一致，不证明源码/配置完全匹配 |
| Kernel | `6.1.111-rt42`，`#8 SMP PREEMPT Wed Jul 30 14:40:27 CST 2025`，aarch64 | dmesg编译器为Linaro GCC7.5-2019.12/7.5.0；`/proc/config.gz`及`/sys/kernel/realtime`不存在，不仅凭-rt42后缀宣称PREEMPT_RT已启用或满足运动实时指标 |
| CPU | cpuinfo有processor0/1，ARMv8，part0xd04；DT model为Anlogic, DR1M90 FPSoc | 双核平台获得实板印证，未测CPU实际工作频率 |
| RAM | dmesg为1048576K物理内存；MemTotal1012420kB | 1GiB基线获得印证，DDR速率/IO电压/训练参数未由这些数据证实 |
| CMA | dmesg在0x17c00000建立128MiB池；CmaTotal131072kB、采集时CmaFree130128kB | 存在连续DMA分配资源，地址与余量不冻结为运动ring buffer地址 |
| eMMC | mmcblk1，device/type=MMC，name=IS008G，manfid=0x9d、oemid=0x0101、date=11/2023；7653888KiB≈7.30GiB | 与标称8GB容量一致；Linux设备名称不能代替完整颗粒丝印 |
| 启动分区 | mmcblk1p1=101376KiB；已挂载/mnt/mmcblk1p1，vfat；df约97.5MiB | 内有BOOT.bin、boot.scr、system.dtb、uImage.lz4及无线/蜂窝辅助模块；无uInitrd.lz4 |
| 根分区 | mmcblk1p2=7550976KiB；`/dev/root on / type ext4`，另挂载/mnt/mmcblk1p2；df约7.0GiB，已用361.6MiB | 当前实际根文件系统在eMMC的EXT4分区，区别于教程parameter-tf-fat默认RAM根文件系统 |
| QSPI | `/proc/mtd`为mtd0、02000000字节、擦除块00010000、名alspinor；dmesg识别gd25q256/32768Kbytes | 实板Flash容量32MiB得到印证，未读取/修改其内容 |
| 时间 | 板端date显示1970-01-01；无/dev/rtc*，运行DT的i2c0 disabled | 当前日历时间无效；没有校时，日志应保留PL启动内相对时间与墙钟有效性区别 |

当前`/proc/cmdline`：

```text
console=ttyS0,115200n8 earlycon=uart,mmio32,0xf8401000 loglevel=8 root=/dev/mmcblk1p2 rootwait rootfstype=ext4 rw
```

读取eMMC启动分区boot.scr的脚本载荷，核心流程为加载uImage.lz4到0x10000000、system.dtb到0x14000000，设上述bootargs，执行`bootm 0x10000000 - 0x14000000`，不加载initrd。
制作完整SD系统时必须为实际SD根分区匹配bootargs；原样沿用`root=/dev/mmcblk1p2`可能仍挂载eMMC根目录。root来源及文件存在不能独立证明BootROM/FSBL第一阶段从何处启动，实际拨码/上电日志未采集，未为采集而重启。

### 11.2 当前PL、DMA与外设绑定

| 运行DT / 资源 | 观测 | 对后续接口设计的影响 |
| --- | --- | --- |
| FPGA Manager | /sys/class/fpga_manager/fpga0，name=Anlogic dr1m90 FPGA Manager，state=operating；绑定dr1m90_fpga_manager；region0存在 | 当前PL处于已配置状态，不证明具体bitstream身份或本项目模块存在；未加载固件 |
| PL AXI DMA | axidma@80000000，compatible=anlogic,axi-dma，status=okay；reg=0x80000000/0x1000；GIC SPI82/83（level high） | `/proc/iomem`显示80000000–80000fff被80100000.ethernet驱动占用，不能直接分配给运动寄存器或遥测DMA |
| DMA配置声明 | DT含include-sg/include-dre；addrwidth=32、sg-length-width=16；MM2S/S2MM两个通道datawidth=32 | 是当前DT声明，不作为新运动DMA选型/实际硬件参数冻结依据 |
| PL Ethernet | ethernet@80100000，compatible=anlogic,axi-ethernet-1.00.a，status=okay；reg=0x80100000/0x40000；SPI84 | `/proc/iomem`占80100000–8013ffff；绑定anlogic_axienet，对应eth0。新增PL地址需保留或明确迁移整套硬件/DT/驱动 |
| Ethernet与DMA连接 | DT有axistream-connected/control-connected；axidma平台设备未单独显示driver绑定，而Ethernet同时占用DMA资源 | 当前DMA为网络路径服务，不视为已可由运动程序独占使用的通用DMAengine通道 |
| DMA class | 当前只列DesignWare AHB DMA与PL330各8通道 | 没有观察到独立PL AXI DMA/VDMA通道注册；modules.builtin/dep未匹配Anlogic axi-dma/axi-vdma/anlogic_dma条目，编译配置仍需对应源码确认 |
| UDMABUF / UIO | /dev/udmabuf（misc，10:126）存在；modules.builtin列udmabuf、uio/uio_pdrv_genirq/uio_dmem_genirq/uio_al_generic | 只证实支持入口/内置驱动存在；未见/dev/uio*或固定udmabuf0，不等于运动缓冲/设备映射已配置 |
| NPU | hard_npu@63F00000节点存在；未见driver绑定或/dev/npu* | 节点存在不等于NPU运行库/驱动已就绪 |

DT中Ethernet clock-frequency为100MHz；dmesg网络驱动另报告assumed host clock 800000000。两者属于配置/驱动报告，未测实际PL时钟，不据此改变项目已确认的100MHz运动基础时钟。
表中SPI号来自DT大端cells；例如DMA SPI82/83对应GIC中断114/115。`/proc/interrupts`中的Linux虚拟IRQ号不能直接写入硬件规范。

### 11.3 启动文件身份与构建配套

实板`/mnt/mmcblk1p1`采集结果：

| 文件 | 字节数 | SHA-256 |
| --- | --- | --- |
| BOOT.bin | 4153472 | 858cf78c03ae75c870587be77d70668e0ba4841448581273e5c996bf8f980706 |
| boot.scr | 393 | 685f9f8cd4a1e43d79da0c78ab9591d3af1f744122e21a60b252b685ffad59d1 |
| system.dtb | 15207 | aba027eadce165ed492ac67c9259ce8d9eacac19c5c6e9f42ca09ec47b0d646f |
| uImage.lz4 | 8724717 | 12cd2ccb851376eb2870f1d3294f0d29f771e74d01a25d1b605378ea733bd7be |

四者的大小和SHA-256均不同于§10.4本地secondary demo/boot同名文件（本地依次为5186560/466/14129/8414947字节）。实板系统不能当作该demo预编译镜像的逐字节副本。这里只记录哈希，没有备份镜像内容；启动分区文件身份也不单独证明它们就是本次上电加载的每个组件。

板上`/lib/modules/6.1.111-rt42`存在，build/source符号链接指向`/home/uisrc/uisrc-lab-anlogic/sources/linux`，目标目录不存在；无法据此在板上编译内核模块。PATH未找到gcc/g++、python3、dtc、modinfo、lsblk；有zcat、sha256sum、devmem、candump、cansend、blkid。devmem仅查到工具存在，没有执行。
后续交叉编译驱动需匹配运行内核的源码/补丁、.config、生成头文件和符号信息；现有6.1.111源码包与-rt42实板镜像是否完整对应仍需核对。不能只凭主版本相同复制任意.ko。

### 11.4 联调环境与未解决事项

- eth0为PL Ethernet，eth1为PS Ethernet；二者查询时均NO-CARRIER，只有lo有IPv4，route为空。尚不能通过已配置网络替代串口登录；未修改网络或探测外部主机。
- ttyS0/ttyS1存在，未观察到PL UART-Lite的ttySL实例。未执行RS485、电机或DMA数据传输测试。
- init目录有S50sshd和PTP相关脚本，但进程查询未见sshd/ptp4l，仅见phc2sys与dhcpcd。脚本存在不视为SSH或时间同步已工作。
- dmesg有5次mmc0的“Got command interrupt ... no command operation”及SDHCI寄存器dump；当前未出现mmcblk0存储设备。未插拔/测试SD，不推定SD启动已验证或控制器已损坏。
- 无线AIC模块日志报告缺少/vendor/etc/firmware/fw_patch_table_8800d80_u02.bin、加载失败；另有regulatory.db缺失。未修改固件或重载模块。
- DDR电压/速率/训练与板卡修订仍未实测；本次根文件系统/PL管理状态不证明DDR所有参数正确，也不验证断电持久性或完整启动链。

可复核采集命令包括id、uname、os-release/cmdline/meminfo/cpuinfo、mount/df/partitions/mtd、mmc sysfs属性、boot分区wc/sha256sum、boot.scr载荷读取、运行DT属性、iomem/interrupts、FPGA/DMA sysfs、模块元数据、ip查询及dmesg。全部查询结果作为当前运行快照，项目接口冻结另见PHASE0_CONSTRAINTS.md。

## 12. Ubuntu桌面系统实板对比

采集日期：2026-10-09（Asia/Taipei）。用户切换至厂商Ubuntu桌面系统后，按授权通过COM4、115200、8N1、root登录，只读查询系统、软件包、运行DT、sysfs和日志。DTR/RTS保持false，无流控；未重启、安装软件、修改网络、挂载启动分区、操作MMIO或加载PL/模块。采集完成已关闭串口。此记录不替代DDR电压测量、运动DMA回环或Qt应用实际运行验证。

### 12.1 当前Ubuntu实际观测

| 项目 | 观测 | 含义 / 限制 |
| --- | --- | --- |
| OS | Ubuntu20.04.1 LTS / Focal，aarch64；hostname为bionic-arm64 | hostname不代表Ubuntu18.04；以os-release为准 |
| Kernel | 6.1.111-rt42，#17 SMP PREEMPT，2025-10-17构建，Linaro GCC7.5.0 | 与§11 Buildroot的#8构建不同；同版本字符串不证明配置/符号/驱动ABI匹配；未发现/proc/config.gz或/sys/kernel/realtime |
| 根文件系统 | cmdline为root=/dev/mmcblk0p2、EXT4；mmcblk0约29.5GiB，sysfs type=SD；根分区约29GiB、使用2.9GiB | 当前root在SD，不在eMMC；BootROM/FSBL首阶段来源仍未独立采集 |
| eMMC | mmcblk1约7.3GiB，type=MMC、name=IS008G；两分区在lsblk中无挂载点 | eMMC仍被识别；本次未读取其启动文件或重新验证原系统内容 |
| RAM / CMA | MemTotal1013496kB；一次free快照used276MiB、available688MiB；CMA128MiB | 仅当前桌面登录界面负载快照，不是启动峰值或HMI/AI并发预算 |
| 桌面 | Xorg与GDM3/GNOME登录界面运行；LXDE包也已安装，lightdm服务inactive | 当前实际运行的不是LXDE会话；未操作桌面或启动测试窗口 |
| 显示 | /dev/fb0，name=anlogic，1920×1080、32bpp、stride7680；绑定anlogic-vdma-fb | 已存在可用显示驱动入口；Xorg记录当前模式为1080p60，未测刷新精度/帧率 |
| 渲染 | Xorg使用FBDEV/shadow framebuffer，GLX DRISWRAST/swrast；未见/dev/dri/card0 | 当前图形链使用软件渲染；安装Mesa不证明GPU硬件加速可用 |
| 开发工具 | gcc/g++9.3.0、make、Python3.8.2、build-essential存在；qmake、cmake未找到 | 具备原生C/C++开发入口；本次未编译应用 |
| Qt | dpkg与/usr/lib、/opt、/usr/local查询未发现已安装Qt；qtbase5-dev和qt5-qmake均Installed:none | apt缓存候选为5.12.8，cmake候选3.16.3；缓存候选不证明当前网络可下载；版本选择尚未冻结 |
| 软件源 / 网络 | 配置华为云ubuntu-ports的focal、updates、backports；SSH服务active；PS eth0配置192.168.137.100/24但DOWN | 未改变网络、更新apt或测试外网/SSH连接；不能视为已联网开发环境 |
| 模块构建 | /lib/modules/6.1.111-rt42及/usr/src内容未具备配套构建资料，/boot为空；lsmod无条目 | 缺少匹配内核构建树、配置与符号信息；不能仅安装通用Ubuntu headers就匹配厂商内核；驱动绑定说明有内置驱动，空lsmod不代表无驱动 |
| 外设 | NPU DT节点存在，无/dev/npu；FPGA Manager state=operating | 无NPU/运动功能验收；PL具体bitstream身份未独立核实 |

### 12.2 当前Ubuntu显示PL资源与本地资料差异

运行DT、iomem与driver绑定相互印证：

- `0x80100000–0x80100fff`：Anlogic AXI VDMA；GIC SPI82/83；注册dma0chan0，绑定anlogic-dma，供显示framebuffer使用。不是项目已选的通用运动AXI DMA回环。
- `0x80200000–0x80200fff`：vdmafb / 视频时序资源；`0x80201000–0x80201fff`：动态显示时钟资源。显示驱动日志报告fb_phy=0x17d00000；不能把它或CMA池固定分配给运动缓存。
- 本镜像仅观察到PS Ethernet，不采用§11的PL Ethernet地址占用布局。资源分配须按所选镜像与实际PL/DT匹配，不能混用两套地址图。
- 日志首次vdmafb probe因VDMA通道未就绪失败，随后VDMA注册、vdmafb再次probe且fb0已绑定；不能只凭首次日志判定显示最终失败。

本地`01_start/02_start_Linux/05_application_demo/05-1_QT环境搭建及demo演示/demo.zip`已只读检查，含`driver/anlogic-vdmafb.c`、`driver/anlogic-dynclk.c`、`driver/anlogic-vtc.h`、PL工程`soc_prj/soc_prj.al`、HPF、两组DTS及Qt运行包。配套PDF第24页（印刷21）要求补入framebuffer/dynclk驱动和Kconfig/Makefile，说明基础BSP不能仅因有Qt选项就假定显示驱动齐全。

该ZIP内`anlogic-dr1m90-softip.dts`却将VDMA放在0x80200000、vdmafb在0x80100000、dynclk在0x80101000，与当前Ubuntu运行DT不同；num-fstores为4而当前运行DT为3。其HPF也为DDRC_IO_VOL=1.5。它可作源码/实现参考，不能认定与当前Ubuntu预编译镜像完全配套或直接覆盖运行DT。后续项目仍遵循§10.3用户确认的1.35V开发基线。

### 12.3 二次开发历史评估（当前方向见§13）

- 2026-10-09图形方案曾建议Ubuntu作为Qt HMI、PS应用和联调基线；当前采用Buildroot与Web HMI，以下保留历史比较：已有1080p显示链、原生编译器、Python、包管理与SSH入口，应用开发成本较低。Qt尚需部署，先验证二维Widgets/软件绘图原型与实际资源消耗；桌面存在不证明复杂3D或高帧率渲染性能。
- 若以后恢复本地HDMI/Qt显示，须核对显示VDMA、时序、动态时钟、HDMI输出及所需复位/互连，避免与已分配的运动GP/DMA资源冲突。重新生成匹配的HPF、FSBL、bitstream、DT及必要内核驱动；显示VDMA不改作运动DMA。
- Buildroot的优势是可裁剪、镜像较小且已有构建脚本/源码；目前实测基线未验证图形链和可用Qt运行环境。厂商Qt示例已提供补入显示驱动的路径，因此Buildroot也能继续做HMI，不需要先拥有桌面；需付出Qt交叉工具链、运行库和显示集成工作。
- 两者都仍需配套厂商内核源码/配置/补丁、当前工具工程迁移和通用运动DMA验证。Ubuntu用户空间不解除BSP依赖；Buildroot的-rt42标签也不单独证明更适合或已满足运动实时性。STEP时序仍由PL保证，Linux侧需要实测轨迹预缓存/供给与桌面并发负载。
- 若后续资源或部署目标需要精简，可评估Ubuntu停用完整桌面后运行全屏HMI，或转向Buildroot；当时尚未冻结最终发行版、Qt版本或部署方式。Ubuntu20.04标准支持已于2025-05-31结束，长期维护时应结合厂商BSP兼容性另行规划更新/支持路径（官方来源：https://ubuntu.com/20-04）。

## 13. Wi-Fi / Web HMI及历史4G资料

2026-10-22：用户确认板卡没有可用4G模块，4G扩展计划移除。本节2026-10-14资料清单保留，不再安排4G拨号或公网中转开发。

用户要求将局域网无线与Web方案纳入当前规划。控制链路为浏览器→PS Web服务→统一命令/状态入口→现有坐标/运动后端→PL；串口复用执行后端。首版不需要图形桌面、HDMI或Qt，使用板卡连接路由器的Wi-Fi STA，手机/电脑在同一局域网访问板卡地址。网页资源本地提供，不依赖互联网；板卡AP功能未验证。

厂商资料目录：`D:\Works\Embedded_contest\docs\Analogic\01_start\02_start_Linux\05_application_demo\05-4_无线通信方案`。已只读核对文件和ZIP条目；没有安装驱动、连接无线或修改板卡。

| 资料 | 已核对内容 | 接入边界 |
| --- | --- | --- |
| `05-4_米联客-安路F3P-CZ02开发板无线通信方案.pdf` | 文件存在，作为后续教程参考，本轮未据PDF正文作新增硬件结论 | 开发时核对工具/内核版本及实物条件 |
| `WIFI.zip` | AIC8800 USB驱动源码、AIC8800D80相关代码、固件及旧构建产物 | 按项目内核/config/Module.symvers重编，核对实际USB设备ID、固件加载路径和驱动依赖；不直接加载旧ko |
| `4G.zip` | GobiNet源码、Quectel连接管理源码/quectel-CM、旧ko及工具产物 | 历史资料；无可用4G模块，扩展计划已移除，不列为待验收项 |

当前项目基线 `bsp/evidence/kernel.config` 已有 CONFIG_INET=y、CONFIG_USB=y、CONFIG_USB_DWC2=y、CONFIG_USB_DWC2_HOST=y；WLAN未启用、USB_SERIAL未启用。最新scope展开DTS的usb_otg0最终status=disabled、dr_mode=host。Buildroot配置未包含本项目专用无线认证/DHCP/网页服务部署配置。USB不是内核完全缺失：需审核设备树/供电/Host枚举，补齐实际驱动所需无线配置、固件和网络工具，再验证STA接入。内核或配置变化后相关树外GP/运动/DMA模块也需匹配重建及身份门禁。

已有 delta-scope 常驻 Unix socket后端，单设备所有者，独立STOP/快照，不自动REBASE/ENABLE/START；目前仅接受root UID，输出为现有文本测试协议。Web需提供受控适配/授权入口，不能直接暴露root socket或拼接任意shell。具体权限分离、API、认证及服务依赖尚未冻结。

首版页面范围：XYZ/时长、IK/目标步数预览、执行/停止、PL命令位置/脉冲计数、故障/命令结果。先用模拟后端开发页面与统一服务，再接无电机delta-scope；当前scope镜像读回/冷启动及ARM模型核对通过，但坐标下发、在途STOP及示波器实测尚未登记，详见bsp/scope/BUILD_STATUS.md和SCOPE_MANUAL.md。

认证、唯一命令ID、重复执行防护、过期拒绝以及请求接收/PL接受/执行完成的区分是要求。命令期限、断线策略和重启后的身份空间须专项确认；不假定板端墙钟有效。网络STOP不替代本地急停，STOP不能被运动等待阻塞，重连不重放旧轨迹。4G阶段由板卡主动连接公网中转服务，复用命令/状态后端，不另建运动通路。

组件分工：无线/BSP任务交付驱动/固件/配置和网络验收；Web任务交付页面、命令服务、模拟测试及受控后端适配；RS485任务独立交付采集/状态与DMA遥测契约。最终系统统一审核PS/PL资源、内核模块、复位/时间基准、网络负载和完整100MHz时序，再打包镜像。现有Wi-Fi/4G档案存在不代表实物连通、驱动兼容或远程执行已验收。


## 14. 2026-10-14 完整 BSP 集成的板载 RS485 管脚确认

用户在本轮集成答复“板载485的管脚定义按照硬件手册来”。据§4接入 TX=L17、RX=N16、DE与低有效/RE共用N15，BANK33/LVCMOS33；J11-4=GND、5=A、6=B。完整顶层保留已确认的 J12 三轴九针示波器输出，M4禁用，不新增实体电机连接。

用户同时说明实际从机型号、地址待定，菊花链末端从机将带120Ω。控制板端点位置、板上固定120Ω与另一端终端的完整拓扑、线长、偏置、转换模块与固件仍待核对；未把参考 E0/E1/E2 当作实物地址确认。实体 RS485 有效反馈和并发压力未执行，超时记录只能作为诊断/运输证据。

本轮新GPIO/HP1顶层复现受保护S2MM-only IP的SYN-5066，未修改或屏蔽IP，禁止发布启动镜像/烧录。详情与最终单顶层资源/时序证据见 bsp/telemetry。未打开COM4或自动复位板卡。

## 15. 2026-10-16 限位触点兼HOME及外部急停供电结构

用户描述三个电机各有弹簧片触点，到极限位置被压合，计划每路信号与公共GND构成低有效输入。三只开关确认兼作HOME/限位：HOME三轴同时低速靠向参考端，各轴触发后独立停止；普通运动任一路触发则三轴全停。具体GPIO/外部上拉/保护/接线、方向、参考角度及响应/搜索上限尚待冻结，不能配置为推挽高电平后直接用触点接地。

用户确认急停位于物理链路，按下后切断运动装置12V供电，控制系统另行供电并继续运行；后续计划选择1NO+1NC急停开关，在切电同时向控制器提供动作信号。具体型号、两组触点是否电气独立、DC额定、功率切断方式、GPIO反馈接线/极性仍待核对。本次没有接管板卡、操作急停、测量12V切断/残压/实际停止或验证恢复；不得假定动作反馈证明电源已经消失，或假定断电会自动取消PL会话、保持机械位置。

用户已接受HOME自动低速退离至触点释放并停稳后进入READY；速度/距离/参考值/限时等尚待配置。急停后的软件取消/位置有效性及供电恢复门禁待专项确认，见PHASE0_CONSTRAINTS.md顶部2026-10-16条目。原有“外部电路负责最终急停失能、PL负责整机安全与HOME”职责不变。
