# 2026-10-13 BSP 内部四轴运动验收

固定源码 `22ea0a41daa974d24f16b72df7c31db212b7ab8f`、封存交接 `3a4ea5c8e56024bd2407916bafed48508e5a1e69`，84份源码、6份IP、7份证据身份门禁及唯一规范生成物检查通过。冻结 PL/接口/Golden 未修改；原 AGENT.md 修改和无关日志未处理。

| 阶段 | 结果 |
|---|---|
| PS/HPF/bitstream/FSBL/BOOT/DTS、匹配 Linux 软件构建 | PASS |
| 同一 SD Windows 写入与完整512MiB读回 | PASS，915d25b7…b6b8e5 |
| 最终版本用户冷启动 FSBL → U-Boot → Linux | PASS，根2176bfe4-02 |
| 原GP回归、新运动身份/IRQ/poll/快照与四轴动态 | PASS，两轮 |
| PAUSE中独立STOP、错误、在途取消/reset、显式恢复/重新分配 | PASS，两轮及失败后安全释放 |
| 100μs点/2ms补给，两路满CPU负载 | SCHED_OTHER失败欠流；FIFO50隔离测试通过，有限实测 |
| 实体STEP/DIR/EN、驱动器、电机、真实电气同步 | NOT_TESTED |

## 集成与独立时序签核

入口 `pl_dma/rtl/motion_gp_ps_top.v` 替换旧 GP/DMA 顶层；原GP0x80400000/4KiB/SPI82(INTID114)、DMA0x80500000/4KiB/SPI83/84(INTID115/116)，新增0x80600000/4KiB/IRQ3/SPI85(INTID117)。新PROFILE=0x31544f4d、VERSION1/CAPS0xf/FEATURES0xf；旧GP VERSION1/CAPS0xf/FEATURES7，旧快照继续原空闲语义。真实运动快照只读新窗口。最终 DTS 全数值地址图无重叠、simple模式/noSG、无旧loopback client，mask32/stream64/BTT16，IRQ level-high。HP0与GP100MHz，共域复位同步释放；独立最终 FSBL GP/HP soft reset释放先于common PL reset。厂商PS属性加载方式保持，DDR1.35V/32bit/1333MT/s及存储/CPU/UART宏与此前实板基线相同。

最终系统独立 route/STA：100MHz，setup +0.454ns、hold +0.020ns，STNS/HTNS0、coverage99.99%；虽数值相同，证据来自本次 BSP 工程重跑，未沿用 PL 参考结论。LUT13995/FF14022/slice16203/ERAM16/DSP4/GCLK1/SCLK6。最终诊断无无时钟、组合环、失效约束、缺失IO delay等问题，保留两类 HIGH：vendor ERAM 未用 reset及executor未绑定实体反馈；完整原文见 evidence/motion-hardware-20261013。speed2 是本次参考器件条件，不等同实物速度等级核验。

STEP/DIR/EN仅内部，无电机引脚绑定；唯一实体输入H16/100MHz。默认冻结RTL时序参数0禁止运行。本镜像明确使用交接隔离参数3/2/4/7/5/3周期、验证max10MHz、raw64/prepared8/START32，不能冻结为驱动器参数或产品性能。

## 软件与恢复

MOT2使用生成 C定义和 codec，72B、小端、CRC32/ISO-HDLC；交叉工具编译样例与冻结Python codec逐字节一致。provider/client W=1和程序Wall/Wextra/Werror通过。设备 DMA API coherent65520B、mask32、地址8B对齐；仅MM2S、S2MM保留恢复域不投RX。buffer交接有屏障及ARM读回，IOC和packet_closed分别检查；GP accepted/active/done/session_done独立验证。预启动包按容量信用限制，不以超过容量大包等待IOC启动；910条仅用于明确的背压在途注入。

单writer命令等待与独立STOP/快照锁分离。恢复阻断提交→GP STOP→pulse-safe→两方向terminate_sync/controller恢复→HALTED/reset-clear→IRQ/tasklet/描述符全静止→10ms稳定复查→PL半包/队列清空→新generation/LINK_RECOVER→显式处理fault→保留位置读取→新session。ERR_IRQ先GP STOP，正常IOC不当故障；旧callback/session失效。停止失败路径quarantine保留buffer和模块引用、禁止释放/重用/自动续跑；未人为制造硬件无法HALTED的失败。显式RELEASE后才能释放buffer和卸载client。PS硬总线在途DDR关闭未独立探针测量，软件门禁与取消后板测证据不能替代总线形式证明。

## 实板结果与限制

