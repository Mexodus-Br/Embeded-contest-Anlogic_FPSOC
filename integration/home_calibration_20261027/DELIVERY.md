# HOME标定镜像最终交付 r2

2026-10-27（Asia/Taipei）。离线实现、完整PL构建与系统镜像装配完成；实板未执行、未写SD、未打开串口。普通XYZ/方向/示教/任务运动保持关闭。只使用 **artifacts/release-r2**；release-r1启动脚本换行失败，保留作证据，禁止部署。旧full_system r4和回退文件未改。

## 文件与版本

- 镜像：[sdcard.img](artifacts/release-r2/sdcard.img)，536870912字节（512MiB）。
- 镜像SHA256：`335a509643f57fe6753c5f596fc7e7f0d84cff7b9c8febc584fcc6779e85f69d`。
- 编译提交：`6bec51644cca5a8699a318b3ab2fe13650ddfc86`，无工作树软件覆盖；后续交付文档提交不改变编译身份。
- 版本：`home-calibration-20261027-r2`；PARTUUID：`a61e22d5-02`。
- HOME配置ID：`5f5d223d88b8cec8f99bdea20a7b40f360b72bdf2a353fd07617ce4494285ad0`，PROFILE0、approval_scope=home_calibration_only。不是旧PROFILE2身份，也不表示实板验收通过。
- 同目录配齐新bit/HPF/FSBL/BOOT、匹配内核/DT/rootfs/U-Boot/boot.cmd/scr；PS程序、驱动、HMI在rootfs内。[manifest](artifacts/release-r2/manifest.json)与[SHA256SUMS](artifacts/release-r2/SHA256SUMS)列出11项必要最终交付物；仅哈希该清单，未递归哈希日志/中间文件/源码归档。
- VM独立目录：`/home/uisrc/embedded-home-calibration-20261027-r3`。冻结来源、六项独立PL输入修改见[hardware-inputs.json](hardware-inputs.json)；其他任务脏RTL均未混入。

## 离线结果

| 检查 | 结果 |
|---|---|
| 完整综合/布局/布线/bit | TD各阶段threads=16；100MHz；最终setup 1.109ns、hold 0.020ns，满足既定>1ns setup目标；bit生成成功 |
| 资源 | LUT6 23369/52480（44.53%），slice 31344/52480（59.73%），寄存器33568/104960（31.98%），ERAM57/280，DSP2/240 |
| 同批启动链 | 新HPF含bit逐字匹配；556项PS参数一致；新HPF的PS/DDR/存储宏、执行初始化与DT头等于基线；独立SDK重建FSBL，GP/HP0/HP1复位释放mask0x33，生成新BOOT |
| 时序约束 | 无无效约束/组合环/缺时钟；STA覆盖99.96%。保留外部IO缺input delay5项/output delay2项、保护IP dummy/等价问题，不能宣称电气全签核 |
| HOME与时序回归 | 实际参数controller54项；原32场景；精确100MHz实际executor/inputs24项，3,007,517拍；闭合起点预退离、逐轴命中、固定150步、500步/超时、稳定释放/重触发、各取消路径及迟到记录 |
| 普通运动禁用/联锁 | 强制controller READY仅作测试，实际门389项检查拒绝ENABLE/OPEN_SESSION/START；联锁79项、解析等价68,728项 |
| 受控驱动/服务 | SAF2实际C函数45项；typed RUN实际函数模型；配置批准5种负例；后端22场景含未知XYZ/缓存来源、HOME完成/故障、身份/期限/重复请求 |
| 匹配内核模块 | 6.1.111-rt42-bsp-wifi1；目标内核原config/Module.symvers一致；212个安装模块、3556项导入CRC全匹配 |
| ARM程序/运行库 | Buildroot GCC7.5；AArch64、解释器和DT_NEEDED闭包/逐库版本满足，含GLIBC_2.25、GLIBCXX_3.4.22、CXXABI_1.3.9；未用Windows GCC7.4产物替代 |
| DT | 启用六个控制节点并替换SAF2 compatible；逆向还原DTS等于基线；1GiB内存、地址/IRQ保持，未添加validated HP1 drain |
| rootfs/镜像 | ext4内14个安装文件逐字节读回；EXT4/FAT只读fsck；最终MBR、两分区及FAT启动文件读回通过；本机11项大小/SHA256与VM一致 |
| HMI/本地/日志 | 最终14项HTTP服务、5项边界、绑定/Host/Origin/认证、当前本地入口持久会话/同boot/STOP/release通过；网页语法/方向边界回归通过。真实动作共用后端 |
| Linux脚本 | 最终LF输入断言、VM sh -n与Python3.6 py_compile纳入构建并通过；修复前候选不交付 |

