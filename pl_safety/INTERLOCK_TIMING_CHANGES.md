# SAF2时序优化变更位置与语义

2026-10-19，当前候选13。最终功能/资源/时序状态见INTERLOCK_HANDOFF.md；
本文件记录修改理由与可审核位置，不表示route或发布签核已经完成。
所有行号对应本轮源码；信号名/分支名用于后续行号变化时定位。

|文件与位置|修改与实际路径原因|边沿/兼容性|
|---|---|---|
|pl_motion/rtl/motion_service.v:123–135，safety_idle_q|把pulse-safe与完整空闲条件一起采样，移除edge_age/low_age宽比较经配置资格绕回执行器的组合路径|仅SAF2使用寄存空闲许可；当前AXI/命令/session/HOME fence立即撤销许可。空闲授予可保守等待一拍，停止/禁止STEP不流水；legacy仍用原full_safety_idle|
|pl_rs485/rtl/rs485_gp_regs.v:48–56，interlock_run/interlock_stop_commit|RUN直接导出唯一采集器寄存器；合法OFF fire独立输出，不再经有效RUN同时进入restart/保护解析|仍在原held AW/W且无BVALID的fire沿生效，精确地址、字节/零值预译码及拒绝规则不变；OFF当拍抑制新反馈超时，不清故障或WD|
|pl_rs485/rtl/rs485_gp_bridge.v:15、26，interlock_stop_commit|只转发上述内部提交事件，避免两份有效RUN状态|原事务、重试、退避、FIFO、revision、32B记录不变；无新PS端口|
|pl_safety/rtl/safety_motion_service.v:140–163，interlock_idle/monitor连接|SAF2不再重复组合pulse-safe，使用已寄存的完整排空资格；连接独立关闭事件|保留当前HOME owner及SUBMIT fence和实际EN失能检查；实际RUN/关闭事件均来自原采集器|
|pl_safety/rtl/safety_interlock.v:31–60，protection_record/feedback_axis/monitoring|固定0x3E格式直接生成逐轴位图，避免通用task编码再译码及其高扇出；关闭事件只抑制监测，不进入restart/在途保护校验|使用同一生成协议定义；原通用采集解析器未修改。无新增解析寄存级，同一实际提交拍有效；在途保护及WD仍有效|
|pl_safety/rtl/safety_controller.v:59–63、124、163、167、179、208、212，home_owner_q|新增1bit同拍所有权缓存，斩断state多位译码经monitoring/abort进入执行器的11级路径|仅SAF2使用缓存。与每个改变所有权的state赋值同拍更新，最后DRAIN排空覆盖优先级保留；不是对当前state再延迟一拍。legacy表达式不变|
|pl_safety/generate_top.py:52–80及四个interlock_*生成顶层|传递collector_stop_commit内部连线|七个既有窗口、原GP转换器、双DMA/HP0/HP1、外部针脚和时钟接口均保持|

## 边沿与代价的验证

- 监测器79项，包含OFF/期限/保护/WD同拍、恢复、u64回绕与耗尽。
- 未修改的通用解析器作为oracle：68728项固定译码差分，覆盖全部地址/查询组合、
  枚举/版本/status/长度字节与非法高payload位。
- GP 416项检查包含16种WSTRB×8类数据、AW/W错开及B/R背压，核对原OFF接受谓词。
- interlock_suite_route13_complete的原374项全部通过，含14×24停止相位、
  END/HOME完成/STEP候选同拍及逐拍完整排空资格、HOME所有权关系断言。
- interlock_route13_owner_projection的20480项独立检查，以合法状态及匹配缓存为
  归纳起点，穷举11bit有效谓词，检查真实RTL下一采样沿的原状态译码关系；层次注入
  仅在测试中。后续suite纳入此模块，合计375项。
- 真实受保护IP系统夹具在采样沿后继续核对所有权缓存与原状态关系，并保留禁止新
  STEP、统一时间、HP0/HP1并发及数据一致性断言。候选13保护/独立WD/单轴反馈超时
  三个场景均通过，证据为interlock_real_route13、interlock_real_watchdog13、
  interlock_real_feedback13；后两者使用非生产统一epoch跳转，不是完整2秒墙钟长度仿真。
- interlock_real_accepted13额外验证双端同拍接受：HP0读18/HP1写8，18拍背压并发，
  其中2拍同时接受HP0读/HP1写；随后再次背压，保护/排空及原数据断言均通过。

本轮声明状态总计2461bit，其中本次新增HOME owner缓存1bit；逻辑状态位不能代替
综合/布线FF利用率。候选13门级只读数据库审计确认新增缓存为1个AL_MAP_SEQ FF
（optimization/interlock_candidate13/owner_gate_result_r3.json）；最终比较报告分别列出
实际gate/route全顶层及相关模块的寄存器代价，布线复制代价另据实际结果记录。
没有修改STEP/DIR/EN唯一所有权、既有急停/限位/STOP沿、公共复位或DMA/DDR静止边界。

## 物理证据边界

route10完整实际顶层在原100MHz约束下setup -1.960ns、hold +0.020ns，失败证据保留。
候选11 gate -2.617/0ns、候选12 gate -1.964/0ns用于定位；两者后续物理优化已主动
中断，保留interruption.json、日志和数据库，不作为最终route验收。候选13现已从其同一
place.db完成恢复布线，综合/布局/布线和数据库审计均显式16线程并读回，原约束已恢复
且逐字节核对。最终route -2.173/+0.020ns，仍不满足setup严格大于1ns目标。
实际最差为原始反馈payload[30]合法性/保护停止路径到A1 DIR CE，10级、cell2.173/
net9.749ns；当前报告不能用门级generation路径或候选14模型替代。完整本轮资源和
路径见optimization/interlock_candidate13/ROUND_REPORT_20261019.md。