两轮通过：四轴不同目标[12,-7,0,5]→[-4,9,0,-2]→零位移END，脉冲增量[28,23,0,12]及位置/accepted/active/done一致；PAUSE/RESUME，忙PAUSE期间独立STOP；CRC、序号间断、旧session、截断/ARM错配、欠流、910条背压在途STOP与DMA取消/reset；保留位置/时间戳、新generation与显式新session、buffer释放/重载重新分配。新增poll等待独立快照事件并唤醒通过，hwirq117 level；S2MM IRQ始终0。旧GP前后41项回归通过。

此前普通调度一次通过102432点/6400批、16..32条补给、约10.2436秒，两路yes CPU负载，max成功间隔1.718370ms、最小采样水位31。最终镜像同样普通调度负载复测在accepted239/done238发生欠流0x202，日志中未完成供给指标；停止后显式清故障/释放，不续跑旧轨迹。此失败证明单次成功不足以保证普通Linux最坏提交界。

随后明确新session、SCHED_FIFO50生产者/两路SCHED_OTHER满负载隔离测试，仍使用同一镜像/模块/app与raw64/prepared8/START32，102432点/6400批/约10.2436秒，实测max成功间隔1.651740ms、最小采样水位31，2ms目标通过。31×100μs减实测间隔约1.448260ms仅为该有限采样下的估算余量；水位不是连续最小值、PREEMPT内核不是PREEMPT_RT、未证明所有IRQ/IO/负载下最坏界。长期可靠持续生产需明确并验收调度策略、预缓存/水位/安全裕量。199.756MB/s旧回环和仿真不作本目标证据。完整每批submit/IOC/packet_closed及成功间隔原始记录保留。

## 身份、复现与失败记录

完整固定IP/schema/源码、镜像23文件及模块哈希见 DELIVERY.json。最终包 `bsp/artifacts/motion-validated-release.tar.gz` SHA fe129e9bd8ff3f818a0ba1cdd602674759f03576398923c3a16afbd19c6292a1；完整SD SHA 915d25b78c5afd2887f1d35b7327afb8cd12fb0529967560e92bc32c87b6b8e5；原回退镜像afa13b14…420050d保留。Windows disk1 UniqueId/31299993600B/USB/非系统身份与历史匹配，排除disk0系统NVMe。写24.625s、读18.406s，536870912B全部一致；源FAT/ext4 fsck通过、Windows分区/文件系统签名通过。eMMC/QSPI未写入。

冷启动COM4/115200/8N1/root，DTR/RTS=false，用户手动上电。首次最终复验采集0B，重开COM4后再次用户上电收到完整19008B日志，SHA 9cd905d56ac0dd548cc72c9bae44b3034bb2976cf2c968f8bc294be531f1461c。零字节日志保留，无法仅凭无输出确定原因。FSBL HPF09:53:35/bit09:52、SD MSSD0/1:/BOOT.bin、DDR1024/1333、GP reset释放、U-Boot/Linux根2176bfe4-02相符；Linux模块/config/CMA128MiB/DT地址IRQ门禁通过。

构建失败未删除：首次supervisor中断导致TD退出，随后从place DB完整重跑route；HPF exporter产物完成且嵌入bit一致，但未exit而超时，复现脚本补exit；SDK BSP_DIR环境冲突后移除重建；CRLF shell、provider误用stock头文件、格式/缩进-Werror等均在构建阶段修正。首板验收程序错误把序号语义拒绝期待为DMA transport失败，修正预期并重编app，PL/契约未改；原失败日志及修正应用日志保留。最终普通调度持续补给失败独立保留，不被FIFO50通过覆盖。

复现步骤见 README.md。原始构建证据 evidence/motion-build-20261013、硬件 evidence/motion-hardware-20261013；COM4全部原始日志和sidecar元数据、结构化汇总见 evidence/motion-board-result-20261013.json。Git保存源码/证据，体积大的debug/完整镜像/FSBL源/map/disassembly在已校验包内。

进入实体IO/电机阶段前仍需确认引脚/电平/极性、驱动器实测STEP高低宽与DIR/EN时序及max-rate、IO复位状态、回零/限位/报警/急停/独立安全停止链路、机械方向/位置恢复策略及驱动输入同步；实物DDR供电/颗粒速度等级、长期DDR/CMA/存储压力尚未测。内部快照通过不能代替实体引脚和驱动器同步验收。

最终长轨迹额外离线核对：accepted=active=done=102431、四轴位置[11,-4,0,-4]、pulse_total增量[199731,198038,0,184380]与逐点目标积分完全一致，END计数+1。最终IRQ114/115/116/117计数9/6433/0/7，闲置1秒两次相同、Err0。结束GP与DMA provider加载且引用0、运动client卸载、coherent运动buffer已释放、无活动传输、所有串口采集/执行进程退出并关闭COM4。
