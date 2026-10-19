# 候选13本轮资源与布线总结

2026-10-19，Asia/Taipei。**布线流程完成，功能证据通过，最终时序未通过，发布签核未完成。**

本轮只恢复候选13布线并生成报告，没有修改产品RTL或采用候选14。原中断尝试保留，
从其完整实际顶层place.db恢复；恢复记录为build/interlock_route13/resume_route_r1.log
及resume_route_r1_summary.json。不能把原中断日志描述为一次完成的构建。

同一DR1M90GEG400 speed 2、原100MHz/10ns约束、native PS、真实受保护GP转换器、
两套DMA/controller及HP0/HP1。基线为eccab43/88af6ee封存的closure_cofactor_route5。
综合、布局、恢复布线及全部数据库审计均显式设置16线程并读回；原SDC、ADC和PS属性
逐字节比较一致。没有降低频率、生成部署镜像或操作板卡。

## 原约束时序

|阶段|基线setup ns|本轮setup ns|基线hold ns|本轮hold ns|
|---|---:|---:|---:|---:|
|gate|-1.439|-2.820|0.000|0.000|
|place|+2.786|+1.193|0.000|0.000|
|route|+1.133|**-2.173**|+0.020|**+0.020**|

最终route相对基线setup下降3.306ns；距严格大于+1ns的目标仍需改善超过3.173ns。
hold无违例，setup有5573个违例端点，STA coverage为99.95%。
工具当前域内推导最小周期12.173ns/Fmax 82.149MHz仅为诊断，实际约束保持100MHz。

最终最差路径：

- 起点：control/core/fabric/rs485/collector/engine/push_data_reg[30]_syn_2.clk。
- 终点：a1_dir_syn_6.ce。
- 10级逻辑：LUT6×3、LUT4×3、LUT3×2、LUT5×1、LUT2×1。
- 数据路径11.922ns，其中cell 2.173ns、net 9.749ns（82%）；Max Fanout 28。
- Clock skew 0.166ns；工具默认uncertainty 0.085ns，SDC额外uncertainty 0.000ns。

该路径从原始反馈payload高位合法性检查进入保护译码/联锁取消，经原执行器停止控制
到A1 DIR CE。push_data[30]属于反馈payload高位，不能误写成状态字节或配置代际位。
当前物理最差路径与门级cap_generation→执行器state的路径不同。线路延迟占主导，
是从报告得到的判断；不能仅凭全局最大扇出来解释此路径。

route.qor和route_budget.timing仍带优化用额外1.25ns setup预算，其-3.423ns不是
最终原约束WNS。验收采用恢复原约束后的route.timing，且数据库审计重放STA数值一致。

## 最终实际资源

|资源|基线已用|本轮已用|总量|本轮占比|剩余|绝对增量|
|---|---:|---:|---:|---:|---:|---:|
|LUT6等效|28185|29873|52480|56.923%|22607|+1688|
|Slice|35919|37984|52480|72.378%|14496|+2065|
|Slice寄存器|36403|37863|104960|36.074%|67097|+1460|
|PAD寄存器|9|9|未单列容量|N/A|N/A|0|
|ERAM|58|58|280|20.714%|222|0|
|DSP|6|6|240|2.500%|234|0|
|IO|17|17|126|13.492%|109|0|
|GCLK|1|1|32|3.125%|31|0|
|SCLK|6|6|72|8.333%|66|0|
|LCLK|0|0|20|0.000%|20|0|
|PLL|0|0|8|0.000%|8|0|
|IOCLK|0|0|16|0.000%|16|0|
|MLCLK|0|0|8|0.000%|8|0|

新增声明状态2461bit：监测器1034、寄存器扩展1422、空闲资格1、HOME opcode预译码1、
RUN预译码2、同拍HOME owner缓存1。声明数包含完整1024bit快照，不代表实际资源代价。

|实际FF代价|基线Slice FF|本轮Slice FF|增量|PAD FF增量|
|---|---:|---:|---:|---:|
|综合gate|35480|37372|+1892|0|
|最终route|36403|37863|+1460|0|

工具模块层次sequential统计：safety_interlock为gate 900/route 923，
safety_interlock_regs为gate 962/route 931。模块优化/复制及其他模块变化均计入全顶层
实际增量，不能把声明位数或层次统计相加替代全顶层资源。

## 高扇出、拥塞与约束审计

统计范围为所有负载数>=64的实际网；按负载pin分类，CLOCK属性优先，混合负载逐pin
数量保留在pins/result.json。时钟网的总负载包含混合负载，不能全解释为时钟pin。

|分类|基线网数|本轮网数|基线最大负载|本轮最大负载|
|---|---:|---:|---:|---:|
|普通数据|79|171|189|263|
|CE|181|203|645|556|
|复位|96|100|421|393|
|时钟网|6|6|5969|6298|
|常量|1|1|860|860|

本轮共481条高扇出网。普通数据最大为扩展寄存器read_offset[8]的物理副本；
CE最大556，复位最大393；时钟频率/身份与基线一致，数量不变。

布局最拥塞1% tile平均routing util由85.087838增至97.560811，工具提示局部拥塞。
最终全部187090条路径完成，overflow为0；零溢出不等于时序通过。
工具wire length由12872576增至14579520，增加1706944（保持工具原单位）。

physical、pins、cdc三项16线程只读数据库审计全部通过，审计前后route.db逐字节不变。
原约束和meta→sync内部路径仍受时序检查；所有check_timing分类计数相对基线增量为0，
无新增告警代码。既有dummy node 2、no input delay 5、no output delay 2等基线项仍保留，
没有把“无新增”称为零开放项。MTBF/电气/外部安全输入资格不在此轮完成范围。
route状态检查正常执行，其记录位于恢复日志；本TD调用未生成独立route.drc文件。

## 证据与下一步

- 最终自动比较：../../evidence/interlock_comparison_route13_resumed_r1/REPORT.md及comparison.json。
- 原约束时序：../../build/interlock_route13/route.timing。
- 最终资源：../../build/interlock_route13/route.area。
- 数据库审计：../../evidence/interlock_audit_route13_resumed_r1/{physical,pins,cdc}/result.json。
- 跨模块RTL原因和位置：../../INTERLOCK_TIMING_CHANGES.md。

已有374项功能集成自检、20480项owner等价检查以及候选13真实受保护IP三类故障与双HP
同拍接受验证仍有效；本轮未改RTL，不重复冒称新一轮功能测试。功能通过与时序通过分开。
候选14完整u32代际比较缓存仅为独立准备，不属于此轮产品或时序证据；它也不能直接证明
已解决本轮payload合法性→保护停止的实际最差路径。后续需针对实际路径继续优化并回归，
保持原检测/禁止STEP边沿，不直接给安全停机增加一拍。

SYN-5066原厂S2MM诊断、安全针脚/电气/同步器资格、RS485实体语义/STP查询/收发时序、
机械HOME/停止/恢复、BSP DMA缓冲区quarantine与板卡验证仍分别开放。
本轮没有计算日志、中间数据库或整棵证据目录哈希，也没有完成最终任务提交/发布签核。
