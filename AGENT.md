# Delta 机器人自主控制系统：顶层设计说明

> 本文档用于描述项目的系统级目标、功能分层、PS/PL 职责边界、主要接口、数据流与推荐实施顺序。  
> 本文档不规定具体 RTL/C/C++ 实现细节；具体模块接口、寄存器映射、通信协议字段和软件 API 应在后续专项设计文档中冻结。
> 当前确认结果和首版功能目标见 PHASE0_CONSTRAINTS.md，硬件事实及资料差异见 HARDWARE.md。

---

## 1. 项目目标

本项目面向一套以 SoC FPGA 为核心控制器的 Delta 机器人系统。

系统目标不是简单复刻原有 MCU 固件，而是在保留原有运动控制功能链路的基础上，重新构建一套能够：

- 脱离外部上位机独立运行；
- 在本机完成任务管理、轨迹规划、笛卡尔插补和 Delta 逆运动学；
- 由 FPGA PL 提供确定性的多轴同步运动执行；
- 通过 RS485 对多台闭环步进驱动器进行运行状态轮询、校验、时间戳标记和数据采集；
- 将运动状态、驱动状态和时序数据送入 DDR，并供 PS/NPU 进行工况识别和故障诊断；
- 通过 CAN 与外部 PC、PLC、无线模块或其他设备通信；
- 支持 HMI、本地任务存储、参数管理、日志记录及其他功能扩展；

的自主机器人控制平台。

系统应将“自主规划”“确定性运动执行”“驱动层闭环”“工况/故障诊断”明确分层，避免将不同实时等级和不同职责的功能耦合在同一实现层中。
系统开发过程中可能会使用厂商 IP，以实际开发过程中用户要求为准。

---

## 2. 总体设计原则

### 2.1 自主运行优先

外部通信节点不是系统运行所必需的实时控制器。

外部设备可以是：

- PC；
- PLC；
- 无线通信模块；
- 调试终端；
- 其他控制器。

外部节点主要用于：

- 下发高级任务；
- 修改配置；
- 上传/下载任务；
- 查询状态；
- 调试和维护。

正常自主模式下，即使外部 CAN 节点断开，控制器仍应具备继续执行已接受任务或按照系统安全策略进入暂停/停止状态的能力。

### 2.2 PS 与 PL 按实时性分工

系统采用如下基本原则：

**PS 决定“机器人要去哪里、如何运动”；PL 决定“运动命令在什么确定时刻被执行”。**

PS 主要负责非硬实时、高复杂度算法与系统管理。

PL 主要负责具有严格时序要求的运动执行、状态采集、时间戳和基础安全逻辑。

### 2.3 驱动器内部完成电机闭环

四台闭环步进驱动器自身完成编码器反馈和电机内部控制环。

SoC FPGA 不在第一阶段实现电机级位置环、速度环或电流环。

控制器向驱动器提供：

- `STEP`
- `DIR`
- `EN`

共四轴、十二根实时控制信号。

控制器同时通过 RS485 获取驱动器运行状态。

因此系统中存在两条独立链路：

1. **运动命令链路**：PL → STEP/DIR/EN → 驱动器；
2. **状态采集链路**：驱动器 → RS485 → PL → DDR/PS/NPU。

### 2.4 运动控制与状态采集解耦

RS485 不参与单脉冲级实时运动闭环。

RS485 的职责是：

- 主从轮询；
- 地址寻址；
- CHECKSUM-8 校验；
- 运行状态采集；
- 故障码采集；
- 驱动器反馈采集；
- 采集时间戳标记。

运动执行的连续性和同步性不得依赖 RS485 应答延迟。

### 2.5 统一时间基准

PL 应提供统一的系统时间基准。

下列信息应尽可能基于同一时间基准进行标记或关联：

- 运动轨迹点；
- STEP/DIR 执行状态；
- 驱动器 RS485 返回数据；
- 报警事件；
- 限位事件；
- Homing 状态；
- 诊断采样窗口。

