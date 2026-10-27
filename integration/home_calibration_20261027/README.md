# HOME与坐标标定验收镜像

起点05686d4。只开放身份匹配的近限位低速HOME标定；普通XYZ、方向、示教、任务运动继续关闭。复用controlled_v1_20261021/frozen/pl的完整PS/双DMA/SAF2/R5S2工程及现有HOME状态机，未混入产品工作树的未提交RTL。旧r4、motor3125和回退介质不变；不恢复CDC独立门禁，不增加4G计划。

## 配置与计数约定

production.json的approved现在明确限定为approval_scope=home_calibration_only，不是普通运动/XYZ或实板通过的批准。生成器验证完整已确认参数，生成Verilog参数与供PS/内核共同检查的home_calibration_policy.h。未知profile禁用，旧simulation/PROFILE2身份不被HOME入口接受。

- 100MHz；STEP高/低最小均3125拍（31.25µs），DIR setup/hold和EN setup/disable均500拍，MAX_STEP_HZ=16000；M4为0且无实体输出。
- HOME DIR=000；预退离/正式退离=111，三阶段每轴周期1,000,000拍，即100脉冲/秒。
- 搜索最多500脉冲/轴、10s；预退离/正式退离均固定150脉冲、最大150、各3s；稳定释放2,000,000拍=20ms，触发快停不延后。
- 每轴开关命中处的**命令计数约定为-150**，正式退离+150后为0。预退离不建立参考。0不是机械0°、不是编码器0，也不是Golden几何XYZ原点；机器显示零姿态指正式退离完成姿态，XYZ映射仍待标定。
- HOME_DONE只使PL计数具备该参考意义；真实XYZ与角度仍未知，普通运动在PL的normal_inhibit和Linux后端两层拒绝。没有台面REBASE/ENABLE入口；后续台面init仅允许PS工作坐标变换。

## 实现与构建

prepare_hardware.py仅复制冻结输入，替换生成参数、选择PROFILE0、换用motor3125脉冲参数、增加普通运动禁用以及使用已核对J12约束。完整综合/布局/布线脚本每阶段显式16线程并读回，原100MHz与有效IO约束保持。finish_hardware.py审核最终>1ns setup目标、hold非负、无无效约束/组合环/缺时钟后生成同工程bit/含bit的HPF。中间估计不能作为最终时序结果。

prepare_sources.py从固定Git提交打包最小软件输入；build_boot.py用新HPF在独立SDK副本重建FSBL/BOOT，核对PS/DDR/存储生成宏和可执行初始化、GP/HP0/HP1复位释放。build_vm.py在原wifi1内核与Buildroot GCC7.5构建SAF2和新增typed RUN的RS485模块、ARM程序，检查全部安装模块CRC、ELF/运行库依赖、DT、实际ext4内容及512MiB SD文件两分区/启动文件读回。旧镜像/SDK/内核来源保留。

目前构建进行中，最终结果与必要交付物SHA256另行登记；不能由脚本存在推导镜像已完成。只哈希必要最终交付物及配置身份，不哈希日志、中间数据库或证据目录。

## HOME入口与数据

启动仅加载受控驱动并运行一个观察服务；不自动配置/开启轮询、OPEN/FEED旧owner、HOME、REBASE、ENABLE、START或重放。设备root:root 0600，CAP_SYS_RAWIO保留。Web认证/CSRF/Host/Origin和STOP独立路径、任务文件存储、日志查询/下载保留。本地ps-local通过同一Service访问，不另开设备owner。

显式动作：configure（空闲RUN-off且无owner时配置SAF2三轴掩码7/2s期限）、feedback_on（应用既有兼容轮询周期并RUN）、feedback_off（仅空闲关闭RUN）、open、clear、recover、home、disable、close。返回queued只算入队；观察ACK和真实快照。HOME同时在PS排队、提交前和内核检查精确配置身份/有效性，旧PROFILE2不能借入口运行。

Linux设备owner独占RS485 fd，以RS485_SNAPSHOT原子读取已存在的15行latest cache：发布每行原始32B good/result副本、有效/陈旧、generation/revision、请求/事件时间和解码值。不会consume FIFO、伪造64B CRC或申请RX DMA；明确history_complete=false、各轴/查询异步。新增RS485_RUN ioctl仅固定RUN字段和状态读回，不暴露MMIO或任意命令，不改变PL空闲门；内核源码在software/telemetry，原frozen不变。

安全/运动快照每轮观察，反馈缓存目标100ms一次；HOME期间及状态变化写入有界home_calibration_observation日志，含安全快照/计数/配置与快照ID、源时间及编码器/接收脉冲缓存。它是观察时刻数据，不承诺精确每轴触点沿编码器同步锁存或完整串行帧历史；网页可下载固定日志快照。PL已有global HOME开始/完成时间和hit/distance掩码原义保留。

## 验证与剩余实物条件

已验证：实际参数的54项controller检查；32项原安全场景（原禁用production用例改为未知profile，仍验证拒绝）；45项SAF2实际C函数模型；22项后端/缓存/来源场景；实际RUN函数模型；配置批准负例；网页14项服务、5项边界、绑定认证、本地入口和浏览器边界。精确100MHz仿真验证31.25µs高/低守卫、100Hz边沿间隔、20ms释放及STOP排空。

保留失败：RTL测试适配脚本首轮匹配条件错误；精确波形测试首轮仅等4000拍而高低合计6250拍，修正bench为7000而不改RTL；本机Linux分支编译发现旧C函数rs485_snapshot与结构同名，显式struct后重编译。全部日志不哈希。新模块首次VM构建发现打包缺少record_decode.h，补齐冻结头文件后从新目录重建；首次bit导出修正Windows反斜杠路径为Tcl正斜杠；禁普通运动测试台修正宏/层级名后389项检查通过，联锁79项和68,728项解析等价通过。

剩余：实物接线/极性、实际驱动16细分/反馈格式及STP查询、外部IO/安全输入电气、受保护IP SYN-5066、速度等级/DDR和实体停止验收仍须按影响记录。HP1中断RX的DDR静止未证明，仍保持quarantine；本轮不启动RX DMA。XYZ/角度/FK/编码器参考与机械边界余量未标定，不能由HOME计数零点放行普通运动。

实板顺序：先核对当次SD并申请覆盖授权，确认实际空闲串口；用户断电接线/上电。先脉冲隔离检查启动身份、波形、逐路输入和异常取消；再由用户确认近限位起点、急停/反馈健康后显式低速HOME，保存计数、源时间和编码器数据。任何失败先STOP、定位、复测受影响部分，不重放旧HOME/任务、不扩大搜索范围。不操作eMMC/QSPI。
