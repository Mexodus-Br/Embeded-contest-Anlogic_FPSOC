# Delta Golden Model — Phase 1

这是可在开发主机运行的 C++ 参考模型，边界为 **IK 输入 XYZ（mm）→ 三轴关节角（rad）→ 三轴绝对目标步数**。不连接电机，不生成 STEP，不处理 PL 的命令位置差分，不实现 M4、G-code、实时插补或回零控制。遵守工作区 AGENT.md、HARDWARE.md、PHASE0_CONSTRAINTS.md 的 PS/PL 分工。

当前验证基线是 **host_float32_double64**：对未经改写的原 C++ 运动学/步数源码做宿主编译，并对比提取模型。不能称为 AVR/Mega 执行结果或原 HEX 的逐位仿真。原理、异常和后续确认项见 [SOURCE_ANALYSIS.md](SOURCE_ANALYSIS.md)。

## 运行与复现

本次实测：Windows PowerShell、MinGW GCC 15.1.0 (`D:\mingw64\bin\g++.exe`)、Python 3.10.11。仅使用 Python 标准库，无第三方依赖或下载步骤。下列命令从 `D:\Works\Embedded_contest\dev` 执行：

```powershell
python golden_model/build.py
& .\golden_model\build\delta_model.exe --config golden_model/configs/firmware_reference.cfg xyz 0 0 -140
& .\golden_model\build\delta_model.exe --config golden_model/configs/firmware_reference.cfg angles -0.48 -0.48 -0.48
python golden_model/tests/test_regression.py
```

`build.py --compiler D:\mingw64\bin\g++.exe` 可以指定已有编译器。测试入口每次先校验基线哈希、重新编译模型与原源码参考程序，然后测试；编译或测试失败会非零退出。默认 CLI 参数集中在 `src/model.hpp::Config`；`firmware_reference.cfg` 是带来源注释的完整参考配置，建议始终显式传入。

批量输入每行一个 `xyz x y z` 或 `angles thetaX thetaY thetaZ`，空行及以 `#` 开头的行跳过。输出一行一个 JSON：

```powershell
@'
xyz 0 0 -140
xyz 30 20 -200
xyz 0 0 0
angles 0.001 -0.001 0
'@ | & .\golden_model\build\delta_model.exe --config golden_model/configs/firmware_reference.cfg --batch
```

单点退出码：0=有效数值结果，1=计算无效，2=参数/配置/输入语法错误。批量模式的计算无效由每条 JSON 报告，整批正常处理退出0；语法错误退出2，之前输出可能已产生。未提供 `--config` 时使用编译内参考默认值。输出字段包括：

| 字段 | 语义 |
| --- | --- |
| `axis_order` | 原电机 `X_high,Y_low,Z_rot`，不是笛卡尔分量，也不是确认后的 M1–M3 接线 |
| `angles_rad` | 三轴原算法角度；非有限值以 JSON `null` 表示 |
| `ik_valid`, `ik_reasons` | 逐轴负判别式、零分母或非有限异常；不证明机械安全 |
| `K`, `discriminant` | 原二次式分母系数及判别式，便于边界/异常分析 |
| `unrounded_steps`, `rad_to_step_factor` | 取整前 float 值及换算因子 |
| `steps_valid`, `step_reasons` | 非有限或整数范围失败 |
| `absolute_steps` | 仅全部轴有效时输出三轴绝对目标；任一失败时为 `null` |
| `valid` | IK 与转换均有效；仍不是允许驱动电机的判据 |
| `firmware_box_allowed` | 原插补矩形检查单独报告；不参与 IK 数值有效性，不能作为安全工作空间 |

初始点实测 `angles_rad ≈ [-0.4760361612,-0.4760361910,-0.4760361910]`，`absolute_steps=[-1090,-1090,-1090]`。计数初始化 `-0.48 rad` 换算为 `[-1100,-1100,-1100]`，两者存在10步差异。

## 配置替换