这样可使后续 NPU 能够将“运动命令”和“驱动器实际工况”进行时间对齐。

---

## 3. 四层功能模型

### 3.1 L1：任务 / 监控层

L1 主要运行在 PS 侧。

主要职责包括：

- 自主任务管理；
- 系统状态机；
- CAN 通信；
- 外部命令解析；
- HMI 服务；
- 参数管理；
- 任务加载；
- 日志管理；
- 运行模式管理；
- 故障信息汇总。

外部 CAN 节点只需要发送高级命令，而不应承担连续的低层轨迹控制。

典型高级命令可以包括：

- Home；
- Enable；
- Stop；
- Pause；
- Resume；
- Move to Cartesian Position；
- Linear Move；
- Run Task；
- Set Speed；
- Set Acceleration；
- Query State。

### 3.2 L2：规划 / 运动学层

L2 主要运行在 PS 侧。

主要职责包括：

- 路径规划；
- 轨迹规划；
- 梯形或 S 曲线速度规划；
- 笛卡尔空间插补；
- Delta 逆运动学；
- 工作空间检查；
- 软限位检查；
- 轨迹合法性检查；
- 运动段生成。

系统的基本运动数据链路为：

`任务目标 → 路径 → 时间参数化轨迹 → 笛卡尔插补 → Delta IK → 关节目标`

对于 Delta 三轴：

`XYZ → θ1, θ2, θ3`

对于辅助轴 M4：

M4 不属于 Delta 逆运动学，应作为独立辅助轴处理。

在 Motion Scheduler 之前，Delta 三轴目标和 M4 目标再合并为统一的四轴运动目标。

### 3.3 L3：确定性运动 / 采集层

L3 主要运行在 PL，并与 DDR/PS/NPU 数据链协同工作。

PL 主要职责包括：

#### 运动执行

- 四轴同步调度；
- STEP/DIR/EN 生成；
- 多轴同步；
- 固定周期轨迹点消费；
- 位置增量计算；
- 脉冲时序控制；
- Homing；
- Limit；
- Alarm；
- Watchdog；
- 基础安全状态机。

#### RS485 状态采集

RS485 Master 必须实现在 PL 中。

其职责包括：

- 多从机轮询；
- 地址字节处理；
- 帧构造；
- 收发控制；
- CHECKSUM-8 生成；
- CHECKSUM-8 校验；
- 超时检测；
- 从机状态解析；
- 数据有效性判断；
- 时间戳标记；
- 采样数据缓存。

RS485 总线连接四台驱动器，逻辑上属于一主多从共享总线。

驱动器通过地址字节区分。

#### 数据缓存

PL 产生和采集的数据通过 AXI / AXI-Stream / DMA 等机制写入 DDR。

主要缓存内容包括：

- 轨迹数据；
- 运动命令；
- 驱动器状态；
- 时间戳；
- 报警；
- 诊断所需时序数据。

### 3.4 L4：驱动 / 执行层

L4 包括：

- 四台闭环步进驱动器；
- 三台 Delta 主运动电机 M1/M2/M3；
- 一台辅助轴电机 M4；
- 驱动器内部编码器；
- Delta 机械机构；
- 末端执行机构或辅助轴机构。

M1/M2/M3 共同完成 Delta 机器人三自由度平移运动。

M4 为独立辅助轴，可根据具体机械配置用于：

- 夹爪；
- 旋转轴；
- 导轨；
- 升降轴；
- 其他工具轴。

闭环步进驱动器完成自身电机闭环控制。

当前 M1/M2/M3 暂定为 Makerbase MKS SERVO42C TTL 版，各自加装 TTL 转 RS485 模块；M4 型号及机构未定，不阻塞现阶段需求整理和通用四轴接口设计。

已确认安全职责：SERVO42C 负责单轴闭环驱动和堵转自保护；FPGA PL 负责 Delta 整机回零、限位、联锁和停止策略；外部电路负责最终急停失能。堵转保护需按实际固件配置并验证，不能假定默认启用。

