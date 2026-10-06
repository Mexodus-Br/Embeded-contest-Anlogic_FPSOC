# 原固件追踪、推导与待确认项

核对日期：2026-10-07。原目录 `D:\Works\Embedded_contest\docs\Arduino_firmware` 只读；以下源码定位均指按字节复制的 `baseline/`，原绝对路径与 SHA-256 见 `baseline/manifest.json`。事实不等于实物已校准配置。

## 1. 源码事实：调用链与坐标

1. `command.cpp::cmdMove`：G91 为输入位移加当前坐标，G90 为输入加 G92 位置偏移；缺省坐标沿用当前值。`interpolation.cpp::setPosOffset` 为 `当前坐标 - 新显示坐标`，对 IK 没有旋转或轴交换。
2. `.ino::executeCommand` 中 G0/G1 经 `cmdMove` 送 `setInterpolation`；`.ino::loop` 每次 `updateActualPosition()` 后把 `getX/Y/ZPosmm()` 原样送 `geometry.set`。本模型的 XYZ 是这一层的数值，已经经过命令偏移；CLI 不替用户应用 G92。
3. 插补按 XYZ 欧氏长度计距离，速度注释为 mm/s，字段名及 config.h 注释明确长度为 mm。`INITIAL_X/Y/Z=(0,0,-140)`；旧 config 注释称其对应上臂水平、下臂垂直，但实际算法输出不是0 rad，不能沿用该注释作为当前姿态事实。
4. `isAllowedPosition` 只检查 `abs(X)<=110 && abs(Y)<=110 && Z>=-300`；`Z<=-140` 被注释，`R_MIN/MAX` 与杆夹角宏没有在这条调用链使用。拒绝时保留上一 XYZ 并结束插补；这不等于先运行 IK 再拒绝。
5. `.ino::loop` 映射见下表。原固件依次执行 `Rotate.update → Lower.update → Higher.update`，并非本项目 PL 同步脉冲执行的设计；本模型只提取目标数值。

| 模型数组索引 | 角度 getter | 原步进对象 | RAMPS 轴 / STEP / DIR / EN |
| --- | --- | --- | --- |
| 0 | `getHighRad` | `stepperHigher` | X / 54 / 55 / 38 |
| 1 | `getLowRad` | `stepperLower` | Y / 60 / 61 / 56 |
| 2 | `getRotRad` | `stepperRotate` | Z / 46 / 48 / 62 |

原 `high/low/rot` 命名来自现有源码，不能直接解释为某条杆的上/下自由度。四轴中的 M4 不参与这里的三个 IK 方程，也不继承旧固件 E0 导轨/夹爪参数。

## 2. 源码事实：IK 与参数来源

`RobotGeometry` 构造时保存 `ee_offset/low_shank_length/high_shank_length`，但 `calculateGrad()` 没有使用它们。真正使用的是局部 float 常量：

| 参数 | 有效值 | 原始来源 | 对比及状态 |
| --- | --- | --- | --- |
| R | 83.7 mm | robotGeometry.cpp | 旁注84.61，未启用 |
| r | 30.4 mm | robotGeometry.cpp | 旁注30.37，未启用 |
| L | 150 mm | robotGeometry.cpp | 依据方程解释为上臂长，待实物确认 |
| l | 280 mm | robotGeometry.cpp | 依据方程解释为下杆长，待实物确认 |
| 构造 LOW/HIGH/OFFSET | 140/160/50 mm | config.h | 被存储但不参与当前 IK |
| 主齿数/电机齿数 | 4.5 / 1.0 | config.h | 比值4.5，旁注90/20未启用；实物待确认 |
| 整步/转 | 200 | config.h | 注释NEMA17，不证明实物型号或步距角 |
| 微步 | 16 | config.h | 明确RAMPS1.4参考，不是SERVO42C最终参数 |
| 数值初始化角度 | -0.48 rad | .ino::setup/homeSequence | 重标位置计数，不是换算偏移 |
| HOME_STEPS X/Y/Z | 0/0/0 | config.h、endstop.cpp | 物理回零后的反向脉冲偏移；并不每次加到绝对目标 |
| INVERSE X/Y/Z | true/true/true | config.h、RampsStepper.cpp | 增加计数时DIR=inverse，减少时DIR=!inverse |

