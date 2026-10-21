# PS合作方最小包交付记录

## 当前交付：v1.1，2026-10-22

用户要求在原包基础上加入日志查看与下载，并确认板卡没有可用4G模块，移除4G扩展计划。本次更新需求及合作方交接，不代表新增服务已经实现。

- 新ZIP：`deliverables/ps_partner_v1_1_20261022_005289b.zip`，294532B，77个文件（含manifest），约287.6KiB；根目录仍为`ps_partner_v1/`。
- 最终ZIP SHA256：`939f836d11b6357d0e2ee03f6c5386761bf8e2fb41e5fd906db4852f962f0648`；同目录保留`.zip.sha256`。
- 基础代码提交保持`ffc67e05dbc7a8fb5559b5753c035ca26b9e815c`；需求、指南及补充上下文固定到`005289ba59463650012e13e5a017225b1c635661`，两者在manifest分开列明，不假称旧schema已升级为SAF2。
- 主入口：`handoff/ps_partner_v1/README.md`；新增需求细化：`handoff/ps_partner_v1/guides/LOG_VIEW_DOWNLOAD.md`，包内同一路径。
- 验证结果：`deliverables/ps_partner_v1_1_20261022_005289b_verification.json`。旧v1 ZIP、校验文件和历史验证记录保留，未覆盖。

### 本次范围变化

1. PS_REQUIREMENTS_V1.md增补v1.1及LOG-02～LOG-06：日志列表、筛选/分页、详情、认证下载、稳定导出边界、只读授权及慢下载/轮转/IO失败期间不阻塞STOP。
2. PS-01/PS-02/PS-05联合交付网页、服务、接口提案、模拟事件源、解析比对与异常端到端测试。确切API/格式、容量、保留期限、并发和性能数值仍需集中确认，不由各组件自行冻结。
3. 更新环境与双方职责：历史Wi-Fi/HTTP已有板测；完整受控镜像为离线候选、控制节点disabled；SAF2/R5S2 RTL已有验证，真实执行后端尚未完整交付。旧delta-scope不能直接作新后端。
4. 新增六份只读上下文资料，位于`reference/current/`：SAF2/R5S2契约、受控集成REVIEW/ACCEPTANCE/BOOT_CANDIDATE、Wi-Fi HTTP状态、MOTOR3125台架状态。台架写SD/读回不等于冷启动或电机通过，也不与完整受控集成混同。
5. 4G从项目架构和本外包范围移除，不交付4G驱动/拨号/SIM/天线或公网中转。历史厂商资料与历史报告仍保留。

### 本次实际验证

固定输入连续生成两次，最终ZIP大小及SHA256一致。新ZIP通过容器CRC检查，从新的含中文/空格目录解压，移除PYTHONPATH后运行smoke，exit0。Windows x86_64 / Python3.10.11 / MinGW GCC/G++15.1.0：

- 全局/GP/遥测三组生成定义检查通过。
- Golden 10项回归、1272向量（826有效、446预期无效）通过。
- MOT2三项既有测试、严格C11 GP mock及遥测C decoder通过。
- 17条冻结RTL样本及1088个单字节损坏拒绝检查通过；独立zlib/字节序核对通过。
- 76份分发原件和manifest测试前后直接字节比较一致；61份旧基础代码/参考文件与旧ZIP逐字节相同。新增日志需求/指南存在，manifest明确4G计划为false。

按最新AGENT约束，打包/验证脚本仅对最终交付ZIP生成SHA256，不再给所有分发文件、日志、样本或证据生成哈希；文件来源记录既有Git blob及字节数。包内无日志、启动镜像、厂商IP、可执行文件或凭据，未通过打包扩大证据哈希范围。本次未连接板卡/串口、写SD/eMMC/QSPI或执行运动；没有实现或运行日志Web服务，不能把smoke算作新增业务功能验收。

### 复现本版本

```text
python handoff/build_ps_partner_package.py --context-commit 005289ba59463650012e13e5a017225b1c635661
python handoff/verify_ps_partner_package.py --archive deliverables/ps_partner_v1_1_20261022_005289b.zip
```

脚本默认基础代码仍为旧固定提交；`--context-commit`锁定已批准需求/指南/状态。显式白名单选取，不递归收集整个工作区。新宿主构建/日志保留在`.tmp/`，不加入ZIP或哈希清单。以下为原v1历史记录，旧逐文件哈希流程不再用于新交付。

## 历史交付：v1，2026-10-15

日期：2026-10-15。项目源码快照：`ffc67e05dbc7a8fb5559b5753c035ca26b9e815c`。

- ZIP：`deliverables/ps_partner_v1_ffc67e0.zip`
- 大小：262587B，约256.4KiB；70个文件（包含manifest）。
- SHA256：`b5f8c8afdfe9b9366f4b8072225e66f49d5130022d0e4be519453b203035b9cf`
- 相同输入连续两次生成，ZIP SHA256一致；不包含本机测试生成物。
- 压缩包根目录为`ps_partner_v1/`，从`README.md`进入；`python tools/smoke.py`在普通主机执行。

## 遴选依据

保留冻结需求、项目环境/双方职责/推进/接口边界/交付指南，Golden原参考与完整1272向量及自测，唯一schema与MOT2编解码，RS485纯C decoder及17条冻结RTL遥测样本，必要生成定义和自检。现有typed UAPI/delta-scope仅作只读对接参考，运动/遥测/优化交接为已有状态证据。

没有加入完整仓库、Git历史、全套硬件资料、厂商IP/SDK/内核/BSP构建部署工具、启动镜像、可执行产物、凭据或大型日志。部分保留交接的全仓库链接不随包分发，指南说明它们不是宿主自测依赖。原始文件按Git blob逐字节提取，包含原有NOTICE；新增指南明确来源和当前限制。

BSP、驱动、PL、DMA owner、交叉编译、设备适配、权限部署与集成上板全部保留项目方负责。正式API/认证/文件格式/时限等仍待集中确认，包中不虚构正式Web API，不让合作方各自猜测。

## 验证结果

从ZIP新解压到含中文和空格的独立目录，清除PYTHONPATH后运行包内smoke，exit0；测试前后69项分发文件哈希一致。

Windows x86_64 / Python3.10.11 / MinGW GCC/G++15.1.0：

- 三组生成定义--check通过。
- Golden 10项回归通过，1272向量（826有效/446预期无效）。
- MOT2 3项codec/损坏/截断/配置检查通过。
- 严格C11 GP mock、遥测C decoder测试通过。
- 遥测17条（16有效/1超时）及1088个单字节损坏拒绝检查通过，另由Python zlib核对17条CRC/字节序。
- 无板卡、串口、SD、网络或DMA操作；不声明六个待开发PS组件已经完成，也不声明Linux/AArch64本批通过。

完整本机验证记录：`deliverables/ps_partner_v1_ffc67e0_verification.json`；ZIP旁另有`.zip.sha256`。

## 复现

从本仓库根目录运行：

```text
python handoff/build_ps_partner_package.py
python handoff/verify_ps_partner_package.py
```

打包脚本只读取显式白名单，固定Git快照，记录来源/Git blob/SHA256，并按固定顺序/时间生成ZIP。新增指南/工具位于`handoff/ps_partner_v1/`。验证脚本保留`.tmp/`下本次独立解压及构建结果，不清理历史或他人文件。