Makerbase V1.1 发布说明提示失能后外力移位再使能可能回到旧目标。重新使能前必须在专项规范中处理驱动内部目标、控制器位置与待执行轨迹的一致性；具体恢复策略、命令和顺序尚未冻结，不能假定驱动清零等同机械回零。

---

## 4. SoC FPGA 顶层职责划分

### 4.1 PS

PS 是机器人自主控制和高级算法的主要执行端。

建议承担：

- Autonomous Task Manager；
- Robot State Machine；
- CAN Protocol；
- HMI；
- Path Planner；
- Trajectory Planner；
- Cartesian Interpolator；
- Delta IK；
- Workspace Check；
- Motion Command Generation；
- NPU 数据预处理；
- NPU 推理结果管理；
- 参数管理；
- eMMC 文件管理；
- 系统日志。

第一阶段不要求将 Delta IK 硬件化到 PL。

PS 可以先用 C/C++ 实现原固件等效运动学模型，并通过测试向量与原固件进行比对。

### 4.2 PL

PL 是系统硬实时核心。

建议承担：

- 四轴 STEP/DIR/EN 输出；
- 多轴同步；
- 轨迹点定周期执行；
- Homing Controller；
- Limit Controller；
- Alarm Handling；
- Watchdog；
- RS485 Master；
- Address/CHECKSUM-8/Timeout；
- Timestamp Engine；
- Telemetry FIFO；
- AXI 接口；
- DMA/Streaming 数据接口；
- 硬实时安全响应。

PL 不应负责复杂自主任务规划。

PL 也不应依赖 Linux 或 PS 调度精度维持 STEP 脉冲连续性。

### 4.3 DDR

DDR 作为系统运行时共享数据存储区域。

主要用于：

- 轨迹缓存；
- 运动段缓存；
- Telemetry Ring Buffer；
- RS485 时序数据缓存；
- NPU 输入窗口；
- NPU 中间数据；
- 日志缓冲；
- PS/PL 数据交换。

推荐采用环形缓冲区保存持续产生的遥测数据。

### 4.4 eMMC

eMMC 用于掉电保持数据。

主要保存：

- 系统程序；
- FPGA 配置相关文件；
- 机器人参数；
- 运动学参数；
- 电机参数；
- Homing 参数；
- 校准数据；
- 用户任务；
- 轨迹文件；
- NPU 模型；
- 日志；
- 故障记录。

机器人机械参数不应长期硬编码在运动算法源码中。

### 4.5 NPU

NPU 用于非硬实时智能诊断和后续智能功能。

第一阶段主要面向：

- 工况识别；
- 异常检测；
- 故障分类；
- 健康状态评估。

数据源应优先使用带时间戳的结构化时序数据。

建议的数据链路为：

`驱动器状态 → PL RS485 Master → 时间戳 → DDR Ring Buffer → PS 数据预处理 → NPU`

NPU 不直接产生 STEP/DIR。

NPU 的输出首先返回 PS，由 PS 结合机器人状态机决定后续行为。

---

## 5. 主要通信与互连

### 5.1 CAN

CAN 是系统对外主要通信接口。

连接对象可以包括：

- PC；
- PLC；
- 无线模块；
- 其他机器人；
- 上层控制系统。

CAN 主要承担：

- 高级任务；
- 参数配置；
- 状态查询；
- 故障信息；
- 维护和调试。

CAN 不负责维持机器人底层实时脉冲。

### 5.2 AXI

PS 与 PL 之间使用 AXI 系列接口。

建议逻辑上区分：

#### 控制 / 状态通路

用于：

- Start；
- Stop；
- Mode；
- Homing；
- Reset；
- Status；
- Alarm；
- FIFO Level；
- 参数配置。

可以采用 AXI4-Lite 等轻量寄存器通路。

#### 高吞吐数据通路

用于：

- 运动轨迹；
- 运动段；
- 驱动器 Telemetry；
- 带时间戳采样数据。

