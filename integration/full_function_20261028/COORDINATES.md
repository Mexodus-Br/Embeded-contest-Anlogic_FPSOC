# PS 坐标/标定契约增量

MOT2、SAF2、R5S2、32B/64B 格式和寄存器不变。PS schema 2 是独立于 HOME elaboration 配置的运行时机械标定；旧 host_demo_v1 只供显式主机测试。

* `home_joint_deg`：HOME 正式退离姿态在原 Golden 几何中的三个关节角；不是计数 0 对应角度 0。机器显示坐标 = Golden XYZ − FK(home_joint_deg)。Golden 保留原厂 83.7/30.4/150/280mm、4.5×200×16 算法及截断语义。
* `encoder_home`：该姿态的各轴 0x30 原始 signed32 carry 与 unsigned16 value。只有显式选择 `signed_turns_plus_u16_fraction` 时，PS 才按 carry×65536+value 建立连续标定量，不能把原始48位重标为实测 XYZ。`encoder_units_per_joint_deg` 由实测确认，允许逐轴正负符号，禁止 0。
* `pl_sign`：每轴 Golden 步数增量到 PL 计数增量的 ±1 映射。PL 目标 = sign × (Golden 目标截断步数 − Golden HOME 截断步数)。触点参考 −150/退离完成0 保持，任何 PS 接口都不 REBASE。
* `physical_min/max_deg`、两侧 `margin_min/max_deg` 使用同一 Golden 关节参考，不能直接复制尚未映射的实体角度。软件 joint_min/max 必须在实测两侧范围内扣除独立正余量。余量大于录入的跟随容差；操作者仍须测定装配误差、实际停止余行程及净空。
* XYZ 的 `workspace`、`xy_envelope` 和 `forbidden_boxes` 均使用机器显示坐标。强制录入带正净空的椭圆 XY 包络，和 XYZ 范围、禁止区域取交集，避免只用独立极值允许矩形四角。Z>=0 的禁止条件应用于内部 Golden 坐标，不应用于 HOME/工作显示 Z。
* `tracking_tolerance_deg` 为 (0,1]，用于命令与编码器映射一致性检查；编码器位置仍为异步 FK 估计。最大源年龄 <=500ms，最大三轴源时间差 <=配置年龄；保留逐轴源身份和时间，不称同步采样。

保存不可变参数版本只保存/选择文档，不建立位置有效性。`POST /calibration/verify` 必须绑定 boot、参数版本、当前 HOME 完成时间；取得控制权、HOME 有效、脉冲静止及至少200ms稳定编码器观察后才建立本次验证身份。失去 HOME/反馈身份、新鲜性或映射一致性即撤销，运行中请求 STOP。重启恢复文档但不恢复验证、任务或 owner。

`POST /coordinates/zero` 绑定 boot、参数、position_id，只更新工作原点机器 XYZ。工作 = 机器 − 原点；工作输入反向转换。原点变化使预览失效，任务绑定 `work_revision`。原点不改变机器边界、编码器、PL计数、EN或 HOME。

速度/加速度后端上限均20，可调低。普通路径使用空间直线和梯形/三角形时间律，2.5ms/<=0.05mm 的生产配置采样、逐样本 IK/关节连续性/脉冲预算检查，禁止区域使用连续线段盒相交检查，椭圆为凸包络。首段及循环返回均重新规划。方向控制使用同一标定/三类边界及脉冲检查，50ms/20样本小包，100ms启动预填；生产者队列最多4包，服务只保持约100–150ms规划前视；350ms输入超时和250ms关键循环租约触发独立 STOP，不在重连后恢复。

`GET /telemetry` 是带源时间/身份的原子 latest-cache。`GET /telemetry/history` 是独立 HP1/DDR 所得原始64B解码窗口，最多512条；退役、缺序、错误、quarantine 单独明示，不声称从启动至今完整。只有正常 DMA exact、CRC 校验及 COMPLETE 后退役；中断不确定 buffer 不释放、不自动恢复。
