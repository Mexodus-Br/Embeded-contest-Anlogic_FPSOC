# 除 NPU 外首版全功能镜像：实现与验收矩阵

基线/开始核对 HEAD：a21751d。2026-10-28 Asia/Taipei。
工作树既有脏 RTL 不属于候选输入；旧 HOME r2 和 SD 不修改。
最终状态：OFFLINE_FULL_FUNCTION_CANDIDATE_NOT_BOARD_ACCEPTED；所列软件与PL功能已实现并离线验证，实板未执行。机械参数未填是现场标定输入，不是镜像功能缺失。

2026-10-29 用户追加：本轮只制作镜像，不写卡、不执行实机动作；制作完成即结束。
本轮最终 nominal 100MHz setup WNS 门限放宽为 >=0.2ns，hold 仍须非负；不修改时钟、IO或安全条件。不把该放宽用于其他任务。首轮完整 P&R +0.040ns/hold +0.020ns 仍未达标，原报告保留，继续物理优化。

2026-10-29 最新用户覆盖：目标快速制作镜像，本次布线优化后 setup WNS **>0ns** 即通过，hold仍须>=0；此项取代本任务先前0.2ns门槛，其他条件不变。达标后不继续追求额外裕量。

|功能|实现状态|离线验证及证据（同目录日志）|实板|
|---|---|---|---|
|Wi-Fi STA、认证 HMI、统一 Web/本地终端、独立 STOP|已实现；现场填 Wi-Fi 凭据及具体 LAN 绑定地址|HTTP 14 项；`service-tests-final.log`；本地适配器 `local-tests-final-2.log`；串口行协议 `serial-tests-final.log`，未连接 UART|未执行|
|0x30→标定角度→FK→机器 XYZ|已实现；只接受新鲜且身份一致的三轴编码器|`calibration-tests-final.log`：108 个 IK/FK 点及独立球面残差；缺采/陈旧/错代际/0x33 伪装均拒绝|未执行|
|Golden 与 PL HOME 计数映射|已实现；Golden 目标减 HOME Golden 目标，再乘逐轴符号|同上；HOME 正式退离机器显示 0；PL 0/触点 -150 不代表机械角度零|未执行|
|双坐标、用户零点、旧预览失效|已实现；仅 PS 平移，机器安全域固定|`full-web-tests-stopped-pose.log`：非零机器位置设工作零，机器/计数不变；假板卡验证零硬件写入和旧帧拒绝|未执行|
|机械参考/编码器/XYZ/角度边界及余量版本保存|已实现；schema 2 校验与显式 HOME 绑定|`hardware-tests-final-2.log`：保存不生效为位置；重启不恢复资格；浏览器实际编辑保存再验证|未执行|
|空间直线、梯形/三角形加减速、多点 MOT2/DMA|已实现；后端速度/加速度均 <=20，时长不可执行则拒绝|数值测试、24 组后端场景；首段/循环返回/路径 XYZ+角度+IK+脉冲检查；实际 Linux 分支另行交叉编译|未执行|
|真实方向、释放/失联 STOP|已实现；有界预填充、生产者超时和独立 STOP|浏览器真实 Service/HardwareBackend + 定时测试板卡：释放和断网均停稳，不自动复活|未执行|
|示教、多点、重复任务与持久化|已实现；任务绑定工作坐标版本|浏览器两点两次任务/示教；HTTP 持久化；取消/故障/重启不重放|未执行|
|0x30/33/39/3A/3E 实际发布|已实现；保留原值/源时间/generation/revision/陈旧标记|已有冻结帧、服务回归；编码器位置与命令脉冲分开|未执行|
|HP1/DDR 64B 原始历史与 quarantine|已接通独立 RX 消费；512 记录有界窗口，记录截断/缺采/错误，不宣称全历史|`provider-tests.log` 65 检查；`rx-owner-tests-3.log` 32 实际驱动函数检查；不确定取消保持 quarantine。**未证明物理 DDR 静止**|未执行|
|日志查看/筛选/JSONL 下载|已实现且有界|HTTP 与浏览器下载解析，方向日志可按同一命令 ID 关联|未执行|
|HOME/限位/急停/485 保护/心跳/普通运动资格|已实现；新身份 runtime_calibrated_motion，HOME、标定、边界、执行资格分开检查|安全驱动 45 检查；普通运动门禁 410 检查；安全 RTL 32 场景、HOME 54 检查；互锁 79 /解析等价 68728/owner 20480|未执行|
|100MHz STEP/DIR/EN 时序与候选 DIR 等价|已验证|`timing-tests-executor6.log`：24 检查/3007517 周期；`executor-equivalence.log`：32 场景/15427 周期逐拍全信号相同|未执行|
|独立 PL、threads=16、完整 P&R/bit/HPF|已完成，选择hardware6/refined6|最终原始100MHz约束 WNS +0.312ns、hold +0.020ns；bit/HPF一致，556项PS导出参数匹配。见hardware-result.json|未执行|
|同批 FSBL/BOOT/匹配内核/驱动/DT/rootfs/SD 文件|已完成，512MiB镜像已下载且11项SHA256一致|构建提交67c276b；VM独立r3目录；新FSBL、原精确匹配wifi1内核、重编驱动/应用；212模块/3556导入CRC、DT/ABI、14安装文件及分区/FAT读回通过|未执行|

## 接口变更边界

新增 PS 标定/坐标接口及参数版本，不修改 MOT2、原 32B/64B 遥测、SAF2 寄存器语义。
旧 host_demo_v1 仅用于显式主机测试，不能作为真实机器标定。
运行配置与 HOME 身份将分别检查；新增功能配置不得继承 home_calibration_only 的普通运动资格。
所有机械数值由现场录入；保存不建立 HOME 或位置资格。

## 实板顺序（需要当次授权）

核对介质 → 用户断电并隔离脉冲 → 身份/输入/STOP → 用户确认近限位起点及供电/急停 → HOME → 网页输入实测标定与边界 → 小范围 XYZ/方向 → 双坐标/示教/有限重复/取消/日志。
每阶段记录身份、原始反馈和结果；失败先 STOP，不扩大 HOME 搜索、不重试旧任务。不操作 eMMC/QSPI。

## 最终交付核对

构建、下载与本地校验全部通过，无本任务已知未实现的软件条目。镜像路径及哈希见DELIVERY.md、release-manifest.json。实际硬件/电气/机械/DMA写静止证据未取得，逐项见OPERATIONS.md；不以离线测试替代实板通过。最新用户限制本轮到镜像交付结束，不写卡、不操作实板。


2026-10-29 后续追加：用户已明确确认本次SD目标并授权写卡，现已完成512MiB写入及完整无缓存读回，SHA256一致。此项取代本文先前“未写卡/本轮不写卡”的阶段状态；实板仍未启动、未执行HOME或运动。详见[SD_DEPLOYMENT.md](SD_DEPLOYMENT.md)。