可以采用：

- AXI-Stream；
- DMA；
- DDR Buffer。

具体 IP 和互连结构以后续器件和实现平台为准。

### 5.3 RS485

RS485 为驱动器状态采集总线。

拓扑为：

`PL RS485 Master ↔ M1 / M2 / M3 / M4`

四台驱动器共享总线并使用地址寻址。

协议至少应具备：

- 地址字段；
- 命令字段；
- 数据字段；
- 校验字段；
- 超时处理。

实际协议字段以后续驱动器协议文档为准。

2026-10-06 用户已确定当前 SERVO42C 协议校验为 CHECKSUM-8（参与校验的字节累加后取低 8 位），本文原有 RS485 CRC 表述据此统一修正。M1/M2/M3 的目标是 STP 运动期间持续轮询状态，实际固件并发能力、TTL 转 RS485 换向时序与报文字段仍需验证。M4 协议在选型后单独确认。

PL 在有效应答通过 CHECKSUM-8 校验后，应对数据附加系统时间戳。

### 5.4 STEP / DIR / EN

四个驱动器分别使用独立的：

- STEP；
- DIR；
- EN。

总计：

`4 × 3 = 12`

根实时控制信号。

全部由 PL 直接产生。

---

## 6. 关键系统数据流

### 6.1 自主运动数据流

`任务 → PS Task Manager → Path Planner → Trajectory Planner → Cartesian Interpolator → Delta IK → Joint Targets → AXI / Buffer → PL Realtime Engine → STEP/DIR/EN → Drivers → Motors`

### 6.2 驱动器状态采集数据流

`Drivers → RS485 → PL RS485 Master → CHECKSUM-8 Check → Timestamp → Telemetry FIFO → DMA → DDR`

### 6.3 NPU 诊断数据流

`DDR Telemetry Window → PS Preprocessing → NPU → Diagnostic Result → PS State Machine`

### 6.4 外部监控数据流

`Robot State / Diagnostic Result → PS → CAN → External Node`

---

## 7. 原固件的定位

现有 Delta MCU 固件不作为 RTL 翻译对象。

其主要价值是：

- 提供已有运动学行为参考；
- 提供机械参数参考；
- 提供坐标系定义参考；
- 提供角度到步进脉冲换算参考；
- 提供基础运动流程参考；
- 作为 Golden Model 的来源。

新系统应实现“功能链路等价”，而不是“源码语句等价”。

建议将原固件中的 Delta IK 和关键运动学行为提取成软件 Golden Model。

后续 PS 实现必须通过测试向量验证与 Golden Model 的一致性。

现有固件位置：D:\Works\Embedded_contest\docs\Arduino_firmware

---

## 8. 建议实施顺序

项目实施应遵循“先建立确定性运动底座，再接入算法，再建立自主系统，再做智能诊断”的顺序。

### Phase 0：需求和接口冻结

目标：先固定系统边界，避免 PS 和 PL 并行开发过程中不断修改接口。

需要确定：

- FPGA/SoC 器件；
- 开发工具名称与版本；
- 系统时钟；
- 操作系统或裸机环境；
- STEP/DIR/EN 电气接口；
- RS485 驱动器协议；
- CAN 物理层和协议框架；
- AXI 接口类型；
- 轨迹点格式；
- Telemetry 格式；
- 时间戳格式；
- DDR Buffer 结构；
- Homing 输入；
- Limit；
- Alarm；
- Emergency Stop 策略。

交付物：

- System Interface Specification；
- PS/PL Interface Specification；
- Motion Point Format；
- Telemetry Frame Format；
- Error Code Definition。

### Phase 1：建立 Golden Model

目标：从原 MCU 固件提取并验证运动学行为。

完成：

- Delta IK 软件模型；
- 机械参数整理；
- 坐标系确认；
- 角度单位统一；
- 角度到步数换算；
- 工作空间测试；
- 批量生成测试向量。

推荐工具：MATLAB、Python、C/C++。

