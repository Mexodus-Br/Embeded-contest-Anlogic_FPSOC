# DR1 工况模型与Soft NPU资源实验

本轮离线实验，2026-10-19开始，2026-10-20继续，Asia/Taipei。
以本目录的 `REPORT.md`、`TOOLCHAIN.md`、资源表和算子分配表为交付入口。
未上板、未生成启动镜像、未修改产品RTL/冻结接口/BSP。NPU仅向PS提供诊断。

## 复现模型与量化

Python3.10环境（不覆盖系统依赖）与数据都位于本实验目录：

```powershell
$exp = 'D:\Works\Embedded_contest\dev\npu_experiments\dr1_probe_20261019_01'
$py = 'C:\Users\boru\AppData\Local\Programs\Python\Python310\python.exe'
& $py -m pip install --target "$exp\env310" -r "$exp\requirements-host.txt"
$env:PYTHONPATH = "$exp\env310"
$env:OPENBLAS_NUM_THREADS = '1'
$env:PYTHONIOENCODING = 'utf-8'
& $py "$exp\prepare_sources.py"
& $py "$exp\make_probe_a.py"
& $py "$exp\download_uci.py"
& $py "$exp\train_probe_a.py"
& $py "$exp\run_al_probe.py"
& $py "$exp\quantize_probe_a.py"
& $py "$exp\analyze_quantization.py"
& $py "$exp\probe_b_compatibility.py"
& $py "$exp\operator_inventory.py"
```

`prepare_sources.py`从本地原厂包提取少量参考及SDK原始脚本。
首次主机依赖安装、UCI下载需联网，其余模型工作可离线复现。
不要把重复运行的成功日志覆盖失败记录；本目录保留了原始失败及不同校准取样尝试。
模型输出可重复生成，默认会更新模型文件；需要保留其他模型版本时另建独立tag。

## 复现IP与资源

确认没有其他任务使用TD；不终止其他进程。按顺序运行以下命令，每次等待完成。
所有生成/综合均显式16线程，实际读取线程参数及工具线程数。

```powershell
& $py "$exp\run_resources.py" --variant full_native
& $py "$exp\run_resources.py" --variant whole_no_video
& $py "$exp\run_resources.py" --variant tiny_no_video
& $py "$exp\run_resources.py" --variant mbface_no_video
& $py "$exp\run_resources.py" --variant v3_no_video
& $py "$exp\audit_and_place.py"
& $py "$exp\route_tiny.py"
& $py "$exp\summarize_resources.py"
& $py "$exp\verify_deliverables.py"
```

TD路径在run_resources.py中显式指定。目标DR1M90GEG400、speed2。
运行器只创建独立项目及原厂生成IP，使用官方预设并以官方Dependency函数检查派生开关。
全部AXI控制、访存、复位与IRQ接口保留为活的虚拟IO边界（203输入/230输出位），未挂死端口。
这用于测独立IP容量，外部PS/GP/HP/仲裁、时钟/复位/中断集成开销另行测量，不能算为0。

早期错误的IP网表模式没有展开ERAM；该结果只保留作失败诊断。
正式表采用原生综合和pack/legalize报告。早期在有效门级网表建立前create_clock的告警
通过独立数据库重放修正；不把早期默认时序当100MHz验收。
`audit_and_place.py`读取原始gate.db，逐字节确认未改源DB，在`audit100_*`和`physical_tiny_100m`
中建立100MHz约束并布局Tiny。TD必须通过SDC文件加载约束；直接执行create_clock曾创建
未绑定对象，实际仍为50MHz DeriveClock。失败的`audit_*`和`physical_tiny`保留，不作100MHz证据。
最终SDC用数据时钟加1:1同源配置时钟表达手册要求，按STA活动时钟表逐项核对100.000MHz，
而不是只数get_clocks对象。
两时钟边界在真实接入时须来自同源同频时钟；独立虚拟IO约束不验证板级时钟来源或复位顺序。

`run_resource_batch.py`是本轮一次性串行排程记录，等待了本轮先期native_full参考；
干净复现应使用上面的正式逐项命令，不依赖该历史排程脚本。

## 主要输出

- `models/*fp32.onnx`：原始/等价输入表达的浮点模型。
- `models/*quant_uint8.onnx`、`*quant_int8.onnx`：SDK静态量化QDQ模型。
- `models/*vectors.npz`：固定输入、周期ID、主机浮点/量化参考输出。
- `models/training_metrics.json`、`quantization_results.json`、`saturation_analysis.json`。
- `operator_assignment.csv`：全部已导出模型的逐节点算子清单，实际硬件落点均明确标注未验证。
- `ip_*/Design.xml`、`requested_config.json`、`RTL/include/define.v`：官方配置与生成开关。
- `resource_results.json`、`resource_comparison.csv`、`physical_tiny_100m/place.area`。
- `physical_tiny_route100/route.area`、`route.timing`、`route.status`：100MHz独立布线，不能当完整系统集成。
- 原始失败/告警、构建日志、数据库在本地保留；不进入哈希清单，不整包打入Git。

没有NPU执行结果或板测时延；主机推理/量化成功不作NPU成功声明。
当前未取得最终Alnpu指令图或模型到裁剪IP的完整资格证明，见TOOLCHAIN.md。

## 来源与许可证

数据：Nikolai Helwig、Eliseo Pignanelli、Andreas Schütze (2015)，
[UCI Condition monitoring of hydraulic systems](https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems)，
[DOI 10.24432/C5CW21](https://doi.org/10.24432/C5CW21)，
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。数据在2026-10-20取得，
在原始各采样率上提取全周期统计；原作者不为本模型结果背书。

B结构参考：[hfawaz 的Keras时序分类示例](https://keras.io/examples/timeseries/timeseries_classification_from_scratch/)。
本轮B是独立实现的16/32通道小型几何探针，未复制原64通道网络/训练代码。
原厂IP、SDK脚本与手册保留其版权/许可证；本Git交付不重新分发整包运行库或手册全文。
