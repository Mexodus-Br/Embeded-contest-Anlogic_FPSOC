# PS 主机开发进度

2026-10-22，依据交接包 v1.1 和用户确认的 D1。独立移交目录包含新应用 web/ps；端口优先 18083，若占用由启动器选择空闲端口。全部执行为 simulation，没有访问硬件或部署设备。

|阶段|状态|证据|
|---|---|---|
|差异核对|完成|ps-comparison.md；两段引用对话及包内 77 文件已读取|
|原始参考测试|通过|1272 向量、10 Golden、3 MOT2、GP C、17 遥测、1088 单字节损坏；77 文件字节不变|
|共用契约 D1|用户已确认|ps-contract-proposal.md；精确实现字段补充到 ps-api.md 与机器 schema|
|PS-06 规划/codec|主机实现完成|直接链接原 Golden/C decoder；梯形/三角形、逐点/禁入线段/步频检查；7 项纯库测试|
|PS-02 命令服务|主机实现完成|独立 ExecutionBackend；预览绑定、成功及拒绝身份重放、期限、互斥、独立 STOP、重启 unknown、方向超时及撤销|
|PS-03 参数/任务|主机实现完成|不可变版本、原子文件、运行快照、绑定参数、示教/多点/重复；文件失败及往返测试|
|PS-04 遥测|主机实现完成|冻结帧回放，valid/stale/unknown、代际、缺采，失败不补零，xyz_feedback=null|
|PS-05 日志|主机实现完成|有界队列/轮转、稳定分页/详情、认证 JSONL；内容及慢客户端/磁盘/队列/STOP 测试|
|PS-01 HMI|主机实现完成|两种模式、显式执行、多点任务、参数、遥测与日志；真实浏览器完成交互验收及截图|
|HTTP/schema 联调|14 项通过|实际响应逐个按 schema 校验；build/partner/service_report.json|
|ARM64 构建|通过，未运行|静态 ELF64 AArch64、无解释器段；build/partner/arm_report.json|
|Linaro 7.5、实板后端及硬件验收|未进行|不属于本次主机模拟授权；接入点与待测清单见 ps-handoff.md|

浏览器验证限制：内嵌浏览器曾显示导出已交给浏览器保存；自动等待下载事件获取本地路径超时，没有宣称已核对其落地副本。HTTP 实际下载已解析并逐字段/逐字节核对固定快照、中文、多行和后续新增隔离。普通浏览器的文件落地仍可按验证记录中的步骤复验。

编译器 Zig 0.13.0，Windows 11、Python 3.12.7；原始 GCC-only smoke 的等价宿主 runner 已明确记录，未声称实际 GCC/Linaro/ARM 执行通过。实现、资源限制、测试和交付入口见 [ps-handoff.md](ps-handoff.md) 与 [ps-validation.md](ps-validation.md)。
