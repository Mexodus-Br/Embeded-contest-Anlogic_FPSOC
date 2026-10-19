# 工具链核对（2026-10-20，Asia/Taipei）

所有操作均在独立实验目录；未接触串口、板卡或生产镜像。工作区 HEAD 开始核对为
`c3e0b471109b7f67b64775b8508f465a496ca07d`；既有暂存/未暂存修改保留。

|项目|实际找到的来源与版本|本轮验证/限制|
|---|---|---|
|TD|`D:/Anlogic/TD_Release_2026.1_SP2.200.067`；运行时 build 6.2.2.200067|DR1M90GEG400、speed 2；综合线程参数及 `get_num_thread` 均读回16|
|当前 IP|`ip/depot/Video_NPU_1.1/Component.xml`、Layout.tcl、Dependency.tcl、原厂加密 RTL|官方 xmlipgen 生成；未改原厂或加密 RTL|
|IP changelog|Video_NPU v1.1 rev0|新增 letterbox、YOLOv5/v8 后处理、删除 HDMI display、优化资源；不提供软件兼容矩阵|
|示例 IP|板卡 `05-5_NPU演示/demo.zip` 内 Video_NPU 1.0|仅历史参考；不把其面积当1.1下限|
|UG1214|本地 UG1214_1.1，2024.12，PDF64–67页|Hard/Soft 协作；FC、卷积、ReLU硬核能力；描述tmfile部署流程|
|IPUG166|用户提供 `D:/Downloads/IPUG166_Video_NPU_IP用户手册.pdf`，v1.0，2023.12，13页|确认网络预设裁剪、至少一种功能/模式、同源同频时钟、配置复位先于系统复位，各至少10周期；早于IP1.1|
|模型预处理/检查/量化|`sdk.2025.7.tar.gz` 内 `sdk/app/npu/scripts/`：AL_onnx_pass.py、check_onnx_model.py、split_convFC.py、run_quant.py、data_reader.py|实际执行；工具未嵌入独立版本号，以包名及脚本路径定位；本轮未改工具源码|
|运行库/接口|同SDK `app/npu/libs/armnn_lib` 及板卡 `face_detection.tar.gz`|Arm NN 32.1.0、ONNX parser 24.6.0；板卡包实际libarmnn.so.32.1是ELF64 AArch64（e_machine=183）；不是Windows库|
|运行时后端|示例 `main.cpp` 默认 `Alnpu,CpuAcc,CpuRef`；executor调用 `armnn::Optimize`|只能证明示例允许这些后端参与选择，未取得本模型逐节点分配；不得默认全NPU|
|驱动|SDK及板卡包中hard_npu、soft_npu、cma_mem源码/示例KO|未构建/加载当前生产内核的匹配驱动；未用旧KO替换任何BSP文件|
|旧tmfile链路|搜索TD目录、板卡demo.zip、sdk.2025.7.tar.gz、uisrc-lab-anlogicM-V4.0.1.tar.gz|未定位UG1214所述独立tmfile转换/优化/指令生成程序，文档未给可执行文件名/版本；不能据此否定已找到的Arm NN路线|
|主机依赖|独立env310：Python3.10、numpy1.26.4、onnx1.17、onnxsim0.4.36、onnxruntime1.20.1、onnx-tool0.9、opencv4.10|先前Python3.12安装onnxsim因缺wheel且无cmake失败，保留记录；未安装torch（本轮实际调用路径无需torch）|

## 已实际复现的软件边界

- 原始68维二维MLP可导出ONNX，但官方检查器拒绝 `Gemm transB=0`。
- 转置常量权重并使用 `transB=1`，数值等价，官方检查器通过。
- 官方AL总入口直接读取输入维度[2]/[3]，二维输入报IndexError。
- 用`[1,68,1,1] -> Flatten -> MLP`表达同一68维模型；检查通过，固定向量输出与原模型完全相同。
- 总入口在未改转换/拆分/量化策略下成功生成UINT8和INT8 QDQ ONNX。
  唯一校准适配为独立FeatureReader，使用500个按标签比例随机选出的训练周期；不把特征伪装成RGB图片。
- SDK运行时才执行Arm NN的后端优化/网络加载。当前Windows主机不能执行附带的AArch64后端，
  本轮又明确不板测，因此没有NPU指令图、实际算子分配或运行时支持性结论。

## 仍缺少的匹配资料或能力

1. **IPUG166对应Video_NPU1.1的修订版/正式兼容说明**；当前提供的是1.0手册。
2. **Arm NN Alnpu 32.1与Video_NPU1.1的兼容矩阵/发布说明**，尤其FC、INT8逐通道、裁剪能力识别。
3. **无Soft算子模型的最小硬件/驱动初始化契约**。检查器Soft清单为空，不能证明可以删除整个软核。
4. **可在离线主机执行的匹配Alnpu后端或其构建源码**，以及不访问硬件即可导出最终指令分配的正式接口。
   已有AArch64运行库不等于具备此项能力；未通过替换后端、模拟设备或跳过能力检查制造通过结果。
5. 当前生产内核驱动、CMA分配、复位/中断/HP互连和DDR竞争的完整匹配验证，均未执行。

手册给出的Yolov3-tiny参考是另一器件封装DR1M90GEG484-2、TD5.9.1 Beta1.0下
12,645 LUT6、15,393寄存器、78 ERAM、48 DSP；不是本轮器件/工具的实测下限。
