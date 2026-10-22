# PS 主机基线验证登记

2026-10-22，Asia/Taipei。范围：Windows主机模拟与离线交叉编译。没有板卡部署、串口/VM连接、介质写入或机械运动；没有计算日志、导出、证据或目录哈希。

|检查|本轮结果与实际条件|
|---|---|
|主机构建|MinGW GCC/G++15.1.0，C++17，GCC尾部链接ws2_32/bcrypt，CLI及服务成功|
|完整入口|`python -B tools/run_host_checks.py` 六阶段全部exit=0，逐次输出保留；Python3.10.11、Node24.13.0、隔离jsonschema4.23.0|
|冻结参考|Golden1272：826有效/446预期无效，10项Golden、3项MOT2、GP mock、17帧回放及1088损坏拒绝通过|
|纯库|7项通过；独立公式、路径/时长拒绝、signed64 codec及遥测|
|原有服务/schema|14项通过；生成schema --check通过，新增字段纳入同一生成源|
|新增边界|5项通过，另含JS四场景：松键、STOP代际改变、boot改变、正常启动；无randomUUID及无安全熵的能力检测|
|连接/取消边界|4个SSE、长规划、普通工作槽耗尽与64个残缺头并发时STOP可接纳/完成；受控浏览器函数与实际HTTP服务联调，释放后无jog/start|
|日志重启|按实际已接收事件逐条比较重启前后列表、详情和JSONL；boot隔离、固定快照新增稳定、路径/未知boot拒绝、坏行/超长/截尾计数通过|
|后端隔离|hardware/非法模式拒绝启动，无模拟回退；模拟注入默认关闭且HMI/状态显示capability|
|Windows迁移运行|独立临时目录、不同cwd、端口冲突/备用端口、同目录实例复用、认证/资源/预览/回放/停止及清理通过|
|冻结副本|77个manifest列出成员（含manifest）与保留来件逐字节相同；不使用哈希|
|接口草案|ps_hardware_port.hpp经本机C++17语法检查；无设备实现，不声称硬件已接入|
|本机厂商Linux工具链|FD2026.1_SP1实际为Linaro GCC7.4.1-2019.02；`--target sdk --server`成功，ELF64/AArch64。不执行该产物|
|目标SDK/运行时|项目记录的Linaro7.5/Buildroot环境本会话未配置、未连接VM；未完成其编译或运行资格，不能以7.4替代|
|CMake|环境未提供cmake命令，入口保留，未执行验证|

SDK服务动态依赖libstdc++.so.6、libm.so.6、libgcc_s.so.1、libpthread.so.0和libc.so.6；readelf发现GLIBC_2.25、GLIBCXX_3.4.22、CXXABI_1.3.9等版本需求。尚未与目标rootfs核对加载器、共享库、内核getrandom或线程/资源条件，故交叉链接成功不等于可部署。

STOP单次观测如下，都是主机测试值，无硬实时/最坏界承诺，不用作生产时限：

|场景|STOP请求至测试确认停止|
|---|---|
|stop_during_slow_log_download|26.38 ms|
|stop_infinite_task|43.05 ms|
|stop_during_long_planning|33.13 ms|
|4_SSE_long_plan_ordinary_exhaustion_64_partial_headers_STOP|34.70 ms|

本地证据保存在`build/partner/`（源码提交只包含本登记，不纳入构建输出或运行日志）：host_checks_report.json关联每次带时间序号的阶段输出；reference_report.json、core_report.json、service_report.json、boundary_report.json、package_runtime_report.json、sdk-linaro74-current.log和sdk-elf-header.txt。run_host_checks会继续执行并记录失败阶段，不隐藏失败。

新增日志测试首次失败输出`boundary-run.log`保留：有界try-lock生产队列可能报告丢弃，原测试错误假设突发20条全接收；改为核对实际接收数、丢弃计数及内容一致性后通过（boundary-run-2.log及最终阶段输出）。原来件与integration审查的旧证据不改写。

尚未完成：真实SAF2/R5S2/MOT2 owner与完成/取消资格、生产参数、LAN写授权/非root启动器、目标7.5/Buildroot ABI、板端内存/CPU/并发/持久性以及实板LAN浏览器验收。独立Wi-Fi只读服务的既有验收不移记为PS运动控制验收，详见WIFI_ACCESS.md。

Git staged whitespace检查报告随件冻结参考源码及第三方许可证中的原有尾随空白；保留原字节，不为消除告警改写参考。ps_app/.gitattributes对冻结依赖和第三方源码关闭换行转换，其余文本固定LF，防止Windows检出后破坏参考库存字节与复测。
