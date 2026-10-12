# 实际验证记录 — 2026-10-07

## 2026-10-12 GP 最小契约冻结与定义检查

用户确认 `gp_control_probe_v1`；本次只落实唯一 JSON 规范、生成工具/定义及契约说明。实际运行 `python pl_interface/generate.py --check`：4 个派生文件逐字节一致；`python pl_interface/tests/test_interface.py`：8 项通过，含 C 编译、完整定义对照、非法 profile 引用/映射/时钟/reset/strobe 变异拒绝及首轮无 MOTION/DMA 特性检查；`python pl_interface/tests/check_verilog.py`：Icarus 编译/仿真实际核对 822 常量通过。运行于正常本地进程环境，无自动重试/跳过。`git diff --check` 通过。

与本次修改前 Git schema 比较：所有旧寄存器偏移/属性、旧 opcode、error/state 数值及 frame 布局保持；IRQ_PENDING/MASK 仅新增 TEST bit7，另有四个空位寄存器和 NOP。Global SNAP 序号 reset 仍为草案 0，profile override 生成 0xFFFFFFFF。Golden Model 文件与运动 RTL 未修改；本次未重跑运动波形/Golden 算法测试。

以上是规范/生成定义一致性验收，**不是 GP RTL/AXI 握手/快照硬件/IRQ 路由或板级验收**。新 profile 标为 USER_CONFIRMED_IMPLEMENTATION_PENDING，部署仍 NOT_DEPLOYABLE；需要新增自检 RTL、适配器集成、10ns STA、实际 HPF/DTS 地址/IRQ 核验及板级 MMIO/IRQ 证据。既有运动时序结果见 pl_motion/TIMING.md。

2026-10-09 后续记录：原 Icarus 崩溃复现，PATH/TMP 隔离和工具升级均不能证明沙箱内稳定；普通进程环境中原 12.0/独立 13.0 各完成 50 次编译/运行和完整单轴仿真。最终默认原 12.0 的独立 HDL 入口实际核对 772 常量通过。check_verilog.py 改用 pl_motion/sim_tools.py 的统一 fail-fast 调用；历史失败保留，下文“不含运动 RTL/HDL异常未解决”描述属于 2026-10-07 快照。最新单轴结果与尚未验证范围见 pl_motion/VALIDATION.md；无板级验收。

同日四轴追加：用户确认共同主槽/对应边沿及单点 scope 后，四轴 12 组自检通过，9,710,041 检查、3,360 安全扫描、840 复位扫描；同槽逻辑输出边沿偏差 0 cycle，非实板验收。接口 7 项、schema 重生成 4 文件一致及实际 HDL 772 常量再次通过。详见 pl_motion/VALIDATION.md 的四轴追加节，连续 FIFO/END/暂停未实现。

Windows PowerShell / Python3.10.11 / MinGW GCC15.1工具链。本次未实现运动RTL、Linux驱动或BSP，未连接电机。测试命令从工作区根运行。

| 实际检查 | 结果与限制 |
| --- | --- |
| `python pl_interface/tests/test_interface.py` | 最终7个方法全部通过，0失败/0错误/0跳过；C11 `-Wall -Wextra -Werror`实际编译并执行 |
| 字段边界/独立wire布局 | signed64最小/最大/-1、u64/u32上界、little endian、完整80B布局与独立struct.pack比较；C读取负数并重编码，CRC一致 |
| 非法记录 | motion每个截断长度0..79、telemetry0..127、额外字节、CRC损坏、magic/version/length、保留位、非法mask/目标、零duration/session、无反馈/新鲜度/年龄与raw填充被拒绝 |
| 规范冲突 | 地址重叠/未对齐、位域重叠、重复错误值、frame overlap/gap注入均失败 |
| 跨语言定义 | 140个候选寄存器、25个错误值、15个命令及全部字段，共772个生成常量：C编译运行值、Verilog受限字面语法解析值与唯一JSON逐项一致；这项**不是HDL仿真** |
| 执行数学 | 人工时序参数检查极限signed65差分、时长乘100溢出、容量边界/反向/零位移/未配置时序/频率拒绝；不是脉冲波形验证 |
| Golden数值样例 | 4条有效持久输出核对原source_id和三轴绝对步数；完整JSON→hex样例匹配；未改算法/参数/期望，也未运行新的运动学回归 |
| `python pl_interface/generate.py --check` | 4个派生文件与schema逐字节一致；生成不包含时间/环境路径，重复生成不变 |
| `python pl_interface/vendor_audit.py` | 只读27份本地源码/工程文件，记录路径/SHA256/相关行；BSP压缩包顺序读取、不落盘解压；未运行厂商工程 |
| motion/telemetry CLI decode | 已实际解码样例hex，含负目标、缺失反馈age=UINT64_MAX及通信错误 |

## HDL工具异常，未隐去失败

早期一个定义快照曾通过Icarus编译/vvp常量输出比较；其后多次调用出现进程崩溃`3221225477`（Windows signed显示`-1073741819`），没有可定位的HDL语法诊断。尝试相对路径、明确backend、PowerShell启动和分块测试源，均未可靠解决；不能据偶发通过认定工具稳定或最终定义已完成HDL编译验证。

独立入口`python pl_interface/tests/check_verilog.py`保留完整编译/仿真检查，任何编译器失败非零退出，无自动重试/跳过。最后实际运行该入口仍报上述进程崩溃。默认宿主一致性测试明确只做Verilog字面定义核对；此拆分避免将工具可用性混同字段一致性，没有将失败HDL检查伪装成通过。后续须修复/替换可信仿真环境，再运行该入口及真正RTL testbench。

## 未验证的硬件行为

AXI AW/W/B/AR/R握手、WSTRB副作用、CDC/复位释放/mailbox原子性、FIFO背压/丢帧、DMA TLAST/simple模式/Linux DMAengine配套、DDR/cache一致性、IRQ触发/路由、100MHz及1MHz时钟实际实现、STEP高低/DIR/EN时序/同步<50μs、外部急停/回零/计数对应引脚、RS485 STP并发和安全恢复均未验证。编解码、字面定义和整数可行性不能证明其中任何一项。

DDR1.35V与示例1.5V、旧工程/IP与当前TD/FD版本差异继续为板级问题；无需改接口算法来掩盖它们。

首个PL模块开始前最低还需：明确有效STEP边沿与对应DIR正向、接受计数/故障同拍优先级及停止时序细节，审查相关机器字段与模块契约。参数化STEP模块可先保留数值TBD，但接驱动前必须给H/L/setup/hold/EN延迟和最大频率；调度器还需duration范围、对应边沿规则/测量点及初始位置建立门。GP/DMA集成分别需地址表、CDC/reset和Linux/IP配套批准，不要求现在冻结所有外设细节。
