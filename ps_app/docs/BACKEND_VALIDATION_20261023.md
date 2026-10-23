# 真实后端离线验证登记

2026-10-23，Asia/Taipei。起点 `e7fcbc3`。没有接板、开串口、探测COM、改DTR/RTS、连VM、写SD/eMMC/QSPI或机械运动；没有计算文件/日志/目录哈希。原有其他任务工作区修改未纳入本任务提交。

|检查|结果和范围|
|---|---|
|新增 BSP 执行函数|41 项通过；从新增驱动实际 C 源码提取 ioctl/open/release，宿主寄存器模型验证。含旧快照ABI、无接管、递增/烧号、HOME/CLEAR ARG=0、ACK、独立STOP、权限、同fd过期后新OPEN、STOP后迟到HOME拒绝。不是 .ko、AXI 或硬件证明|
|真实后端假板卡|17 场景通过；正常执行、PL拒绝、执行超时、STOP写失败/等待超时、迟到完成/IOC、取消后不复活、在途取消quarantine、恢复失败仍quarantine、owner丢失、服务重启不接管、不续喂、容量拒绝、关键循环停滞、packet超时、代际改变、65条分包、起点身份拒绝、有限重复新session及Service来源隔离/故障恢复控制权|
|编码独立检查|假板卡对实际供给的72B包独立核对CRC32与axis_mask=7；原MOT2/Golden回归同时保留|
|来源/schema|实际硬件模式Service输出通过state/telemetry schema；XYZ/驱动反馈null，模拟注入即使构造时请求也关闭；模拟历史与真实日志保留各自来源|
|完整宿主入口|`tools/run_host_checks.py` 现含9阶段：build、hardware、safety_execution、serial、schema、reference、core、service、boundary；全部通过|
|原参考回归|Golden1272（826有效/446预期无效）、10项Golden、3项MOT2、GP mock、17帧回放、1088损坏拒绝通过；未修改Golden/冻结副本|
|原纯库/服务/边界|7项纯库、14项服务、5项边界通过，含原JS方向取消与普通连接耗尽时STOP接纳|
|本地行式适配|stdin/stdout模拟测试通过：共用Service控制权、普通队列并发STOP、request_id关联、未知位置/默认禁注入及EOF停止；未打开UART|
|本机构建|MinGW GCC/G++15.1，C++17；ps_core、ps_server、ps_control构建通过；node --check网页语法通过|
|Linux用户态编译|本机FD提供的Linaro GCC7.4.1，`--target sdk --server`通过，包含Linux真实ioctl分支与固定宽度ABI断言；ps_server只读ELF检查为ELF64/AArch64。产物未执行|
|目标环境|匹配Buildroot7.5 SDK、kernel .config/Module.symvers/构建输出与rootfs运行库核对未完成；新增内核模块未生成.ko；CMake命令不可用，未执行CMake构建|
|实板全部事项|NOT_EXECUTED，见NO_MOTOR_ACCEPTANCE.md。数字功能通过不关闭实物、电气、HOME、DDR drain、发布或机械许可门禁|

复现：在 `ps_app` 目录安装/使用已有 `requirements-dev.txt` 开发依赖及Node/GCC后运行 `python tools/run_host_checks.py`。单独运行 `python tests/ps_hardware.py`、`python ../bsp/safety_execution/test_driver.py` 可复查新增测试。假板卡直接使用编译的 HardwareBackend 和 Service，不是另一套状态机实现；它不能证明实际驱动、DDR、PL、供给最坏时延或机械停止。

交叉编译使用 `PS_CC` / `PS_CXX` 指向本机 Linaro 的 gcc/g++，执行 `python tools/build_ps.py --target sdk --server`。本机旧编译器在沙箱内出现 WinError623 DLL重定位错误，沙箱外 `--version` 及编译正常；HTTP回环在沙箱内遇到WinError10013，获准在沙箱外仅做localhost回归。没有把环境失败登记为业务通过。

保留的修复记录：首次缺jsonschema时使用已有审查副本隔离依赖，不改系统Python；健康租约与循环起始采样时间交错造成假超时已修复；保持原模拟health名称及“no fallback”错误约定后原边界回归恢复；STOP反馈绑定当前取消代际且只接受写后开始取得的快照；STOP与迟到HOME提交由新增BSP取消门约束。所有失败尝试的逐次日志保留，不纳入哈希清单。

本地证据在 `ps_app/build/partner/`：最新 `host_checks_report.json` 指向逐阶段唯一日志；`hardware_report.json`、`safety_execution_report.json`、`reference_report.json`、`core_report.json`、`service_report.json`、`boundary_report.json` 和 `sdk/build_info.json` 保存相应输出/命令。构建与运行日志不提交、不哈希；本登记提交可复现步骤与结果。旧2026-10-22登记为历史状态，当前实现和未完成事项以BACKEND.md为准。

九阶段完整检查通过后，最终健康门调整（仅关键poll可更新租约、动作出队后重新读取健康租约）又单独复跑假板卡17场景、真实schema、安全函数41项及网页语法，全部通过；最终用户态也重新交叉编译通过。相应补充输出为 `hardware-health-final.log`、`safety-execution-delivery.log`、`backend-arm-health-final.log`；行式适配的四项检查在 `serial_report.json`。

仍未实现的产品接入：真实XYZ/方向控制与获准参数；R5S2唯一owner向服务提供32B/64B原始帧只读发布。当前真实遥测仅安全/运动原始快照、命令位置及脉冲。原因和具体方案集中列在BACKEND.md，不将这些缺口记成“仅剩实板验证”。
