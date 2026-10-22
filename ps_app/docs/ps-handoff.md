# PS 主机模拟移交

采用用户确认的 D1，完成 PS-01～PS-06 的主机实现。输入包 77 个文件保持原样。本目录是独立移交根目录，旧工作台不参与本应用的构建或运行。差异见 [ps-comparison.md](ps-comparison.md)，API 见 [ps-api.md](ps-api.md)。

## 本机运行

从本移交目录双击 `启动.cmd`，或执行 `powershell -NoProfile -ExecutionPolicy Bypass -File tools/launch_ps.ps1`。默认优先 18083，遇到端口占用时自动选择 18083～18102 中的空闲端口；以启动器实际输出为准。`停止服务.cmd` 只关闭本目录启动的服务。启动器只启动本项目 C++ 服务，读取本地令牌并在页面载入时消费 fragment；令牌不进入 HTTP 请求路径、查询或日志。随后取得控制权，在“模拟条件与故障注入”建立模拟参考，预览，再显式运行。当前/目标分列；长按方向、松开停止；任务文件保存/加载不执行；日志可查询、分页、查看详情和下载。

原始静态产物就是 `web/ps/` 的 HTML、CSS、ES module，不需要 npm、CDN 或外网。新 PS 应用的路径图是 XY 投影。移交网页已去掉指向外层旧工作台 18082 的链接。

## 构建与验证

依赖：C++17/C11 编译器；复用项目内 nlohmann/json 3.11.3（MIT），原 Golden 和 C decoder/生成协议头。保留输入包原许可与 NOTICE；新页面不引入第三方前端库。构建脚本只需 Python 标准库；HTTP schema 测试额外需要 jsonschema。

```powershell
# ZIG 指向本机现有 Zig 0.13.0；也可直接用 --zig 路径。
python -B tools/verify_partner.py
python -B tools/build_ps.py --server
python -B tests/ps_core.py
python -B tools/ps_schema.py --check
python -B tests/ps_service.py
python -B tools/build_ps.py --server --target aarch64
```

未设置 ZIG 且本机有可用 GCC/G++ 时，本机构建使用 GCC。目标生成物在 `build/partner/native/`、`build/partner/aarch64/`；每次构建的参数记录在 build_info.json。也可使用 CMake 的 ps_core_cli/ps_server 目标，Golden 关闭优化、fast-math 和浮点收缩。当前机器没有可运行的 CMake，因此该入口未实测。

本轮 Windows 主机用 Zig 0.13.0 完成参考、纯库及 HTTP 验证；ARM64 用 aarch64-linux-musl 静态交叉构建，检查 ELF 机器类型和无解释器段。**没有运行 ARM 程序，没有用实际 Linaro 7.5/Buildroot SDK 验证，也没有板端测试。** 为 GCC 7 提供 filesystem TS 别名及旧 GCC 的 stdc++fs 链接，十进制解析不依赖较新的 from_chars；仍需项目方 SDK 编译确认。

## 模块与线程

|需求|文件|边界|
|---|---|---|
|PS-01|web/ps/|模式、预览/运行/STOP、参数/任务、遥测、日志；无设备接口|
|PS-02|src/ps_service.cpp、ps_backend.hpp/.cpp、ps_server.cpp|单执行 owner、HTTP/SSE、身份/期限/互斥；ExecutionBackend 可替换|
|PS-03|ps_service.cpp、ps_runtime.cpp|版本不可变、原子落盘、运行快照独立；保存失败不变更活动参数|
|PS-04|ps_core.cpp、ps_service.cpp|原 C decoder + 冻结帧缓存，无 DMA/GP owner|
|PS-05|ps_runtime.cpp、ps_server.cpp|有界异步日志、稳定查询/详情/认证导出；不控制运动|
|PS-06|ps_core.hpp/.cpp、ps_cli.cpp|Golden 原样、直线梯形/三角形、每段停稳、完整逐点检查、独立 MOT2 codec|

服务一个执行线程约 5 ms tick，一个日志写线程，最多 32 个连接线程，最多一个规划请求；文件保存互斥不持有运动锁。STOP 先递增原子 epoch，再由执行线程停止。预览、磁盘、网络不会持有运动锁；日志状态先读取再取运动锁，避免锁顺序把 STOP 绑到历史复制。所有模拟执行最终通过 ExecutionBackend，真实实现需提供已验证 submit、manual_target、request_stop、poll、status 与停止结果，不能仅替换 kind 标签。

最多 1000 任务点、有限重复 1～1000 或明确 until_stopped；一份规划最多 200000 段、1 小时，首次和循环路径分别预验证。JSON 内存对象开销较高，最大样本配置下可能占用数百 MiB；当前上限是主机 fixture，板端 RAM/CPU 峰值未测，部署前必须下调并以实测结果定额。主机采用日志/连接/命令身份的显式容量边界，不是硬实时服务。

## 运算与反馈的限制

Golden 保留 float32/double64 混合运算、轴顺序和向零截断。当前规划适配保留 Golden 参考的 int16 目标有效域，之后提升为 signed64；这不表示 MOT2 协议只支持 16 位。独立 codec 已测试完整 64 位极值。扩大规划目标域需要项目方另行确认，不能修改冻结参考换取更大范围。

工作盒/禁入盒显式配置，禁入盒使用整条线相交检查；IK/关节/分支连续性按不大于 0.25 mm、10 ms 的 fixture 采样验证。手动每个 tick 也检查中间 IK。采样不等同机械碰撞或连续奇异性证明。

模拟位置来自采样端点，**没有逐周期模拟真实 PL 的 Nmax 脉冲分配，没有编码器闭环，没有真实 FK/标定位置**。backend.pulse_model 明确为 not_cycle_accurate。旧工作台的 pulse/FK 模型与包基线存在差异，不自动转作真实反馈。

## 数据、权限与板端待接入

默认本地数据 `runs/ps/`，访问令牌 `.cache/ps-token`；CLI 可传 `--port`、`--data`、`--token-file`。服务仅监听回环地址，无 root、设备文件或串口权限。工作目录须为带 scenarios/、web/ps/ 和冻结遥测样本的项目根。令牌及日志目录权限使用宿主账户设置；此配置仅用于本机开发。

项目方后续负责：Linaro/SDK 编译与资源测试；root socket/UAPI 单 owner、真实 EN/START/STOP、FIFO/完成序号、session/REBASE；DMA 与遥测代际传递；可靠 HOME/联锁、标定和真实坐标有效性；板端超时、速度、容量、权限和凭据分发；断电持久性及实机 STOP/STEP 安全。禁止把模拟 reference_position 当作回零。

本轮未部署树莓派/FPGA。未来按项目约定先完成本机验证，部署目录只放生产程序、配置和必要运行文件，不带 tests/、探测脚本、编译缓存或旧环境产物；清理限定本项目。回退主机新应用只需停止它，旧 18082 工作台不受影响；参数/任务旧版本保留，失败运行不自动重试。
