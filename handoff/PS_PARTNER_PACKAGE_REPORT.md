# PS合作方最小包交付记录

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
