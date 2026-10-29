# 本轮实现说明（中间检查点，未验收）

实际起点为07745a8。本轮不修改接口schema、生成定义、约束、保护IP、BSP或板卡。
当前产品源码为候选21；最终原10ns约束route setup>1ns、hold>=0以及物理/CDC审计
尚未完成，不能把本说明或任何布局估计作为验收通过证据。

## 已集成的内部改变

| 文件 | 改变及理由 | 对外周期 |
|---|---|---|
| motion_planner.v | 将2461位私有算术/记录数据移出复位和取消门控；原state/error/basic_ok仍按原边沿失效，每次请求覆盖依赖数据后才允许有效输出 | 不变 |
| motion_service.v | 2048位原子快照数据不复位，以原有效位屏蔽；命令owner蕴含原冗余空闲门；私有停止使用原RX谓词的精确Shannon分支 | 不变 |
| safety_regs.v | 2048位原子快照数据不复位；原valid/事务/响应复位保留，捕获前读取仍为0 | 不变 |
| safety_interlock_regs.v | 1024位原子快照数据不复位；原snapshot_id=0屏蔽旧epoch，ID及全字捕获规则不变 | 不变 |
| rs485_gp_regs.v | 1bit OFF请求寄存投影完整的NEXT邮箱状态，当前拍严格等于旧谓词；当前安全空闲资格仍直接参与 | 不变 |
| motion_fifo.v | 可选物理spare slot，原公开DEPTH容量不变；原指针/计数复位保留 | 不变 |
| continuous_motion.v | 仅原raw FIFO启用spare slot；逻辑64×421bit，物理65槽，准备FIFO仍8条 | 不变 |
| motion_executor.v | 1032位私有计划数据移出全局复位/停止CE；IDLE或旧boundary作推测装载，原控制过程唯一授予RUN、输出STEP/DIR/EN及更新位置 | 不变 |

源码层共8613位数据去复位，不代表相同数量的物理FF消失。候选21门级实测：连接异步SR
的AL_MAP_SEQ从26100降到20457（−5643，−21.62%）；FF仍需承载有效数据。工具默认
SRMODE=ASYNC而SRMUX=0的单元没有真实复位负载，未计入；这项统计也不包含PAD/其他
FF原语，不能冒充全芯片FF总数。Slice资源须另以最终route.area计算。

原始复位仍立即清除STEP/DIR/EN、位置/valid、安全/会话/IRQ/AXI状态和所有所有权。
GPIO仍为外部异步输入，经原两级同步进入检测；没有改动同步器、快速停止边沿或时钟。
所有内部实现改动均无新增接口周期，原启停、73/74拍预检、快照和传输语义继续逐拍比较。

## 存储映射门禁发现与修复

初次去除planner数据复位后，TD将原raw FIFO读捕获合并为11块ERAM。实际NORMAL模式
同址pop/push返回新数据，原厂模型与独立旧队头oracle不符。因此17/18/19候选被拒绝，
原失败与中断记录保留，不能用其RTL回归通过替代映射兼容性通过。

候选20/21保持count<=64、物理指针mod65。队列距离不变量保证非空时wr!=rd，因此任何
有效读写不会同址；不修改厂商模式或依赖未证明的RAM属性。5201项原厂模型检查包含
满64条同拍pop/push520次、单条刷新396次、flush/背压/回绕/epoch复位。

ram21_banks_r1核对实际11块RAM全部配置、地址、时钟和有效使能一致，RSTAMUX/RSTBMUX=0，
全部421位捕获输出恰好一次存在：metadata101、duration64、target256。TD按消费者别名
命名输出；未将未命名成plan_data的320位误判为丢失。前两次解析器失败记录保留。
模型使用实际导出的40bit银行参数；它补充整个真实DMA系统/RTL回归，并非整个门级
顶层仿真或资源相加。ERAM使用69块，对照原58块增加11，DSP仍6。

## 候选21当前功能证据

- equivalence_r4、stop_equivalence_r2：原07745a8逐拍参考，planner26547、service66799、
  寄存器10409拍；保持全部原断言，补充短复位和所有快照字/背压。
- off_candidate_r2：70317拍，包括65536组归纳边界；停止cofactor另覆盖65536种布尔组合。
- spare_fifo_r1：容量2/3/7/8/64/65；spare_equivalence_r1与spare_service_r1覆盖全内核/服务。
- executor_equivalence_r1、executor_service_r1：执行器325、服务66799拍全部连接输出等价。
- executor_stress_r1：192602拍、1375次启动、6230次脉冲事件（HOME3738），600次取消，
  包括极值、随机未接收数据、短复位及HOME/故障/边界竞争。
- interlock_suite_reset21_r1：最终产品源码375项原安全/HOME测试全部通过。
- interlock_regressions_reset21_r1：最终产品源码33项原运动/接收器/GP/RS485/遥测回归通过。
- real21_r1：三个真实原厂GP、双DMA及HP系统场景串行通过：protection/watchdog/feedback_timeout。
- spare_ram21_model_r1、ram21_banks_r1：实际映射的容量、冲突及全421位连通性通过。
- software21_r1：原C11严格编译、GP mock、17帧RTL/C交叉解码与1088个逐字节损坏拒绝，
  原IRQ set-wins/屏蔽/W1C、错误完成测试，以及旧schema/生成数值兼容检查全部通过。

## 仍在调查的候选与验收边界

memory_candidate_r1为未集成的准备队列存储写入分离方案。只有私有payload允许在flush
边沿推测写入；原有效握手、指针、计数、失效及STEP控制保留。它已通过原FIFO独立
scoreboard的12种参数组合、原内核993拍/服务66799拍逐拍比较、375项安全/HOME测试，
正在reset_gate22完整真实顶层中仅做门级综合，须先确认实际收益再决定是否集成。

reset_path20/21完整P&R和reset_baseline16_r1优化前独立完整物理对照仍在执行。
baseline16的44份RTL/header逐字节（仅规范化行尾）等于07745a8；使用保留gate检查点的
独立副本，不修改旧工程/日志。所有TD综合/P&R/数据库审计均显式16线程并读回。
最终还须提交gate/place/route、全网Data/CE/reset/clock负载、拥塞、check_timing/CDC、
关键交付源码/IP/约束身份及Git。日志/数据库/临时与历史证据不计算哈希。

生产PROFILE0禁启，SYN-5066受保护S2MM、外部RS485时序、实际安全引脚/电气/MTBF、
实物速度与输入资格、机械HOME/停止/复电、BSP DMA/DDR quarantine与板测仍独立开放。
本轮不生成部署镜像，不进行REBASE/ENABLE/START或任何板卡操作。