原始审计：[artifacts/r2-audits](artifacts/r2-audits)，PL结果[hardware-result.json](hardware-result.json)。保留首轮测试台适配/命名错误、模块漏头文件、Tcl路径和CRLF失败记录，均未删除或覆盖旧候选。宿主原C++源有既存缩进警告；目标模块-Werror构建通过，未将主机测试当实板证明。

## 与cf764ad及r4的差异

三轴索引、物理引脚与普通DIR极性沿用已核对映射，M4无实体输出；参见原[位置/RS485核对](../full_system_20261026/POSITION_RS485_REVIEW.md)。cf764ad MOTOR3125高/低均3125拍、MAX16kHz、DIR setup/hold及EN setup/disable均500拍，本镜像恢复同口径；r4为500拍/100kHz。新HOME采用三轴搜索000、退离111、100Hz/轴，搜索限500/10s、两种退离150/3s、释放20ms。

接触命令计数=-150，正式退离完成=0。机器显示零姿态为退离完成姿态；这不是机械0°/编码器0/实际XYZ。HOME_DONE不使XYZ有效，也不开放普通运动。原厂运动学与4.5×200×16倍率保留供后续标定；不能从直接init或现有模型的参考姿态继承真实坐标。

0x30发布编码器carry/value，0x33发布接收命令脉冲；二者不能互换。现在服务通过独占typed设备读取原子latest-cache，保留15行原始32B、身份/时间/有效与陈旧信息，不是完整64B历史或触点沿同步锁存。HP1中断RX保持quarantine，本镜像不启动RX DMA。

## 部署与实板停止点

完整分阶段命令、标准、停止条件及空白结果表见[ACCEPTANCE.md](ACCEPTANCE.md)。顺序为当次SD身份与覆盖授权 → 用户断电/隔离STEP与接线 → 空闲实际USB串口确认 → 启动身份/波形/安全及异常 → 用户确认后近限位HOME → 数据标定。每阶段失败先定位修复再复测受影响项。

默认HMI只监听127.0.0.1:18083，设备root:root 0600。启动仅观察，不自动配置/轮询/OPEN/HOME/REBASE/ENABLE/START或重放，也不自动复活服务。`ps-local`使用同一服务认证和owner。Web认证、任务存储和日志查看/下载保留；若后续需要局域网，先配置既有Wi-Fi并核对本机实际IPv4，再显式配置`/etc/ps-hmi/bind-ipv4`及重启，保留token/Host/Origin/CSRF，不使用0.0.0.0。镜像不预置个人网络凭据或HMI令牌。

剩余：真实16细分/正向/限位极性和485/STP格式、外部电气/安全输入、实物速度/DDR及受保护IP资格均须实测；机械/FK/编码器参考、XYZ/逐轴角度边界与余量待标定。普通运动不放行。不操作eMMC/QSPI，不恢复CDC独立门禁、不增加4G。

当次只读枚举发现Disk1 Generic- SD/MMC/MS PRO（31,708,938,240字节，USB，非系统/启动盘），无卡片序列号，UniqueId是读卡器身份，不能单独证明是哪张卡。尚无覆盖授权，禁止写入；写前须用户确认该卡非回退卡、旧数据处置/备份并再次核对。串口仅COM9/COM10蓝牙，尚未发现板卡USB串口，未打开端口。