输出：

`XYZ → θ1, θ2, θ3 → Step Position`

测试集。

此阶段不接实体电机。

### Phase 2：PL 四轴基础运动内核

目标：完全绕开 Delta IK，先证明 PL 可以可靠控制四轴。

完成：

- STEP Generator；
- DIR；
- EN；
- Position Counter；
- 4-Axis Synchronizer；
- Motion FIFO；
- Homing；
- Limit；
- Alarm；
- Watchdog。

测试方式：手工向 PL 输入四轴目标步数。

例如：

`[10000, 5000, -7000, 2000]`

验证：

- 方向正确；
- 脉冲数量正确；
- 四轴同步；
- 停止行为正确；
- Homing 正确；
- Limit 正确。

### Phase 3：PS ↔ PL 运动链路

目标：打通 PS 生成运动点、PL 确定性执行的完整数据路径。

完成：

- AXI Control；
- Motion FIFO；
- DMA 或 Streaming；
- FIFO Underflow 处理；
- PS 轨迹预缓存；
- PL 固定周期消费。

建议验证目标：PS 自主产生一段四轴位置序列，PL 无需 PC 实时参与即可完整执行。

### Phase 4：PS Delta IK 与笛卡尔运动

目标：完成：

`XYZ → IK → Joint Targets → PL`

链路。

完成：

- PS Delta IK；
- 工作空间检查；
- 笛卡尔直线插补；
- 轨迹规划；
- 速度规划；
- 角度到 Step Position；
- 与 Golden Model 自动比对。

建议首个实体任务：

1. Home；
2. 移动到安全点；
3. 在固定 Z 平面走一个矩形；
4. 回安全点；
5. 停止。

整个过程不依赖外部上位机实时下发轨迹。

### Phase 5：PL RS485 采集系统

目标：建立确定性驱动器状态采集链路。

完成：

- RS485 UART；
- DE/RE 控制；
- Poll Scheduler；
- Address；
- CHECKSUM-8；
- Timeout；
- Frame Parser；
- Timestamp；
- Telemetry FIFO；
- 多从机轮询；
- 异常应答处理。

验证：

- M1/M2/M3/M4 地址正确；
- CHECKSUM-8 错误能够检测；
- 超时不会阻塞运动控制；
- 每帧有有效时间戳；
- RS485 采集不会影响 STEP 输出。

### Phase 6：DDR 遥测环形缓存

目标：将连续运动数据和驱动器反馈数据可靠写入 DDR。

完成：

- Telemetry Record；
- Ring Buffer；
- DMA；
- Buffer Overflow 处理；
- PS 读取接口；
- 时间窗口提取。

验证：运动过程中持续采集数分钟，不丢失、不覆盖未消费数据、不干扰运动实时性。

### Phase 7：CAN 与自主任务系统

目标：系统达到“工业控制器”式运行方式。

完成：

- CAN Service；
- Task Manager；
- State Machine；
- 参数配置；
- 本地任务加载；
- eMMC；
- Fault Handling；
- Autonomous Mode；
- Remote Command Mode。

验证：CAN 节点只下发高级任务。

任务开始后，即使 CAN 节点不再持续发送轨迹数据，机器人仍能独立完成任务。

### Phase 8：NPU 工况 / 故障诊断

目标：利用时序运行数据构建诊断能力。

完成：

- Telemetry Window；
- Resampling；
- Normalization；
- Feature Construction；
- NPU Inference；
- 工况识别；
- 故障分类；
- 异常评分；
- 诊断结果回传 PS。

NPU 不直接控制执行机构。

所有 NPU 结果必须先进入 PS 的 Robot State Machine。

### Phase 9：高级二次开发

基础平台稳定后，再逐步增加：

- S-Curve 优化；
- Jacobian；
- 关节速度约束；
- 奇异区处理；
- 更高插补频率；
- 连续轨迹；
- 圆弧插补；
- 视觉定位；
- 自主抓取；
- 在线轨迹调整；
- 预测性维护；
- 驱动器健康评估；
- 多机器人协同。