每轴先求 K/M/N，再计算 `theta = PI/2 - 2*atan((-M-sqrt(M*M-4*K*N))/(2*K))`。角度成员与返回值是 float、单位 rad；源码没有 `atan2`、另一解分支选择、相位展开、夹角/关节限位或异常返回。

`K/M/N` 声明为 double；XYZ、R/r/L/l 为 float。宿主上，第一/第二方程由 `sqrt(3)` 提升部分表达式到 double，第三方程在赋给 K/M/N 前多数运算仍是 float。因此即使中心点完全对称，高轴与另外两轴可能相差1个float ULP，不能擅自统一重写表达式消除它。

## 3. 推导结论：可人工复核的理想几何

设 `D=R-r`。按原方程可推出三个径向单位向量：

- high/X：`u=(0,-1)`；
- low/Y：`u=(-sqrt(3)/2,+1/2)`；
- rot/Z：`u=(+sqrt(3)/2,+1/2)`。

令 `q=u·(x,y)`，由半角二次式可得到杆长约束：

```text
x²+y²+z² + D²+L² - 2Dq
  + 2L(D-q)cos(theta) + 2Lz sin(theta) = l²
```

因此可在同一等效坐标系中构造肘点：

```text
elbow = (ux*(D+L*cos(theta)), uy*(D+L*cos(theta)), -L*sin(theta))
distance((x,y,z), elbow) = l
```

这里肘点已扣除末端半径 r；实际基座转轴径向距离为 R，末端连接点距平台中心为 r。该推导支持：XYZ 原点为理想对称基座平面中心，X/Y 在平面内，Z 垂直平面，输入的负Z在基座下方，正角度使上臂肘点向负Z运动。**这是方程推导，不是实物坐标/朝向确认**；实物观察侧、左右手系、轴朝向、三轴标签仍待核对。

手算中心样例 `(0,0,-140)`：`D≈53.3、L=150、l=280`，令 `C=z²+D²+L²-l²`，解 `D*cos(theta)+z*sin(theta)=-C/(2L)`。选原分支的解：

```text
theta = atan2(z,D) + acos(-C/(2L*sqrt(D²+z²))) ≈ -0.4760362 rad
```

独立检查只使用 Cartesian 肘点和杆长，不再调用二次式。理想杆长误差小不证明关节角选择符合所有实体装配约束，也不证明无碰撞。

## 4. 源码事实：角度到绝对步数

`RampsStepper` 构造把 `MAIN_GEAR_TEETH/MOTOR_GEAR_TEETH` 作为 float 参数、`MICROSTEPS*STEPS_PER_REV` 作为 int 参数送 `setReductionRatio`：

```text
factor(float) = gearRatio(float) * stepsPerRev(int) / 2 / PI
target(int) = rad(float) * factor(float)
```

宿主参考 factor=2291.831298828125 step/rad。整数赋值**向零截断**，不是 round/floor：例如精确因子1时1.999→1、-1.999→-1。`inverse` 不参与 factor 或 target，不应把其写成负步数换算。

`setup/homeSequence` 调用 `setPositionRad(-0.48)` 将当前与目标计数都重标为-1100；普通 `stepToPositionRad(theta)` 随后直接设置目标，没有减去-0.48。HOME_STEPS 在 endstop.cpp 中只用于限位触发后的物理退回脉冲，本模型不执行。

