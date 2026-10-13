# 坐标测试轨迹 → J12 实体 GPIO 交接

本交付是无驱动器、无电机的示波器测试配置。原 MOT2、GP、DMA、四轴调度及停止/恢复契约保持，未新增运动算法；BSP 和启动镜像未修改，板卡未下载。构建/仿真及固定源码身份以 `GPIO_RELEASE.json` 和 `scope_test/*_RESULTS.json` 为准；旧 `MOTION_RELEASE.json`、`MOTION_HANDOFF.md` 保留其历史身份。

## 身份与集成入口

基础运动源码 `22ea0a41daa974d24f16b72df7c31db212b7ab8f`、原封存交接 `3a4ea5c8e56024bd2407916bafed48508e5a1e69`。唯一规范仍是 `pl_interface/schema.json`；生成 Verilog/C 定义和 MOT2 codec 未改变。原厂 DMA/转换器/IP 及实际 PS 模型身份在新清单中逐项记录，旧源码 commit blob、未改动核心/算法/接口以及旧证据字节哈希由 `verify_gpio_delivery.py` 核对。

本次固定GPIO源码提交为 `df17b4ebd6e358d6626a227b5c0c152c1f6cb9ed`；规范SHA256=`ac407bcb2ef0798b6d2bcc2aa7feee7c331166efdbf61b37b4a51f00b7ef4b10`，实际PS RTL SHA256=`7cfbddbb88c6b914fa88b1e2b7ec50d53aa54d3948b00ec96ce9f73d78bb3db1`。六份已安装原厂IP逐文件SHA、PS属性源SHA、当前源码LF规范化SHA和所有原始证据SHA均列于独立 `GPIO_RELEASE.json`。封存提交包含本文件与清单，不替换原交付身份；旧验证器检查旧固定源码，当前GPIO交付应使用新验证器。

集成入口仍为 `pl_dma/rtl/motion_gp_ps_top.v`，替换旧 GP/DMA 顶层，不能并联重复 GP 从机。真实输出路径为：

`motion_service.step/dir/en → motion_dma_lite_top → motion_shared_lite_top → motion_gp_full_top → motion_gp_ps_top.motion_step/dir/en → motion_soc_scope 的九根标量端口`。

所有层级通过显式端口和连线传递，未通过层级引用取信号，未增加另一套脉冲源或输出延迟寄存器。motion_service 原本已有输出，核心无需修改。原端口顺序/参数默认值及命名实例调用保持，新增输出可不连接；现有调用的 GP/真实 DMA 回归已验证。附带的 point_start/point_done/slot_event/slot_id 是显式逻辑观测端口，供仿真自检，不绑定实体针脚。原 GP 快照保持旧语义，真实运动快照继续从新窗口读取。

资源保持：GP `0x80400000/4KiB/SPI82`；DMA `0x80500000/4KiB/SPI83/84`；运动 GP `0x80600000/4KiB/IRQ3/SPI85/INTID117`，高有效 level，PROFILE=`0x31544f4d`、VERSION1、CAPS/FEATURES=`0xf`。MM2S only；不投 S2MM RX、不要求回包。

## 已确认的 J12 测试接线

用户于2026-10-13集中接受下表、连接器针序核对、九针无其他占用及仅接示波器/不接驱动器或电机条件。按实物针1标记及针2=GND核对观察方向；本表使用连接器电气针号，不按原理图符号文字的屏幕位置猜测。

| 内核测试轴 | 信号 | J12针 | DR1球位 | Bank/标准 |
|---|---|---:|---|---|
| A0 | STEP | 3 | Y12 | BANK11/LVCMOS33 |
| A0 | DIR | 4 | Y13 | BANK11/LVCMOS33 |
| A0 | EN | 5 | T9 | BANK11/LVCMOS33 |
| A1 | STEP | 6 | U10 | BANK11/LVCMOS33 |
| A1 | DIR | 7 | T5 | BANK11/LVCMOS33 |
| A1 | EN | 8 | U5 | BANK11/LVCMOS33 |
| A2 | STEP | 9 | V6 | BANK11/LVCMOS33 |
| A2 | DIR | 10 | W6 | BANK11/LVCMOS33 |
| A2 | EN | 11 | U7 | BANK11/LVCMOS33 |

