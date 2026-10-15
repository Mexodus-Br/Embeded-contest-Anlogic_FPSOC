# Delta机器人PS合作方最小开发包 v1

这是给六项PS软件组件合作方的离线开发包。**BSP、Linux驱动、PL修改、设备接入和集成上板由项目方负责。** 本包用于理解现状、复用已有计算/解码代码，并在普通电脑上完成模拟开发与交付。

## 从这里开始

1. 阅读 [PS_REQUIREMENTS_V1.md](PS_REQUIREMENTS_V1.md)：已冻结功能及第10节开放项。
2. 阅读 [项目环境与现状](guides/PROJECT_CONTEXT.md)：目标系统、可复用资产、当前限制及双方职责。
3. 阅读 [推进指南](guides/WORK_PLAN.md)：六组件各自从哪里开始、先交什么、如何对接。
4. 阅读 [接口边界与开放项](guides/BOUNDARIES.md)：不要把现有板端测试接口误当正式Web API。
5. 安装已有Python 3.10+及GCC/G++（支持C++17），在解压目录运行：

```text
python tools/smoke.py
```

该命令无网络请求、不打开设备、不连接板卡；校验包内哈希、生成定义、Golden 1272向量、MOT2编解码及RS485 C解码/模拟访问。首次会在本目录产生本机编译文件和测试日志。**不需要Git、厂商工具、SDK、内核源码、VM或串口。** Windows PowerShell与Linux shell均可使用上述命令；交付前已实测的平台和工具见[HOST_VALIDATION.md](HOST_VALIDATION.md)，不把未实测平台标为通过。

只核对包完整性而不编译：

```text
python tools/smoke.py --verify-only
```

## 包内有什么

|路径|用途|
|---|---|
|`PS_REQUIREMENTS_V1.md`|冻结功能需求，不是已实现API。|
|`guides/`|环境、职责、推进顺序、开放项及交付检查表。|
|`golden_model/`|只读原参考源码、C++提取模型、配置、完整1272向量及既有回归；保留NOTICE。|
|`pl_interface/`|完整唯一schema、MOT2 codec/测试、定义生成器及生成定义。schema含历史Draft，使用范围见BOUNDARIES。|
|`pl_rs485/software/`|已有纯C解码器及有序回调助手；本包仅测试内存/模拟回调，不调用物理MMIO。|
|`pl_rs485/generated/`|解码/快照所需的生成头文件、寄存器说明及生成核对依赖。|
|`samples/telemetry_rtl_frames.hex`|既有RTL生成的17条冻结遥测样本，含16条有效及1条超时；不是实机采集。|
|`reference/board/`|现有Linux typed UAPI和delta-scope实现，只读对接参考；不属于本机smoke编译目标。|
|`reference/`|既有运动/遥测交接及资源优化摘要，帮助理解已完成与未完成的边界。|
|`PACKAGE_MANIFEST.json`|基线提交、逐文件来源、Git blob和SHA256；非原件会明确标明。|

包中不含FPGA厂商受保护IP、完整RTL/BSP/内核、工具链、启动镜像、ko/exe、板卡操作脚本、凭据或大日志。引用文档的部分全项目链接未随包分发，**不是运行smoke的依赖**；必要信息已在guides中摘明，缺少板端材料向项目方提出集成需求。

## 两个可立即复用的入口

```text
python golden_model/build.py
golden_model/build/delta_model.exe --config golden_model/configs/firmware_reference.cfg xyz 0 0 -140
golden_model/build/delta_model.exe --config golden_model/configs/firmware_reference.cfg xyz 5 0 -140
python pl_interface/tests/test_motion_v2.py
```

Linux可用相同的相对可执行文件路径；PowerShell中若单独运行可加`./`。参考起终点绝对步数分别为`[-1090,-1090,-1090]`和`[-1089,-966,-1213]`。Golden输出角度是**rad**；HMI/API要求**°**，适配层转换，不改Golden。原参数和16位参考步数范围不是机械标定/产品限制。

正式Web API、认证、文件格式和数值期限尚未冻结。请先提交统一接口提案；可以继续纯计算/解码/界面草图及模拟测试，不能把自行选择的接口或演示参数写成项目已批准契约。

交付内容及验收见 [DELIVERY_CHECKLIST.md](guides/DELIVERY_CHECKLIST.md)。本包不授予板卡访问或修改PL/BSP权限。
