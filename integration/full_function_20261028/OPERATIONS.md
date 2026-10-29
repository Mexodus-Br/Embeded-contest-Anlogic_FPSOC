# 首版全功能镜像：后续实板验收步骤

本次只制作镜像。以下步骤是后续验收记录模板，不表示已执行，也不授权本轮写卡、上电或运动。用户负责断电、接线和上电；不操作 eMMC/QSPI。每阶段失败即 STOP，保留原始值、身份和日志；不扩大 HOME 范围，不增加二次接近或自动重试。

## 1. 隔离与身份

后续另获当次写卡授权并核对介质后，由用户保留回退卡、断电并隔离 STEP/EN 或电机。启动时只观察，不自动 HOME/ENABLE/RUN/重放。读取：

```sh
cat /etc/full-system-identity.json
cat /etc/home-calibration-config.json
uname -r
cat /proc/cmdline
ls -l /dev/bsp-motion /dev/bsp-saf2-exec /dev/bsp-rs485
ps-local state
ps-local telemetry
```

核对交付 manifest 的源码提交、完整 CONFIG_ID、功能配置 runtime_calibrated_motion、100MHz、M4 禁用与 wifi1 内核。真实后端无设备必须报错，无模拟回退。初始 XYZ 未知、无 owner、无任务重放。设备 root:root 0600，认证令牌现场首次生成在 `/etc/ps-hmi/token`，分发镜像无个人 Wi-Fi 凭据或令牌。

Wi-Fi 使用镜像既有 STA 配置流程（`bsp/wifi/README.md`）；在板端确认实际 IPv4 后，把该具体地址写入 `/etc/ps-hmi/bind-ipv4`，维护停稳并重启，浏览器访问该地址的 18083 端口。默认 loopback，不用 0.0.0.0，不放宽 Host/Origin/CSRF。网络配置、标定和任务均可板端持久化，无需为填写 PS 参数再烧卡。

## 2. 隔离安全链与 HOME 波形

取得控制权后按步骤显式执行并逐条读回：

```sh
ps-local action configure
ps-local action feedback_on
ps-local action open
ps-local state
ps-local telemetry
ps-local action clear
```

确认三轴实际地址 A0→E0、A1→E1、A2→E2，485 五类反馈源时间、generation/revision 正常且保护项新鲜健康；确认 owner/心跳。隔离状态由受控开关触发 HOME，检查 STOP、急停、限位、心跳丢失、485故障/断线/RUN-off 均停止实际输出且不会被迟到数据恢复。需要急停时由用户硬件急停/断电，不依赖网页。

HOME 搜索 DIR000、退离111，三阶段100脉冲/秒/轴，STEP高31.25µs、低至少31.25µs，DIR/EN守卫各500拍。搜索最多500步或10秒，任一先到失败；已闭合轴先150步预退离，正式退离150步，各3秒超时，稳定释放20ms。触点参考-150、正式退离后0，不是机械0°或编码器零点。M4无输出。

## 3. 近限位 HOME 与真实参数录入

隔离通过且用户确认接线、16细分、4.5:1、近限位500步可安全命中和150步退离空间后，才进入电机验收。显式 `ps-local action home`，逐轴记录触发/退离/失败原因、计数、0x30原值、0x33脉冲、PL时间、快照和代际。不得自动重试。

网页“参数版本”→“新建实测标定文档”。模板的未测物理量为 null，不能直接保存。按实际测量填写：

- `reference_id` 与正式退离姿态 `home_joint_deg`（Golden角度约定）；逐轴 `encoder_home` 的 carry/value、带符号 `encoder_units_per_joint_deg`，解释固定为 signed_turns_plus_u16_fraction。
- `pl_sign` 为逐轴 ±1；原厂 Golden 几何和4.5×200×16基准保持不变，`golden` 必须为空对象。
- 三轴实测机械最小/最大角度、两侧正余量、跟随容差、软件角度边界；边界必须落在机械范围减余量内，余量大于跟随容差。
- 机器 XYZ 包围盒、实测 XY 椭圆安全包络及余量、禁止盒；均以正式退离机器零点为基准，与用户工作零点无关。
- 初测速度/加速度可降，均不得超过20mm/s和20mm/s²；脉冲间隔至少63µs、段守卫至少32µs；位置采样间距至多0.05mm、角度步长至多0.1°。
- 新鲜度最多500ms、允许的三轴采样偏斜；依据实测485周期设置更严格值，不能用增大期限掩盖缺采。

保存新版本只完成校验/存储，不生成位置有效性。HOME完成、反馈稳定且停稳至少200ms后点击“验证当前 HOME 与标定”，查看映射查询。当前姿态须由0x30映射角度→验证FK得到；与PL计数偏差超容差或反馈陈旧立即撤销资格。用独立机械测量验证数个小位移点和正负方向，不能只根据软件自洽判定物理映射正确。

机器XYZ = FK(当前编码器角度) − FK(HOME正式退离角度)。PL目标 = 逐轴符号 × (Golden目标步数 − Golden HOME步数)。两套参考必须分别记录；0x33、目标点、HOME_DONE均不是实测XYZ。

## 4. 小范围 XYZ、方向与双坐标

先以更低速度/加速度和很小行程测试。网页预览包含首段、每段及循环末点返回首点；机器域、关节角、IK和脉冲预算必须全部通过。指定时长太短应拒绝，不能偷偷加速。显式运行后观察实测轨迹与最终误差。

方向每次只按一个键，松开、失焦、断网和控制权超时均实测停止；恢复连接不恢复运动。普通STOP后可显示可靠停稳位置/设零，但下一次执行仍须显式“恢复运动运输”；故障可能使HOME/标定资格失效，按实际原因重新建立，不能盲目恢复。

在非零机器位置停稳，点击“标定用户0点”：工作XYZ变为0，机器XYZ/原PL计数/EN保持不变且无运动；先前预览失效。再次检查机器边界没有随原点移动。

## 5. 示教、任务、日志与历史

示教数个工作点，保存/加载版本化任务，先单次再有限两次重复；检查首段与循环返回。改变工作零点后旧任务帧绑定应拒绝，重新示教/保存/预览后才能运行。取消、故障、断网、重启均不得复活旧任务，加载文件不代表执行。

查询并下载JSONL日志，按boot/命令/任务关联开始、停止原因及结果。遥测同时检查latest快照和“HP1/DDR原始历史窗口”：原始64B、源时间、代际/修订、缺序号、陈旧、窗口退休数必须可解释；有界窗口不代表从启动起的完整历史。

中断不确定RX后buffer保持quarantine。不得以延时、HALTED、PL drained替代HP1/DDR写静止证明；先保留证据，再根据驱动允许的显式恢复路径处理，不自动复用不确定buffer。本轮离线驱动检查没有证明物理DDR静止。

收尾确认静止，再依次 `ps-local stop`、`ps-local action disable`、`ps-local action close`、`ps-local action feedback_off`、`ps-local release`。记录每阶段结果；本文件当前全部实板步骤均未执行。
