# 接口复用边界与尚未冻结项

## 已冻结、不可自行改动

- 功能需求：PS_REQUIREMENTS_V1.md；mm/°、使能只预览、运行才执行、运动中使能即STOP、方向键及互斥、任务/手动不同的失联行为。
- 算法参考：Golden内部rad、原始参考配置/快照及精确向量；不是标定后工作空间，不使用旧firmware_box_allowed单独决定安全。
- 运动线格式：pl_interface/schema.json的frames.motion_stream_v2及motion_integration_profiles.gp_motion_v1；72B小端、绝对目标signed64、相对1μs duration、CRC、session/sequence及END保持。
- 遥测：rs485_gp_profiles.gp_rs485_v1和rs485_telemetry，加pl_rs485/schema.json/rate_design.json；原32B及外层64B保持。完整schema也含历史Draft，不把frames中的旧80/128B候选格式或未确认安全策略当正式接口。
- 寄存器/错误码来自schema生成定义；不要在新服务中重新手写一套数字。合作方无需实现GP访问，但可使用这些定义理解/解码快照。

## 参考代码与正式组件的差别

`reference/board/delta_scope.cpp`是已有Linux无电机测试实现，包内仅供阅读，不作为宿主构建目标，也不是正式命令服务。其文本socket协议、root UID要求、init中的维护REBASE/ENABLE、单点关节move、500ms例子和5μs/100kHz测试guards均不能直接扩展成未审批的网络API/实物参数。

`reference/board/motion_uapi.h`与`rs485_uapi.h`是当前typed ioctl边界的只读快照。合作方通过项目方批准的后端抽象或模拟源开发；项目方负责唯一设备owner、ioctl/Linux接入和全部DMA生命周期。

`pl_rs485/software/rs485_gp.c`及`rs485_telem.c`同时包含纯解码与回调写助手。合作方可复用纯解码并在内存mock测试；ARM/COMPLETE、GP配置/捕获/消费函数不是获准访问硬件的通行证，实际调用由项目方受控owner负责。

## 字节与数值

- `samples/telemetry_rtl_frames.hex`每行是Verilog 512bit向量的高位到低位十六进制显示。64B线性字节序需`bytes.fromhex(line)[::-1]`，不能把文本直接当字节流；既有C测试已按此还原。
- 64B外层小端，内含32B原bitvector；payload的解读复用既有C decoder。CRC保护封装，不能替代UART CHECKSUM-8。
- query33是接收命令脉冲，不是编码器位置；query30 carry/value分别保留，不能直接标成Delta末端XYZ；错误记录不是零反馈。
- current/target、command/feedback、valid/stale/unknown分别表达；坐标FK/标定尚未完成时不能以目标点填“当前实际坐标”。

## 需要集中确认后才能联调

需求第10节OPEN-01～08仍有效：正式HTTP/JSON/SSE、内部接口/权限、认证/会话、期限和方向刷新/超时/最大前瞻、参数/任务格式、有限/无限重复及循环返回、示教打点/坐标来源、规划限制/采样误差、日志/历史容量与持久性。

合作方负责提出可审查方案与模拟测试；项目方负责跨组件统一确认。没有答案的项不得静默填0/无限或套用scope参数。BSP尚未就绪也不授权合作方通过/dev/mem、任意shell或直接root socket绕过边界。
