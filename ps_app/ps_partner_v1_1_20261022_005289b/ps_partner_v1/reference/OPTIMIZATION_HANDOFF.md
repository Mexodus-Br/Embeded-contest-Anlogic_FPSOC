# PL 资源优化独立交接 — 2026-10-15

实际完整 `system_wrapper` 释放 **3297 个 Slice，6.2824 个器件占用百分点**；内部 100MHz route setup/hold **+0.080/+0.022ns**。这是同一九 GPIO/RS485/双 HP 顶层的一次资源计数，不能将组件或含子模块的层级报告相加。资源优化通过，硬件发布仍 BLOCKED。

开始核实 HEAD=7681c69，f447116 为冻结遥测源；受控文件无未提交修改，当前分支 codex/rs485-telemetry-hp1 保持。初始未跟踪 log/、td_*.log/logw、旧测试可执行产物均未删除或加入本交付。原发布、回退镜像、原证据与旧清单全部保留。

## 同一真实顶层结果

DR1M90GEG400 **参考 speed2**、TD Release_2026.1_SP2.200.067，内部 10ns。实际 PS、554 项历史配置审核、HP0/HP1、九 J12 GPIO 及 L17/N16/N15 RS485 都保持。A0..A2 500 拍保护时间/100kHz，M4=0、raw64/prepared8/START32。ADC、SDC、PS properties 和 system_wrapper 源文件 SHA 与原基线完全一致。九个 GPIO 仍是 OREG，无隐藏输出或附加输出延迟。

|资源|基线 route|优化 route|差值（优化−基线）|
|---|---:|---:|---:|
|LUT6|32720/52480 (62.35%)|28644/52480 (54.58%)|-4076|
|Slice|44346/52480 (84.50%)|41049/52480 (78.22%)|-3297|
|Slice 寄存器|48872/104960 (46.56%)|47328/104960 (45.09%)|-1544|
|ERAM|34/280 (12.14%)|46/280 (16.43%)|+12|
|DSP|15/240 (6.25%)|5/240 (2.08%)|-10|
|PAD|13/126 (10.32%)|13/126 (10.32%)|+0|

设计寄存器总数 47337 = Slice 寄存器 47328 + PAD 寄存器9；PAD9不计入104960的Slice容量。ERAM代价+12，DSP减少10，IO仍13，GCLK1/SCLK6。剩余Slice=11431，不能据此保证安全/HOME/Watchdog一定放得下。

|阶段|基线 setup/hold ns|优化 setup/hold ns|
|---|---:|---:|
|gate|-1.739/+0.000|-2.276/+0.000|
|place|+2.152/+0.000|+2.498/+0.000|
|route|+0.104/+0.021|+0.080/+0.022|

route 双corner、coverage99.99%，内部无 setup/hold 违例。gate负估计和所有物理修复保留；没有新增false-path、多周期或放宽10ns。既有九GPIO异步20ns观察预算保持，不将其解释为外部100MHz驱动器接收签核。check_timing：{"no clock": [0], "clock definition": [0], "dummy node": [2], "no input delay": [1], "no output delay": [2], "invalid constraint": [0], "combinational loop": [0]}。全部诊断、拥塞原文及详细变化见 `top_r1/comparison.json`、`top_r1/reports/`，没有屏蔽剩余诊断。

setup裕量减少0.024ns，hold增加0.001ns；80ps setup仍很窄，只说明此次参考speed2的100MHz收敛。详细布线路径225526→198878，首轮overflow177375→152155，最终两者overflow0/eco open net0。最拥塞1% tile平均利用率97.398649→94.925676，布线前top1指数99.49→96.99，局部拥塞仍存在。早期RUDY top1峰值114.27→115.19反而升高，不能声称每个阶段/区域都改善；原文完整保留。

|route层级（含子模块，不可相加）|logic LUT|ripple|seq|ERAM|DSP|DRAM LUT|
|---|---:|---:|---:|---:|---:|---:|
|motion_dma_lite_top|6771|3826|10924|16|4|864|
|motion_service|5699|3627|8789|0|4|864|
|rs485_probe_time_regs|425|0|572|0|0|0|
|axi_lite_six_way|189|0|505|0|0|0|
|rs485_gp_bridge|5585|1221|10223|6|1|16|
|rs485_latest_cache|4247|289|18514|0|0|0|
|rs485_telemetry|1081|573|1710|12|0|0|
|telemetry_dma_lite_top|970|135|1652|12|0|0|

## 实现与原子性