J12-2是示波器共地；J12-1是电源针，不能接探头地。建议高阻/10×探头，不能用50Ω端接直接加载 GPIO。J12为2×13/2.54mm，资料显示24根信号经过33Ω串阻；核心板BANK11固定3.3V。依据GPIO xlsx、底板原理图p16、核心板p4/p6分别核对，原表/网络名的Zynq BANK13不作为DR1 Bank号。资料哈希与九针核对见 `scope_test/PIN_REVIEW.json`。实物speed未确认，工具明确使用 DR1M90GEG400 **参考speed2**。

M4参数为0、禁止ENABLE，不绑定输出。A0..A2仅是测试轴，不冻结为最终M1..M3机械映射，其他J12引脚不分配。

STATUS.CONFIG_VALID是四轴config_valid的归约AND，M4故意无效使其保持0；这不是前三轴配置失败。scope应用应按SNAP.VALIDITY的独立config/position位检查mask7：config位[7:4]=0x7，REBASE后position位[3:0]覆盖0x7；不能要求四轴全有效或ENABLE mask15。唯一规范与该状态语义未修改。

## scope-test 参数及引脚状态

配置源 `scope_test/CONFIG.json`，由 `generate_scope.py` 派生参数、ADC/SDC及固定 MOT2 仿真记录；`--check`核对再生一致性。100MHz/H16，前三轴 H/L/DIR setup/hold/EN setup/disable 全部500拍=5μs，最大STEP100kHz、测试EN高有效；raw64/prepared8/START32不变。默认模块参数继续为0，默认自检确认config_invalid、无自动输出、显式ENABLE被拒绝。

H是实际高脉宽，L是最小低电平，不意味着此固定低速轨迹每个低电平都只有5μs。给定124主槽/500ms轨迹的槽间距约4.03217ms，实际步频约248Hz，低电平远大于5μs。DIR/EN建立和保持也是最小值。本配置不能用作SERVO42C时序或产品参数。

| 状态 | STEP | DIR | EN |
|---|---|---|---|
| 启动/整域复位 | 0 | 正方向1 | 禁用0 |
| 未显式使能 | 0 | 保留 | 0 |
| 正常END/正常STOP安全排空后 | 0 | 保留末方向 | 保留已使能1 |
| 显式DISABLE完成后 | 0 | 保留 | 0 |

STOP不等同DISABLE，不改变原EN保持契约。正常STOP禁止新STEP，已经发出的高脉冲、低间隔和DIR保持完整排空；GP STOP_COMPLETE才表示pulse-safe，B响应/命令应答不表示排空完成。整域异步复位可能截短脉冲，只用于启动/受控重建，不替代正常STOP。DMA-only恢复不复位位置/时间戳、不自动重开旧session。

## 固定向量与示波器对照

原固件参考配置的XYZ起点(0,0,-140)mm，对应命令位置A0..A2=[-1090,-1090,-1090]。停止/失能态维护REBASE到此值，再显式ENABLE mask=0x7。该REBASE只是无电机初始化，不是机械回零。

新session sequence=0，目标XYZ(5,0,-140)mm对应[-1089,-966,-1213]，axis_mask=0x7、duration_tick=500000、END=1、M4 target=0，完整预缓存后显式START。增量[+1,+124,-123]，STEP数[1,124,123]，DIR电平[1,1,0]。返回起点用新的session、目标[-1090,-1090,-1090]，增量[-1,-124,+123]、相同步数、DIR[0,0,1]。

共同主槽数124，保守初始guard=1002拍=10.02μs；槽k的预期上升沿为 `1002 + floor(k×49998998/124)` 拍，相对point_start，下降沿再加500拍。槽间距403217或403218拍。非零轴首槽同拍：A0仅槽0，A1全部124槽，A2槽0及槽2..123。对应边沿只按实际共同槽配对，不能把不同轴的第n个边沿一概视为对应边沿。

示波器可用A0首次STEP上升沿触发对齐；表中的point_start原点比它早10.02μs，point_start/done不额外占GPIO。完整duration由逻辑观测及GP END/状态核对，不能仅用最后STEP到末点的间隔替代。仿真波形为 `scope_test/evidence/scope_outputs.vcd`，逐边沿参考表 `scope_test/expected_edges.csv`，真实观测表 `scope_test/evidence/observed_edges.csv`，图 `scope_test/scope_waveforms.png`；真实RTL仿真不是示波器实测。

