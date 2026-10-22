# 独立移交目录验证

2026-10-22。唯一交付根为 `PS_D1_移交_20261022/`。接收方整目录复制后可从顶层 `启动.cmd` 开始；不需要查找外层工程的 src、web、docs、build 或原始包。

## 已完成的目录验证

|检查|结果|
|---|---|
|本目录源码重编译|Windows x64 的 ps_core.exe、ps_server.exe 成功；Zig 0.13.0，严格浮点参数|
|原始参考回归|1272 案例，10 个 Golden 测试、3 个 MOT2 测试、GP C、17 遥测帧及 1088 损坏校验通过|
|纯库|7 个测试方法通过|
|实际 HTTP 联调|14 个测试方法通过，约 22.1 秒；实际响应按 schema 检查|
|schema 生成一致性|`python -B tools/ps_schema.py --check` 通过|
|原始输入|原压缩包的 77 个文件与本目录展开内容逐字节一致|
|第三方依赖|json.hpp、MIT 许可与来源清单记录的长度和 SHA-256 一致|
|运行目录搬移|复制到带空格的临时目录，从另一工作目录启动，成功|
|端口和进程隔离|显式指定占用端口会拒绝；自动选空闲端口；再次启动复用本副本进程；停止入口关闭该副本|
|实际运行依赖|HTML/CSS/JS 返回字节与副本一致；初始位置未知；建立模拟参考后预览 Golden 目标正确；17 帧冻结遥测可回放|
|数据边界|令牌、日志和数据全部生成于临时副本中；验收后副本和进程已清理|
|ARM64 产物|与此前成功交叉构建的产物逐字节一致；10 个 C++ 源文件未因封装而改变|
|开发机路径|src、web、tools、tests 中无开发机 `E:\codexonly` 路径依赖；构建报告保留历史实际命令，仅作证据|

本次 HTTP 测试的 STOP 延迟：慢日志下载 51.35 ms、无限任务 35.24 ms、1000 点规划并发 34.31 ms；均为主机 fixture 单次观测，不是实板或最坏实时界限。

运行目录搬移验证仅做认证、预览与遥测回放，没有发送运行命令。测试命令为 `python -B tests/ps_package.py`，只依赖 Python 标准库和 Windows PowerShell。首次测试的输出管道被后台服务继承导致等待；验收工具已改用临时输出文件，最终完整复验通过。

## 机器记录

- [参考回归](../build/partner/reference_report.json)
- [纯库](../build/partner/core_report.json)
- [HTTP 服务](../build/partner/service_report.json)
- [目录搬移与启动器](../build/partner/package_runtime_report.json)
- [ARM64 构建](../build/partner/arm_report.json)
- [汇总](../build/partner/validation_report.json)
- [最终封装检查](../build/partner/packaging_report.json)

`ps-validation.md` 的浏览器截图和交互记录来自封装前已核对的相同主机应用。封装时只移除了网页指向外层 18082 教学工作台的链接；没有重新进行整套浏览器视觉验收。浏览器下载落地文件比对、CMake、Linaro/Buildroot SDK、ARM 运行及真实硬件的未验证边界保持不变。

本交付目录仅保留源码、原始包、必要依赖、正式可执行文件、构建参数与验证记录。编译缓存、对象文件、调试符号、临时测试程序、测试输出数据和凭据不作为移交内容；需要时由随包脚本重新生成。
