# Motion Point Format — 候选 v1

2026-10-09：有效 STEP 上升沿/闲置低、DIR=1 正向，故障与新边沿同拍优先禁止，以及 REBASE/停止/失能/复位契约已按用户确认更新 DECISIONS。pl_motion 实现基础单目标执行通道，不消费本页候选记录、未实现 duration 调度；本页 DDA/均匀槽/点结束等算法仍候选。

同日后续：用户确认四轴单点共同 Nmax 槽/余数分配及同槽对应边沿、整组预检、精确 duration 完成/统一停止。本批四轴 profile 已实现在 pl_motion，细节见 FOUR_AXIS.md；覆盖本页相应算法待定，不能把下文逐轴 Ni 均匀槽公式视为本批实现公式（本批槽数是共同 Nmax）。80B 布局、连续边界/END/暂停及本页其他草案仍候选。

## 1. 时间候选比较

| 方案 | 优点 | 代价/迟到语义 |
| --- | --- | --- |
| 配置固定周期P | 消费和RTL最简单；PS预插补 | 全点同P；变化需停机提交配置；欠流不能补旧点 |
| 显式相对duration（推荐） | 每点连续区间、零位移驻留；固定周期是所有duration相同的特例 | 字段与可行性检查；预缓存后START定义首区间，不受Linux发包抖动影响 |
| 显式绝对execute_tick | 外部时间协调 | 首点时钟/epoch、迟到/比较回绕复杂；不适合先做基础内核 |

用户已确认每点显式相对duration_tick、1MHz tick、signed64目标/位置和signed65差分。以下调度细节仍候选：首点开始时刻由START在PL接受的安全调度边界确定；下一点区间紧接上一点，无隐式空拍。duration包括DIR切换及脉冲高低约束预算，不在结束后追加未计时尾脉冲。实际消费周期和最小/最大duration仍TBD，不擅填1ms为性能规格。

## 2. 线格式

固定80字节、8字节对齐、little endian、二补码；全部保留位为0。轴顺序逻辑A0/A1/A2/A3，与实际M1/M2/M3/M4接线映射另行确认。软件映射配置在会话前完成，不以X_high/Y_low/Z_rot名字自动绑定。

| byte | bytes | 字段 / 候选语义 |
| --- | --- | --- |
| 0 | 4 | magic=0x31544F4D（字节MOT1） |
| 4 | 2 | version=1 |
| 6 | 2 | length=80 |
| 8 | 8 | session_id，PS每次连接/停止/错误恢复选择新非零值 |
| 16 | 4 | sequence，从0严格连续；不回绕，满前开新会话 |
| 20 | 4 | batch_id，PS任务关联，无重排序/隐式flush效应 |
| 24 | 4 | flags：bit0 END（最后一个点），其余0 |
| 28 | 4 | axis_mask bits0..3，本点参与轴；必须为已启用轴子集 |
| 32 | 8 | duration_tick，u64，>0且不超过配置可行区间 |
| 40 | 8×4 | target[0..3]，signed64绝对step |
| 72 | 4 | reserved=0 |
| 76 | 4 | CRC32/ISO-HDLC over bytes[0:76]，poly 0x04C11DB7/reflected 0xEDB88320、init/xorout 0xFFFFFFFF，refin/refout=true；check("123456789")=0xCBF43926 |

此CRC是候选PS/PL记录完整性校验，与RS485已确认CHECKSUM-8不同。CRC不代替AXI响应/DMA错误检查，亦不是安全认证。mask=0允许纯时间驻留；未参与轴target必须为0并完全忽略，不要求未初始化轴位置。

接收完整80字节和last、keep、CRC等校验通过才入FIFO。候选64bit流10拍，keep每拍0xFF，last仅第10拍。长/短包、部分keep、提前/缺失last都丢弃整包、记录错误并使运动session失效；不靠搜索magic在破损字节流里继续执行。批量DMA可传多点，边界契约见DMA文档。

## 3. 顺序和状态语义