额外执行中STOP在首槽高电平期间发出，预期本次三个STEP各1个，高脉宽仍5μs，禁止以后槽，保留部分位置[-1089,-1089,-1091]，END/done不增加，随后显式DISABLE释放EN。GP位置/累计脉冲与GPIO边沿积分独立比对。仿真通过真实GP和原厂MM2S/HP转换器读取72B记录，不使用行为DMA stub，IOC、packet_closed、record_accepted、point_done/session_done分别检查。

## 构建、复现及后续 BSP 接入

在工作区根、可正常运行本地TD/Questa/Icarus的进程中：

```powershell
python pl_motion/verify_gpio_delivery.py --baseline-only
python pl_dma/generate_motion.py --check
python pl_motion/generate_scope.py --check
python pl_motion/tests/run_scope_default.py
python pl_motion/tests/run_gpio_regressions.py
python pl_motion/tests/run_scope_dma.py
python pl_motion/scope_test/analyze_edges.py
python pl_dma/build_gpio_scope.py --tag gpio_scope_async
python pl_motion/scope_test/audit_gpio_sta.py
python pl_motion/verify_gpio_delivery.py
```

绘图另运行 `python pl_motion/scope_test/plot_waveforms.py`，需matplotlib；本次使用 `C:\Users\boru\AppData\Local\Programs\Python\Python310\python.exe` 和matplotlib3.10.9（桌面bundled Python未安装matplotlib，首个绘图调用失败后改用已有环境，未新增安装）。`archive_gpio_evidence.py`在全部成功后封存原文，`seal_gpio_release.py --source-commit <固定GPIO源码提交>`生成独立清单。源码提交与封存提交分开，清单不自行哈希；完整记录有两个500ms点的100,000,000个真实时钟周期，Questa耗时较长，7200s超时上限不改变仿真时序。每500万周期输出进度并刷新边沿文件，不能因stdout缓存尚未显示PASS而认定完成。

Questa只有一个本机会话许可证，真实IP回归与坐标仿真必须串行。生成的最终真实PS顶层在 `pl_dma/build/motion_soc_gpio_scope_async/top.v`；实际PS property只重映射真实实例层级，原属性值保持。新工程保留内部10ns时钟，实体ADC全部明确约束。九路输出8mA/SLOW、PACKREG=ON（原有寄存器打包至PAD，不添加时钟延迟），异步示波器没有外部同步capture clock，因此仅这九路使用20ns datapath-only约束；output_delay的0ns仅保留工具参考定义，其max setup由该明确上限覆盖，不能解读为外部100MHz同步接收签核。未加false path/multicycle、未放宽内部clock；20ns是本次观察通路测试上限，不是驱动器或产品参数。原来假设外部100MHz同步接收的0ns输出参考配置失败：未打包−1.342ns、打包−5.223ns；PAD/SLOW clk→out自身10.533ns、实际launch clock插入约4.69ns，失败原文保留。最终独立setup/hold/IO/诊断见STA_RESULTS和封存原文，不沿用内部输出工程签核。工具大产物在build目录，交接证据独立封存。当前bit仅为审核产物，不是配套启动镜像。

BSP/PS agent后续应建立独立GPIO候选系统，核对新固定源码/IP/bit/PS/约束身份，重新生成匹配HPF/FSBL/BOOT并按其已授权部署流程验收；本任务没有执行这些步骤。保持DDR1.35V/32bit/1333MT/s、存储、PS属性及GP/HP reset释放方式，保留原回退系统。GP/DMA/运动地址及IRQ、MOT2/C ABI没有新增或修改，是否复用模块由BSP核对新身份后决定。

现有通用 `motion-accept` 使用四轴ENABLE及快脉冲验证参数，不能直接用于此三轴scope配置。受控应用使用现有typed ioctl/设备DMA API：独立STOP/确认静止→DISABLE mask7→显式RECOVER→维护REBASE mask7/position[-1090,-1090,-1090,0]→ENABLE mask7→新session OPEN→canonical codec生成72B END记录→count1/BTT72、提交前PACKET_ARM（由client管理）→IOC和packet_closed/accepted确认→START_READY/显式START→读取动态快照/END。仿真记录session1/2/3仅是fixture，实板必须使用client分配的新非零session并重算CRC，不能重放旧session二进制。全部等待不得阻塞独立STOP/快照。