原工程留下 `arduino.avr.mega` 产物，其传统 AVR int 范围是16位；宿主 int 为32位。模型默认先按16位目标域检查，再转换宿主 int，不对非有限或超域值执行原来的未定义转换。这个保护是显式包装语义，**并不声称复刻 AVR 对未定义输入的某个返回值**。

## 5. 最小复现、影响及独立修正建议

以下问题保留原参考源码与数值算法。测试中对异常的诊断是包装层；未悄悄换成修正版 IK。

| 问题 / 复现 | 原行为与影响 | 单独建议，尚未实施 |
| --- | --- | --- |
| 输入 `xyz 0 0 0` | 原矩形检查接受；IK负判别式，sqrt→NaN；继续进入整数强转没有可移植结果 | 后续在IK前后做几何/关节/有限性检查，拒绝轨迹段 |
| 输入 `xyz 0 0 100` | 原Z上界关闭，因此矩形允许；不能认为允许即几何可达或安全 | 在实物工作空间确认后定义上界/软限位，不能直接恢复旧-140作为新规格 |
| 固定本任务测试配置R=r=0，输入 `xyz 0 0 -130` | 三轴K=0、M=0，半角公式0/0→NaN；附近极点可能数值敏感 | 独立版本研究稳定的atan2或线性退化解处理并明确分支；继续保留旧算法作为回归基线 |
| 默认参数在 `z≈-124.88017` 附近 | K接近0，减法相消/除小数；浮点profile差异可能显著 | 增加极点敏感性分析，勿用放宽精度容差掩盖 |
| 输入 `xyz nan 0 -200` 或 `xyz 1e30 0 -200` | 原无有限性保护；后者float平方溢出 | 输入与中间结果检查，失败原因和停止策略明确分层 |
| `setInterpolation(p0,p0)`，源码INITIAL点重复传入 | dist=0，v至少5，`tmul=v/dist` 为Inf；`t=0` 时0*Inf可能NaN，t>0可能跳至终点 | 独立后续修正零距离段直接结束；本阶段不提取时间插补，不宣称验证整机初始运行 |
| `RampsStepper` 构造中的 `stepperStepTargetPosition;` | 表达式无效，未初始化成员；在目标被设定前读它有未定义风险。宿主编译给出警告 | 后续明确初始化。参考测试先setPositionRad再读取，不触发未初始化读 |
| INITIAL IK与-0.48重标差10步 | 初始点IK=-1090计数，而重标是-1100；注释“0°”不能成立为数值事实 | 实物标定后确定零位、Homing基准和第一点规则，不把10步差擅自补成偏移 |

这些复现的 CLI 计算异常可通过 README 的 batch 命令或回归用例执行；零距离插补及构造初始化问题来自逐句源码分析，**没有运行原 Arduino 时间/IO 调用链**。本模型不处理 Jacobian，`K==0` 是算法表示的退化点，不自动等同机构 Jacobian 奇异；判别式接近0测试也不代替完整奇异性分析。

## 6. 下一阶段需要确认

不影响本次宿主参考提取的事项继续记录，不猜测为校准事实：

1. 实物R/r/L/l、杆连接结构、末端工具坐标偏移、坐标轴朝向与M1/M2/M3到原X/Y/Z的映射。
2. 实物电机步距、传动比、SERVO42C实际固件及微步/脉冲模式、DIR/EN极性与回零方向；不将RAMPS16直接迁移。
3. 机械零位、回零偏移、-0.48来源、PL命令位置初始化与第一目标一致性；启动未回零时的允许状态。
4. 当前装配的解分支、关节限位、碰撞条件、安全工作空间及奇异性判据；不能用本次理想几何容差作为安全限值。
5. 取得真实AVR编译器/数学库或可运行原产物的仿真环境，验证32位double路径；再选择PS的float/double策略及对应可接受差异。
6. 上游版权/许可证信息。本次保留原注释及字节，无据可确认更具体授权。
7. M4机构与参数独立确认；轨迹周期、目标字段宽度、PL调度另由专项规范确定。