复制 `configs/firmware_reference.cfg` 为 `golden_model/configs/my_robot.cfg`，替换已测量或确认的字段，并在注释中写明实物版本、测量方法及来源，再用 `--config` 指定。配置是 `key=value`，支持 `#` 注释；未知、重复、非有限、非法整数和无效参数域拒绝。允许局部覆盖，其余字段沿用 `Config` 参考默认值；正式校准建议维护完整文件。

- 有效机械参数来自 **robotGeometry.cpp 内常量**，不是 config.h 中已被忽略的140/160/50。更改配置得到的是该原算法在新参数下的输出，不证明参数已校准。
- 齿数比4.5/1、电机200整步/转、RAMPS细分16来自原 config.h。**它们不代表 MKS SERVO42C 的最终配置**。
- `angle_offset_*_rad` 在 float 加法后乘因子；`step_offset_*` 在向零截断后做整数加法。这是显式配置扩展，原参考值全部为0。原 `-0.48` 不应填作角度偏移。
- `inverse_*` 保留原 DIR 元数据，改变它不改变绝对目标数字。电平时序和接线不在本模型范围。
- `target_min/max` 默认使用 AVR `int` 的 `[-32768,32767]` 作为参考保护域；可以配置其他宿主 int 范围，**不冻结 PS/PL 字段位宽**。范围外或非有限转换不执行整数强转，原固件在这些情况下没有可移植的 C++ 数值行为。

API 在 `src/model.hpp`：`xyz_to_angles` 与 `angles_to_steps` 独立提供。直接使用 API 时必须提供合法配置；CLI 的配置读取负责域校验。

## 自动回归与向量

`vectors/firmware_host.json` 是固定随机种子 **20261007** 的1272条持久参考向量，期望值由独立可执行程序直接调用原源码产生，**不调用提取模型**。测试不自动重写期望值，还会重新运行原源码并核对持久期望，防止基线悄然变化。

```powershell
# 明确要求重新生成基线时才运行；之后审查向量 diff。
python golden_model/generate_vectors.py
# 默认写 vectors/firmware_host.json；另存副本：
python golden_model/generate_vectors.py --output golden_model/vectors/reproduced.json
```

测试覆盖初始点、正常点、X镜像及正负方向、矩形边界、杆长可达边界与半角公式分母极点附近、不可达与非有限/溢出、整数和半步附近相邻 float 值、正负截断、偏移、方向元数据、配置替换/非法配置、1000条固定种子随机点、201点连续 XYZ 轨迹。轨迹只是确定的几何采样，不复刻 Arduino 插补时间曲线；`build/trajectory.jsonl` 同时给出各点角度、步数及相邻变化。

2026-10-07 实际运行结果：**10个测试方法通过，0失败、0错误**。1272条与原源码宿主角度完全一致，有效826条、按诊断无效446条；无效用例的预期失败被断言，未隐藏或跳过。有效结果步数逐整数相等。2388次独立杆长检查最大残差 **0.000036533 mm**；201点轨迹最大相邻变化 **0.007532183 rad / 18步**。完整结果由测试生成到 `build/test_report.json`，构建元数据在 `build/build_info.json`，本次交付的永久结论见 [VALIDATION.md](VALIDATION.md)。

暂定测试判据及数值差异的解释见 VALIDATION.md；不能将测试残差或轨迹连续性阈值冻结为机器人精度、速度或安全指标。

## 文件与限制

`baseline/` 保存13份按字节复制的依赖/调用链源码和路径/SHA-256清单；`src/` 是模型与 CLI；`tests/` 是 Arduino无IO桩、原源码入口和回归；`configs/` 为参数；`vectors/` 为持久期望；`build.py`/`generate_vectors.py` 为手写工具。`build/` 和 Python 缓存局部忽略。版权与原始格式保留说明见 [NOTICE.md](NOTICE.md)。

结论限定为本次编译环境下的源码提取一致性及理想几何证据。AVR浮点/数学库执行、实物精度、机械校准、限位/碰撞、安全工作空间、驱动器细分/方向、M1–M3映射及启停位置一致性均未验证；下一阶段确认清单见 SOURCE_ANALYSIS.md。
