# 项目环境、已有资产与双方职责

## 目标系统

项目是Delta机器人自主控制平台。链路为：浏览器→PS统一命令/状态服务→规划/运动学→现有运动后端→GP/MOT2/DMA→PL→STEP/DIR/EN。串口与Web复用同一执行后端，网络不参与单脉冲实时控制。

|项目|已核验基线/含义|
|---|---|
|硬件|DR1M90GEG400，双核ARM，MLK-F3P底板；不要求合作方有板卡。|
|目标用户态|AArch64/arm64，Buildroot 2022.02.6；现有Linux交叉工具为Linaro GCC/G++ 7.5。库与应用应兼容C++17及该工具链，不依赖目标机必有Python/Node或桌面环境。|
|内核参考|6.1.111-rt42-bsp-sd1；名字含rt不代表已验收PREEMPT_RT或最坏调度界。|
|存储/内存|DDR 1GiB，eMMC 8GB，QSPI 32MB；目前项目镜像使用SD，部署介质由项目方管理。|
|网络/界面|首版Wi-Fi STA连接路由器，局域网HTTP JSON＋SSE，网页资源本地提供，无互联网依赖、无HTTPS要求；认证仍需实现，机制待定。|
|开发环境|项目方Windows/PowerShell，Asia/Taipei；合作方可在普通Windows/Linux电脑开发，无需复制项目方绝对路径。|
|时间/单位|PL统一u64/1MHz；高层XYZ为mm、角度为°，Golden内部rad。64位JSON值使用十进制字符串，时间来源/epoch分别标识。|

前端构建时可使用本机工具，但交付网页构建产物及可重复构建方法，运行时不从CDN加载资源。具体HTTP库、依赖、部署进程及权限模型先提出并由项目方审核。

## 已有交付能做什么

1. Golden：C++ IK/角度到绝对步数、原源码oracle及1272条冻结向量；宿主及ARM已有精确一致证据。包中可重新运行宿主回归，不能以本机运行替代新的ARM验收。
2. 运动：MOT2为72B、小端、CRC32/ISO-HDLC，signed64四轴绝对目标、u64 session、u32连续sequence、相对duration_tick。72B codec和标准schema可复用；维护REBASE不等于HOME。
3. delta-scope：现有无电机Linux测试程序，单设备owner、root-only Unix socket、独立STOP/快照；move只提交一个关节终点，不是XYZ直线插补。它尚无正式Web命令生命周期，不直接暴露给网络。
4. 遥测：既有32B采集记录保持，新外层64B带CRC、collector/transport generation、revision和completion_serial；纯C解码器可直接在普通主机测试。
5. 最新值cache/原子快照、独立HP1遥测DMA已实现，PS读取接口有原型；BSP/板端恢复和最终部署由项目方验证。合作方消费已交付的内存数据或模拟源，不拥有DMA控制权。

## 当前未完成条件

- HOME、整机安全输入/联锁/Watchdog、实物机械标定及有效XYZ估计链尚不完整；模拟器可注入明确标识的已知状态，不得隐式视为实机HOME完成。
- 实际GPIO波形/坐标执行证据仍由项目方/用户登记。运动命令计数不等于编码器反馈，也不直接证明实际末端XYZ。
- 硬件集成/优化已有资源和时序报告，但S2MM-only厂商IP诊断仍未关闭，不能对外声称新镜像已上板验收。
- 普通Linux调度持续补给曾欠流，有限FIFO50测试成功不构成最坏延迟保证；不能让HTTP、日志或数据查询阻塞轨迹供给和STOP。
- 无线驱动/联网及正式命令API尚待接入/确认。合作方可使用localhost模拟服务，不依赖板端网络就绪。

## 工作归属

|合作方交付|项目方负责|
|---|---|
|六项PS组件的源码、可重复宿主构建、模拟器、单元/组件测试、前端静态产物|HTTP/IPC边界统一审核、板端设备适配、AArch64交叉编译/运行与系统部署|
|接口/依赖/资源需求提案、异常场景、集成说明|Linux驱动与DMA owner、权限/服务启动配置、内核匹配、设备树、HPF/FSBL/BOOT/SD|
|纯轨迹规划/IK适配、遥测内存解码、文件/日志逻辑|PL/厂商IP修改、时序与资源签核、GPIO/RS485实物、校准、安全及板测|

合作方不得要求直接访问COM口、SSH板卡/VM、SD或任意MMIO来完成常规交付。确有额外设备/接口需求时，给出输入输出、理由和可模拟验收方法，由项目方实施集成。

信息来源：冻结需求、bsp/README.md、bsp/scope/build_arm.sh及BUILD_STATUS.md、bsp/telemetry/BUILD_STATUS.md、pl_motion/MOTION_HANDOFF.md、pl_rs485/RS485_DMA_HANDOFF.md、资源优化交接。精确快照提交及源文件哈希见包内manifest。