---

## 9. 开发与验证原则

每一个模块都必须先单独验证，再集成。

推荐遵循：

`Reference Model → Unit Test → Simulation → Hardware Test → Integration`

特别是以下模块必须具有自检测试：

- Delta IK；
- STEP Generator；
- Four-Axis Synchronizer；
- Homing；
- RS485 CHECKSUM-8；
- RS485 Parser；
- Timestamp；
- Motion FIFO；
- Telemetry FIFO；
- DMA Buffer；
- CAN Parser。

运动学和轨迹算法需要具备可重复的输入/输出测试向量。

PL 模块需要具备 self-checking testbench。

禁止仅通过“实体机器人看起来能运动”判断算法正确。

---

## 10. 当前暂不纳入首版范围

以下功能不作为第一阶段必需功能：

- FPGA 内 Delta IK 硬件加速；
- FPGA 内浮点数学单元优化；
- SoC 主控直接实现电机级编码器位置闭环；
- NPU 直接参与硬实时运动控制；
- 高级视觉闭环；
- 动力学模型；
- 力控制；
- 多机器人协同。

这些能力应在基础运动平台稳定后再评估。

---

# 11. Agent 行为约束

## 11.1 架构约束
- 不得擅自改变 PS / PL 职责边界。
- RS485 Master 必须位于 PL。
- RS485 为三线半双工通信。
- STEP / DIR / EN 必须由 PL 直接生成。
- NPU 不得直接控制执行器。
- CAN 不承担底层脉冲级实时控制。

## 11.2 开发流程约束
- 遇到无法确定的架构选择/具体实现方法选择时，不得猜测或盲目推断，优先询问用户意见。
- 所有交互式提问的超时时间不小于300秒。
- 修改 RTL 前先阅读对应接口规范。
- 新增 PL 模块必须同时提供 self-checking testbench。
- 修改运动学算法必须通过 Golden Model 回归测试。
- 不得在未验证单模块前直接集成系统。
- 不得隐藏失败测试或跳过回归测试。
- 开始工作前在工作区创建 git 仓库，完成模块后续提交到 git 并写 commit message。
- 本文档中的推荐实施顺序仅供参考，以用户实际要求为准。

## 11.3 文件和代码约束
- RTL 全部使用 Verilog 编写。
- 规定寄存器地址管理方式。
- 规定错误码管理方式。
- 规定配置参数来源。
- 规定生成文件和手写文件边界。

## 11.4 变更控制
- 新建或删除目录/文件前需取得用户许可。
- 修改已冻结接口前必须说明原因、影响范围和迁移方案。
- 不允许无理由重构已经验证通过的模块。
- 不允许为了“更优雅”而改变对外可观察行为。

---

<!--
建议在这里补充类似以下约束：

## 11.1 架构约束
- 不得擅自改变 PS / PL 职责边界。
- RS485 Master 必须位于 PL。
- STEP / DIR / EN 必须由 PL 生成。
- NPU 不得直接控制执行器。
- CAN 不承担底层脉冲级实时控制。

## 11.2 开发流程约束
- 修改 RTL 前先阅读对应接口规范。
- 新增 PL 模块必须同时提供 self-checking testbench。
- 修改运动学算法必须通过 Golden Model 回归测试。
- 不得在未验证单模块前直接集成系统。
- 不得隐藏失败测试或跳过回归测试。

## 11.3 文件和代码约束
- 规定目录结构。
- 规定 Verilog/SystemVerilog/C/C++ 风格。
- 规定寄存器地址管理方式。
- 规定错误码管理方式。
- 规定配置参数来源。
- 规定生成文件和手写文件边界。

## 11.4 变更控制
- 修改已冻结接口前必须说明原因、影响范围和迁移方案。
- 不允许无理由重构已经验证通过的模块。
- 不允许为了“更优雅”而改变对外可观察行为。
-->
