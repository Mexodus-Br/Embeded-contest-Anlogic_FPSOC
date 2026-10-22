# D1 主机验证记录

日期 2026-10-22。宿主 Windows 11 10.0.26200，Zig 0.13.0，Python 3.12.7，jsonschema 4.23.0。所有测试均使用命名 fixture 或临时目录；不连接 FPGA、树莓派、串口、驱动或电机。

## 已通过

|范围|结果|证据|
|---|---|---|
|冻结 Golden|1272 参考案例：826 valid、446 invalid；原始 10 测试方法|build/partner/reference_report.json|
|冻结接口|生成定义 checks、MOT2 3 测试、GP C mock、17 遥测帧及 1088 损坏校验|同上；原源码/字节未修改|
|新纯库|7 测试方法；独立梯形公式、三角形/指定时长/停留、多段非法路径、未知起点、signed64/u64、MOT2 字节及 CRC|tests/ps_core.py；build/partner/core_report.json；最终运行 7/7|
|服务与存储|14 测试方法；实际响应按 JSON Schema 校验；身份/期限/权限、版本快照、磁盘失败、重启、SSE、模拟与 STOP|build/partner/service_report.json|
|ARM64|ps_core 和 ps_server 构建成功；ELF64、EM_AARCH64=183、小端、无 PT_INTERP|build/partner/arm_report.json；未执行 ARM 程序|
|输入完整性|压缩包内 77 个文件逐字节比较一致|arm_report.json / reference_report.json|

最终服务测试耗时约 21.2 秒。STOP 从 HTTP 请求前开始计时，到观察到 idle 结束：慢下载 40.89 ms、无限重复 35.33 ms、1000 点规划并发 43.97 ms；本轮均低于 D1 的 100 ms 主机 fixture 目标。它们不是实机 worst-case 或实时上界。

日志测试包含：队列满/丢弃标记、暂停写入时仍可查询详情、稳定分页及跨快照游标拒绝、认证及路径遍历拒绝、中文多行还原、连续两次导出字节相同、追加不混入、轮转、注入写失败、未消费完下载连接期间 STOP。命令日志关联 command_id/task_id；若入队发生短时争用，gaps/dropped 必须显式报告，不假定无损。

任务往返保留每点 duration/dwell 和参数绑定；运行中换参数仍用旧快照，选回旧版本才恢复匹配位置有效性。实际文件系统失败测试把目标目录位置放置一个测试文件，确认保存拒绝且当前版本/旧文档不变。方向测试包括过期刷新、旧序号不续租、释放 STOP 之后晚到的 start 不启动、会话注销手动停止而自主任务继续。

## 真实网页核对

内嵌浏览器已验证：未知位置禁止运行/示教；建立模拟参考后预览不运动；输入改变使运行按钮失效；显式执行并观察 completed；长任务运行中使能按钮变 STOP，按下后 cancelled；长按 X+ 及松开，当前 XYZ 改变后稳定，界面显示“模拟停止已完成”。

已在网页保存/加载三点任务，确认无运动，再预览并执行完成：路径 `(0,0,-140) → (5,0,-140) → (5,5,-140) → (0,0,-140)`，首轮 1.453554 s、146 段。参数新版本保存及切回、17 帧遥测的失败/陈旧/代际、日志筛选、详情、快照过期及下载反馈均已检查。截图见 ps-preview.png。

内嵌浏览器下载事件回传超时，未取得其本地保存路径，因此“浏览器落地文件与选定快照逐字段比较”未完成；HTTP 导出内容比对已通过。普通浏览器复验步骤：运行 launch_ps.ps1 → 日志 → 创建查询快照 → 下载 JSONL；首行 count 应等于后续事件行数，snapshot_id/boot_id/筛选和页面一致。不要把未取得的浏览器文件写成已解析。

## 未验证及不作的推断

没有 Linaro 7.5/板端 SDK 实编，没有 CMake 运行环境，没有 ARM 运行、FIFO/DMA 或真实 STEP 证据。Windows 的静止/完成来自模拟执行器，pulse_safe 不表示硬件输出已经测量。未验证浏览器所有尺寸/移动设备或板端最大资源占用。原 18082 教学仿真未在本轮重新做全套回归，且其模型本来就不与冻结 PL 等价。

汇总机器记录：build/partner/validation_report.json；交付页面截图：ps-workbench.png。这是封装前的验证记录和截图；封装后重新构建、目录隔离与启动验证见 ps-package-validation.md。移交目录不附带运行进程、数据和访问令牌。