`rs485_latest_cache.v`：保留每行完整 last_valid、last_result、不可变generation/revision及饱和updates；失败不覆盖有效记录。删除可从有效原始记录精确还原的解析副本。快照仍在原同一个上升沿捕获全部15行边沿前状态，保存15×676bit原始记录/标签/flags及统一capture time、五组34bit stale_limit、disabled。对外15×128B全部字段保持，读出age/signed/carry/value/enum仅从冻结输入计算；当前采集、配置、generation、时间变化不会污染快照。将规范固定3×u32周期的计算显式实现为34bit移位相加，再零扩展至64bit，五查询共享；没有浮点/标定或迁移PL职责。冻结schema哈希门禁限定该数学契约，不能无审查套用未来不同的stale比例。

`rs485_telemetry.v`：原544bit内部记录/256容量保持，常量header由工具移除存储但原值继续输出。同步读取当前/下一队首，在pop边沿预读下一地址；同地址写入显式旁路，定义首次enqueue及单条pop/push冲突，避免依赖ERAM不确定的read-during-write模式。无RAM内容复位，以count/state/generation围栏无效内容。原LOAD/CRC/SEND周期与可观察接口逐拍一致，未新增AXI等待、提前确认、credit变化或生命周期变化。FIFO槽直到记录最后拍握手才pop，满丢新、cache继续更新、两FIFO唯一消费者都不变。

实际组件综合与route证明：FIFO映射12 ERAM、DRAM LUT1824→0，优化RTL网表仍有480动态bit×256条（另64bit常量header）；cache网表保留15×676bit冻结存储。不是仅添加RAM属性或删掉快照后计算收益。

|相同scan组件|原Slice/LUT6/REG/ERAM/DSP|新Slice/LUT6/REG/ERAM/DSP|新route setup/hold ns|
|---|---|---|---|
|cache|15550/7218/22646/0/10|13863/5147/20726/0/0|+1.065/+0.020|
|transport|5093/4705/2841/0/0|2761/2162/2967/12/0|+1.084/+0.024|

组件有scan寄存器且未绑定实际IO；其计数/裕量只用于候选评估，最终改善仅以上方真实顶层为准。

## 兼容与验证

唯一规范 pl_interface/schema.json 哈希不变，596个旧leaf值保持；全局/GP/遥测/运动/scope生成定义再生一致。MOT2 72B、原采集32B、遥测64B CRC、地址/IRQ/错误码/profile均不变。collector/UART/轮询、多速率、运动算法、PS配置、DMA架构与受保护IP字节身份不变。

- 旧字节归档RTL作独立oracle：115831项cache差分，全部512读地址、三节点五查询、signed极值/未知enum/失败保留/未见字段、同拍事件与快照/配置/generation、捕获后配置/time/gen更新、64bit回绕、age/stale_limit边界与复位/饱和。
- AXI/运输/事件/统计逐拍差分：334项BFM断言，339完整帧/24包；满256同拍pop/push、全环回绕、单条同拍pop/push/刷新、无credit、长背压、CRC/TLAST、重复/矛盾/错误COMPLETE、取消/reset、IRQ mask/W1C竞争、重复/新SNAP ID。允许变化的接口周期数=0。
- parser66组、cache/FIFO unit、results、IRQ、C decoder/软件、旧GP（214寄存器检查、209压力事件、302端到端检查）、原采集/FIFO、原多速率/divider回归通过；RTL帧与C/zlib CRC核对及逐字节损坏拒绝保持。
- 真实未经修改S2MM-only DMA/converter 2251项，精确/短包/超长/缺TLAST及实际长度检查通过。
- 真实双controller标准fixture 23044562项；补充实际三轴500拍/100kHz/M4禁用fixture **23044530项**，HP0读288/HP1写16、3完成事件、32运动点。背压/取消/遥测局部reset期间STEP/DIR/EN、时间及HP0参考逐拍一致。
- 15项原GP/DMA/单轴/四轴/continuous/运动服务/接口/Golden回归通过；本机Questa真实IP测试串行。旧冻结证据/JSON保持原字节。
- 身份门禁正/负检查通过：新候选只允许两个RTL身份变化，同时核验旧f447116 git blob；错误hash、非授权文件、错误基线均拒绝，默认旧当前树门禁仍拒绝新源码，未删除原assertion。