完成后GP STOP/pulse-safe，按既有controller作用域terminate_sync和静止确认，显式DISABLE/RELEASE；失败quarantine保留buffer，禁止自动续跑旧轨迹。不得用户态任意物理地址/MMIO绕过。实体观测顺序为上电/未使能状态→正向固定点→独立新session返回→在途STOP→DISABLE→最终无传输/安全静止。

## 审核结果与保留失败

默认零参数检查1250项通过；受影响回归17个命令全部通过；最终真实DMA/GP坐标自检4434项通过（starts3/dones2、27个64bit HP read beat、无HP write/S2MM RX），两次duration均精确50,000,000拍。独立边沿oracle核对往返各[1,124,123]及对应slot零逻辑偏移，STEP高500拍、低≥500拍；观测到的最小DIR setup1002拍、EN setup1996拍、DIR hold404524拍、EN disable1721拍均覆盖500拍要求，不能把实际更长间隔改称配置最小值。最终STEP/EN全0。

| 快照阶段 | A0..A2位置 | 累计pulse_total | END计数 |
|---|---|---|---:|
| 去程完成 | [-1089,-966,-1213] | [1,124,123] | 1 |
| 返回完成 | [-1090,-1090,-1090] | [2,248,246] | 2 |
| 在途STOP排空 | [-1089,-1089,-1091] | [3,249,247] | 2 |

最终工程使用真实PS/GP0/HP0及上述九路GPIO：DR1M90GEG400参考speed2，Slow/Fast双corner，Routed覆盖99.99%；内部board/GP/HP均100MHz。最终SWNS=+0.031ns、HWNS=+0.021ns，STNS/HTNS=0；此前gate估计−2.588ns、place估计+2.546ns分别保留，不能把place估计当签核。内部最差路径到A0 DIR的PAD寄存器CE；仅31ps setup裕量，不形成更高频率或实物speed承诺。九路异步观察通路的20ns上限单独审核，不表示外部100MHz接收器通过。

最终资源LUT6=13051、REG=13616、SLICE=15335、ERAM=16、DSP=4、GCLK=1、SCLK=6；10个PAD仅H16与已确认九路。Critical-warning为0；无时钟/无效约束/组合环路/无IO延迟均0。仍有两类HIGH dummy诊断：原厂DMA/转换器ERAM未使用的reset端、运动planner映射slice未使用的OFB；未擅改原厂IP或算法消除它们。另保留plan_fifo两个映射RAM slice的SLATR-1036/1038注记，最终route pin/net/LUT bridge/multidrive/clock/abnormal path检查完成无error/critical-warning。不能报告为“所有诊断为零”。详情见IO_AUDIT_RESULTS及完整run.log/route.check。

审核bit SHA256=`6e662645ae80177ef11c2a01eb3986f99897f575548912200efc04143a18c426`，位置`pl_dma/build/motion_soc_gpio_scope_async/scope-test.bit`。只用于此独立工程审核，尚无配套新HPF/FSBL/BOOT；不得用旧系统身份宣称已经实板运行此bit。

保留失败记录包含ADC注释语法、首轮编译宏名、两次人工终止的未完成长仿真、Questa单会话许可证冲突、STOP断言bit6传入单比特参数被截断的问题（改为显式非零比较，内核未改）、以及两份错误假设外部100MHz同步capture的输出参考约束失败。未完成/失败记录不计作通过证据；最终通过以独立RESULTS和成功原文为准。

## 未验证项

未下载板卡、未修改BSP/启动镜像，未用示波器测量电压/脉宽/对应边沿/极性/上电高阻窗口，未验证探头/线缆/连接器外侧延迟，未接驱动器或电机。实物speed、板卡修订/3.3V供电实测、驱动器输入同步、SERVO42C参数、安全输入/回零/报警/机械映射均不由本测试冻结。维护命令位置不是编码器反馈。Linux普通调度欠流与FIFO50有限实测限制继续遵循BSP报告，不能用本次长点仿真替代Linux最坏提交界。
