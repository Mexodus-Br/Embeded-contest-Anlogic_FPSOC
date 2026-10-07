# Telemetry Frame Format — Draft v1

固定128字节、8字节对齐、little endian，CRC与motion同算法。所有保留字段必须0。每帧一种事件类型；反馈不是命令位置，缺失反馈绝不填成0冒充有效。

| byte | bytes | 字段 |
| --- | --- | --- |
| 0 | 4 | magic=0x314D4C54（TLM1） |
| 4/6 | 2/2 | version=1 / length=128 |
| 8 | 8 | session_id；无运动session时0 |
| 16 | 4 | telemetry_seq，生成事件时分配，丢帧也递增，允许u32自然回绕 |
| 20 | 2 | type：1 MOTION、2 FEEDBACK、3 SAFETY、4 COMM |
| 22 | 1 | axis：0..3，255表示整机/未映射节点 |
| 23 | 1 | node：1..255，0表示无RS485节点 |
| 24 | 8 | event_tick，事件采样时刻，不是DMA写DDR时刻 |
| 32 | 8 | sample_tick，最近一次有效反馈的完整帧校验完成时刻 |
| 40 | 8 | age_tick=event_tick-sample_tick；无有效样本时UINT64_MAX |
| 48 | 4 | motion_seq；无关联时UINT32_MAX |
| 52 | 4 | status：state bits0..7，subtype bits8..15，其余0 |
| 56 | 4 | validity：bit0 CMD_VALID，1 FEEDBACK_VALID，2 COMM_VALID，3 FRESH，4 RAW_VALID，其余0 |
| 60 | 4 | error_code，来自唯一候选规范 |
| 64 | 8 | command_position，signed64 step；CMD_VALID=0则字段0 |
| 72 | 8 | pulse_total，u64，初始化后累计实际有效边沿次数，不带符号；溢出饱和并报诊断 |
| 80 | 8 | feedback_raw，signed64驱动原始值；单位由feedback_unit定义，不伪造step换算 |
| 88 | 4 | feedback_unit：0未知/无反馈、1原始编码器count；更多单位需版本扩展 |
| 92 | 4 | driver_status，原始驱动错误/状态值 |
| 96 | 4 | poll_seq，节点轮询请求序号，u32回绕 |
| 100 | 4 | raw_length=0..16 |
| 104 | 16 | raw bytes（请求/应答诊断片段），超长保留前16并在driver_status解释截取；非完整帧不可当有效反馈 |
| 120 | 4 | reserved=0 |
| 124 | 4 | CRC over [0:124] |

运动事件subtype：1 START、2 DONE、3 CANCEL、4 SNAPSHOT；event_tick对应原子启动、完成、停止脉冲安全完成、快照捕获。命令位置和pulse_total同拍捕获。安全事件event_tick为经PL同步后首次锁存时刻（不是外部物理输入的精确发生时刻）；通信成功为最后字节完成并通过完整校验时刻；超时为定时器到期，CHECKSUM失败为检验判决时刻。RS485接收首字节时刻若需要留待扩展，不混称反馈采样真实电机时刻。

成功反馈：COMM_VALID/FEEDBACK_VALID=1；FRESH仅age<=configured_fresh_ticks且节点启用。校验/超时事件：COMM_VALID=0，保留最近有效样本则FEEDBACK_VALID可为1，age继续增长，FRESH必须0；首次失败无样本时sample_tick=0、age=UINT64_MAX、raw feedback=0且FEEDBACK_VALID=0。长期过期但最近请求成功的通信有效性与反馈新鲜度分别表达。timestamp epoch改变后旧sample无效。

axis与node通过配置映射，node enable独立，M4未选型可关闭轮询；映射不能据驱动地址等同物理轴索引。CHECKSUM-8参与字节范围以最终SERVO协议为准，当前只有低8位加和方式确认，不能把整帧一律相加冻结。波特率、字符格式、地址、DE极性、换向/首字节等待、超时/重试/轮询周期、寄存器解析与feedback单位均TBD。

遥测满时：候选不背压运动/安全/轮询时序，丢完整帧；seq造成缺口、drop计数饱和并IRQ；故障first_code/time和最新安全状态保存在寄存器，关键事件日志不能宣称绝不丢失。建议独立安全事件保留槽，容量及优先级待验证。普通反馈丢帧不自动停机；关键日志丢失是否停机列TBD。

CHECKSUM错误、轮询超时、驱动报警分开分类。推荐通信诊断可配置连续失败阈值、age阈值与各节点策略（WARN / STOP），默认未配置时禁止运动；**推荐不等于已确定一律停或忽略**。驱动报警与整机联锁关系、阈值、安全延迟预算需用户确认。运动执行始终与应答延迟解耦。