最终证据索引以独立 OPTIMIZATION_RELEASE.json/evidence.zip 为准；baseline/ 保存原报告、原两份RTL与实际PS/project配置及哈希，top_r1/ 保存新完整工程输入、报告与比较。旧发布identity_telemetry.json、bsp/telemetry/DELIVERY.json不刷新。组件报告分别pl_dma/reports/telem_cache_opt20261015_cache1、telem_packet_opt20261015_fifo1；真实IP及新回归原文均有独立tag。

新源码清单同时记录构建时原始字节SHA、LF规范化SHA及固定git blob SHA。历史motion三个文件工作区CRLF、Git LF，仅继承GPIO交付已有的LF身份规则，不重写源码；实际工具展开文件内容及PS/IP/约束/证据仍逐字节核验。

## 未完成/失败与剩余热点

没有为达资源指标而降功能的候选。两项兼容实现均通过模块、差分及实际顶层验证。保留工具/夹具失败：首次沙箱Icarus access violation（普通本地进程同判据通过）、差分夹具unsized时间常量编译失败（修为64'd10）、continue消息中断前的未完成顶层综合/系统仿真（原日志保留，新tag/原输入重跑，未完成结果不计PASS）。首次GP/旧采集使用同sim目录导致新manifest被另一新测试更新；改独立GP tag重跑并封存完整身份，旧发布证据未受影响。

没有采用逐行采样/冻结采集、仅添加RAM属性、削减FIFO/字段、共享或更换controller、增加约束例外等方案。cache仍保存两个完整raw记录的live/frozen副本；旧GP完整统计快照/读选择器、运动FIFO/规划路径仍是剩余热点。没有重构这些已验证范围；后续优化须继续保持原子性及旧profile兼容，不能简单将整个快照串行采样。

## 集成与复现

接入文件是这两份优化RTL及新增候选身份门禁/流程；现有 pl_dma/generate_telemetry.py、规范及生成定义保持。使用同一新源码提交整体引入，原BSP/LINUX ABI代码可以保持，但必须识别独立优化候选源码/IP/约束/证据身份；不要更新旧冻结发布清单来假装哈希未变。

在本工作区、Python3.10/TD指定版本、可运行本地仿真工具的进程中，所有TAG必须是未用过的：

```powershell
python pl_dma/prepare_ip.py
python bsp/telemetry/verify_input.py --optimization-manifest pl_rs485/optimization/top_r1/candidate.json
python pl_rs485/optimization/run_diff.py --tag NEW_DIFF_TAG
python pl_rs485/optimization/run_regressions.py --tag NEW_REG_TAG
python pl_rs485/optimization/run_actual_system.py --tag NEW_ACTUAL_TAG
python pl_rs485/optimization/prepare_top.py --tag NEW_TOP_TAG
python bsp/telemetry/build_hardware.py --work-dir telemetry_opt_NEW_TOP_TAG
python pl_rs485/optimization/audit_top.py --tag NEW_TOP_TAG
```

基线复现用 `prepare_top.py --tag NEW_BASELINE_TAG --baseline`，再用同一build/audit入口。它从归档实际PS/project和原RTL构建独立工程，不切换共享分支、不覆盖工作区源码；baseline_preflight已核对完整输入准备流程。本轮优化前参考报告来自已封存实际route，没有把重新跑过的夹具报告冒充基线。

未来一般验证用新tag；当前seal.py绑定本交付证据tag，封存命令 `python pl_rs485/optimization/seal.py --source-commit FIXED_SOURCE_COMMIT`，随后 `--verify`。seal只创建新清单，拒绝覆盖；verify在缺少本地原文时核对zip内对应字节，有本地文件时仍要求一致。完整原文可在同提交的干净工作区运行 `python -m zipfile -e pl_rs485/optimization/evidence.zip .` 恢复。证据zip不含仿真可执行文件、数据库或vendor保护源码副本。

## 发布边界

timing_pass=true，**signoff_pass=false**。S2MM-only受保护IP仍报SYN-5066内部多驱动；未改IP、未屏蔽、未启用MM2S。RS485外部input_delay1/output_delay2未资格确认、实物speed未确认；dummy原诊断保留。真实IP RTL仿真和资源下降不证明该原厂综合优化的等价性。

无bitgen、HPF/FSBL/BOOT/部署镜像，无COM4/SD/eMMC/QSPI/板卡操作，无自动REBASE/ENABLE/START。Linux实板RX、IRQ/cache、在途取消后DDR写静止/恢复、共享DDR并发最坏补给界、实体RS485与GPIO/机械安全仍由后续已授权流程独立验收。未获静止证明时继续保留/quarantine buffer。优化成果只为后续整机安全/Watchdog/HOME提供实测布局空间，不是整机或发布签核。
