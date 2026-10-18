# 保留的失败与限制

不将未到达综合阶段的0条警告当消警结果。所有目录以本实验build/为根。

| 目录 | 原始结果 / 原因 | 处理 |
|---|---|---|
| A1 | Tcl把Windows反斜杠路径解释为转义，couldn't read file | experiment.py改用as_posix，A2成功 |
| gui1..gui5 | 独立IpTool启动未产生窗口/生成物；gui4/exit.json记录exit1、stdout/stderr空；其余未单独取得退出码 | 正式TD工程Tools→IP Catalog成功；不能据这些探测称单向配置不支持 |
| official_xml1 | `HDL-8001 ERROR: Incorrect module param isPresent file path: .../.m_params_official_s2mm.txt` | 输出不可作为官方合格配置，原始失败包装层/RTL仍保留 |
| official_replay1 | `Warning: incorrect random string size. 1`，`HDL-8001 ERROR: can not match component file in user xml`，`XmlIpGen error occur in getRandomNumFile` | CLI复制GUI配置重放尚未成功；正式GUI步骤可复现 |
| B1 | Python `AssertionError: 46`：实验脚本误预期49个官方公开端口，未启动TD | 改为真实46个端口，B2成功 |
| C_width | 宏替换时短名称误命中长名称前缀，`HDL-8007 ERROR: syntax error near 'SF'` | 实验生成脚本按名称长度降序替换；C_width2成功 |
| sim_B | 启动vlib失败 `WinError 623`（系统DLL重定位） | 正常Windows环境串行执行sim_B2成功 |
| sim_A | 所指A_repeat尚未创建，FileNotFoundError | sim_A2使用已完成A2，成功；随后最终asserted组成功 |
| gate_function_B | 功能顶层IO数超封装，`SYN-8228 ERROR: MapIO rule -- The IO number may exceed the device max IOs(126).` | 使用厂商现有OOC流程参数，gate_function_B2成功；不混入扫描资源矩阵 |
| sim_gate_B | 适配已删除内部信号时用字面常数索引，TB语法错 | 改为TB内未使用零向量，未改DUT |
| sim_gate_B2 | 未包含common映射原语，`AL_MAP_SEQ_GSR`/`AL_MAP_LUT5`未定义 | 加入安装包common原语 |
| sim_gate_B3 | 未加载DR1_PHY_GSR仿真顶层，层次名解析失败 | 加载work.DR1_PHY_GSR，B4及最终asserted组成功 |

Python准备/启动阶段异常原文已在本次执行工具输出中出现；上表转录其关键信息，并非冒称每个异常都有TD日志。TD/Questa已启动后的原始错误均在对应run/compile/simulation.log内。所有失败目录保留。中途信息查看命令的错误（PowerShell glob/错误相对读取路径）没有修改设计，也不作为设计实验结果。

门级通过仍伴随原语缺省端口/类型等警告；报告没有称警告无害、没有关闭任何告警。完整等价和在途取消/DDR静止仍未确定。
