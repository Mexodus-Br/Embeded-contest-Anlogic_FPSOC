# Delta机器人自主控制系统

基于安路DR1M90 SoC FPGA的Delta机器人控制项目。PS Linux负责任务、轨迹规划/插补、Delta逆运动学、Web与诊断；PL负责确定性四轴STEP/DIR/EN执行、安全/HOME及RS485采集。

首版交互采用Wi-Fi局域网与Web HMI。网络接入、PS服务、PL数字验证和实板验收分别推进；功能仿真或时序通过不等于已获准部署或带电机运行。

## 阅读入口

- [AGENT.md](AGENT.md)：架构、协作和变更规则，执行任务前完整阅读。
- [PHASE0_CONSTRAINTS.md](PHASE0_CONSTRAINTS.md)：用户确认和阶段状态，顶部较新条目覆盖对应历史记录。
- [HARDWARE.md](HARDWARE.md)：板卡、电气、工具和资料差异。
- [PS_REQUIREMENTS_V1.md](PS_REQUIREMENTS_V1.md)：PS组件、Web HMI、命令和任务需求。
- [BACKUP.md](BACKUP.md)：远程Git备份范围、本地产物和推送步骤。

## 目录

| 目录 | 内容与入口 |
| --- | --- |
| `golden_model/` | 运动学参考实现、原行为对照与回归向量，见[README](golden_model/README.md)。 |
| `pl_interface/` | PS/PL机器可读接口规范、生成器及C/Verilog定义，见[README](pl_interface/README.md)。 |
| `pl_motion/` | 四轴运动、连续供给、GP与GPIO，见[运动交接](pl_motion/MOTION_HANDOFF.md)。 |
| `pl_rs485/` | UART/轮询、GP、解析、缓存和遥测，见[DMA交接](pl_rs485/RS485_DMA_HANDOFF.md)。 |
| `pl_dma/` | GP/HP/DMA互连、守卫和验证，见[README](pl_dma/README.md)。 |
| `pl_safety/` | 限位、急停反馈、HOME与后续联锁，见[契约](pl_safety/CONTRACT.md)和[README](pl_safety/README.md)。 |
| `bsp/` | Linux/Buildroot、启动链、板测和部署，见[README](bsp/README.md)。Wi-Fi见[专项入口](bsp/wifi/README.md)。 |
| `handoff/` | 合作方资料、打包脚本及交付说明。 |
| `deliverables/` | 本地生成的合作方交付包，默认不纳入Git。 |

## 开发与证据

源码、接口、必要生成物和经过审核的交接资料保存在Git中。构建树、镜像、工具临时文件与新测试运行目录默认留在本地；历史已跟踪证据保持原样，不因新增忽略规则而删除。

执行测试和重建时按所属模块文档选择命令，先单模块验证再集成。新增RTL须有自检；运动学变更须通过Golden回归。完整顶层资源和时序以同一实际工程报告为准，不拼接独立模块结果。TD操作显式16线程并核验实际值。

共享工作区中可能同时存在其他任务的暂存和未暂存修改。不要使用`git add .`、清理未跟踪文件、重置暂存区或覆盖他人构建目录。哈希范围遵守AGENT.md最新规定，只限最小必要关键交付物及其直接源码。
