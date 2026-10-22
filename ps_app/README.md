# PS 主机软件基线

2026-10-22，Asia/Taipei。接收来源：`../deliverables/PS_D1_移交_20261022/`，原来件保持不动。本目录是可编辑、可复测的集成基线。范围是主机模拟，未批准生产参数、LAN 运动权限、真实设备后端或板端发行。

## 目录与依赖

- `src/`：C++17 规划、codec、命令服务、模拟执行器和 HTTP 服务。
- `web/ps/`：离线页面；`scenarios/ps-host.json`：明确的测试参数。
- `tools/`：GCC/Zig/SDK 构建、schema 生成、主机验收和 Windows 启停。
- `tests/`：纯库、原有服务、边界回归和 Windows 迁移运行测试。
- `ps_partner_v1_1_20261022_005289b/`：随件冻结 Golden、PL 定义、C decoder 及测试依赖的字节保真副本；不要在这里修改冻结协议或 Golden。
- `docs/`：D1 原接口说明及生成 schema；本轮差异见 `INTEGRATION.md`、`BACKEND.md`、`WIFI_ACCESS.md`、`VALIDATION.md`。
- `build/`、`runs/`、`.cache/`：本地产物/测试证据/运行数据，不纳入源码提交。日志、导出和测试证据不计算哈希。

需要 Python 3.10+、GCC/G++（C++17）、Node.js（前端回归）和 `requirements-dev.txt`。可在本目录的独立环境安装：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -B tools/run_host_checks.py
```

完整检查顺序为构建、schema、Golden1272/参考测试、纯库7项、服务14项和新增边界测试。服务测试只使用回环临时端口，结束时关闭自己启动的服务；失败日志逐次保留。测试需要允许本机监听，不访问板卡、串口、VM或网络设备。现有 review 的隔离 jsonschema 依赖也可通过 `PYTHONPATH` 复用，本轮未修改系统 Python。

## 构建与运行

```powershell
python -B tools/build_ps.py --server
python -B tools/ps_schema.py --check
# Windows独立迁移运行验收（临时副本与回环服务）：
python -B tests/ps_package.py
powershell -NoProfile -File tools/launch_ps.ps1 -SimulationInjection
powershell -NoProfile -File tools/stop_ps.ps1
```

`-SimulationInjection` 只用于模拟验收。不带该开关时仍为模拟后端，但禁用参考位置、故障、日志突发及遥测回放注入。CLI 同样要求明确选择：

```powershell
build/partner/native/ps_server.exe --backend simulation --allow-simulation-injection true --port 18083
```

服务工作目录必须是 `ps_app`，资源按该目录加载；数据默认 `runs/ps`，认证令牌默认 `.cache/ps-token`。`--data`、`--token-file` 可配置。未指定 `--backend` 或选择 `hardware` 都拒绝启动，不自动回退，不接触设备。默认只监听 `127.0.0.1`，Host/Origin 校验仍限回环；本轮没有开启 LAN 运动控制。

SDK 构建使用实际编译器路径，生成到 `build/partner/sdk`；不把交付中的 ARM 文件当本轮结果：

```powershell
$env:PS_CC='<target-sdk>/bin/aarch64-linux-gnu-gcc'
$env:PS_CXX='<target-sdk>/bin/aarch64-linux-gnu-g++'
# 仅在 SDK 要求时设置 PS_SYSROOT；不要指向主机头文件。
python -B tools/build_ps.py --target sdk --server
```

Linux SDK 路径显式链接 pthread/stdc++fs，兼容 GCC7 filesystem TS；Windows 的 ws2_32/bcrypt 只在 native Windows 构建中链接，且位于对象之后。可另用 CMake（本轮是否验证见 `VALIDATION.md`），目标 SDK 需由 toolchain 文件指定 C/C++ 编译器、sysroot 和查找范围。

`scenarios/` 的速度、加速度、采样、脉冲预算、超时、工作盒及所有容量均为 host fixture，不作为生产参数。生产接入须批准配置与后端资格，并另行完成板端验证。