START需已OPEN_SESSION、配置和position_valid、预缓存最低完整点数（TBD容量预算）、EN延迟满足。首点基于当时cmd_position，不自动重标为首target，不加十步补偿。PS先快照位置再规划；若位置在规划后改变则新session/重新规划。

重复点sequence（即使内容相同）拒绝且session失效，避免重播；乱序/缺号、旧session、END后再发点均拒绝，旧session丢弃并增加stale计数。传输重试应先查accepted_seq，无法确定则STOP并开新session。控制命令的transaction重复语义与运动点不同。

无效格式、越界（配置signed64软目标上下界）、不可执行频率/时长均不输出该点任何STEP；候选使会话失效并停止，不能跳过一条继续执行后续绝对目标。接收时查格式和目标界，执行时查当前真实delta/时序。预接收可基于目标估算负载，但不能据上一目标执行。

相对时间方案没有墙钟“迟到点”：区间边界无下一完整点即欠流，STOP、取消session。迟到到达的旧点不得自动恢复。PAUSE候选只在点边界生效并冻结消费，RESUME从下一点开始；急停/FAULT不等待点完成。零位移点合法，只等待duration；END完成是有计划结束，不报欠流。STOP后保留实际计数，队列/部分接收记录取消。

## 4. 可执行性、溢出与脉冲调度候选

目标和命令位置signed64；delta=sign_extend65(target)-sign_extend65(position)，范围[-(2^64-1),2^64-1]，不能用64bit减法或对INT64_MIN取abs。N=abs(delta)为unsigned64。每次更新position需先检查signed64界限。

令F=100MHz，已确认时间戳分频K=100，C=duration_tick*K，使用unsigned128或经checked-multiply后限定u64。H/L为STEP最小高/低cycle（均>0），S/Q为DIR setup/hold cycle，E为EN提前时间，R为最大STEP rate配置（pulse/s）。所有时序数值来自PS配置/经过驱动器实测批准；候选配置默认0且config_valid=0表示**未配置、禁止START**，setup/hold等参数是否允许0需按最终驱动契约确定。

候选保守均匀槽算法：N>0时，D=max(尚欠DIR hold+需要DIR setup，尚欠EN setup，首边沿前低电平预算)，M=C-D；必须C>D，floor(M/N)>=H+L，且N*F<=R*M。于是N_max=min(floor((C-D)/(H+L)), floor(R*(C-D)/F))；乘法用u128/checked arithmetic。N=0无除法，无DIR/EN改变。

首有效边沿at D；后续边沿at D+floor(k*M/N)，k=1..N-1；余数分配器实现避免直接大乘法，间隔至少floor(M/N)，每次active H、其后inactive≥L，最后边沿到区间末≥H+L。每个轴D不同可造成对应槽边沿偏差，需同步定义/公共预算D=max(all enabled D_i)及测试；推荐所有轴用公共D，具体DDA/相位算法仍Draft。

保守预算将每点末尾保留L，可能降低极限容量；冻结算法前可以证明更紧边界，但不能默默超越已验收时序。DIR保持以最后有效边沿为参考，若驱动手册以其他边沿定义，参数映射需修改并复核。DIR反向只能在inactive时，先满足hold再等setup；持续同向可不改DIR。计数发生于实际有效边沿，point_done还需区间结束及STEP inactive。

累加器、duration*K、N*F、R*M、序号和position越界均显式失败，不截断/饱和后执行。时间戳回绕不是允许超长duration的理由；跨回绕运动候选禁止。目标位宽64不等于允许2^64个脉冲在任意区间内执行。
> 2026-10-09 连续层补充：用户已确认 END/边界 PAUSE、显式 RESUME、逻辑 u32 sequence 与 stale 隔离、START 预缓存和边界欠预检取消规则，详见 DECISIONS.md 与 ../pl_motion/CONTINUOUS.md。以下候选线报文布局/CRC/容量仍 Draft。实现以预测端点预规划，但仅在提交时核对实际已输出 STEP 位置才执行；预规划不修改实际位置。边界需下一点**已预检完成**，只有完整点入 FIFO 不足以避免欠流。
