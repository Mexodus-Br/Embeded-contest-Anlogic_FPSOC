# 完整 BSP GPIO/HP1 集成状态 — 2026-10-14

发布状态：**BLOCKED / 不可部署**。冻结交付基线 f447116；完整实际顶层资源与STA已完成，受保护IP SYN-5066未关闭。未生成新bitstream、配套HPF/FSBL/BOOT/SD镜像，未写SD/eMMC/QSPI或占用COM4。

|阶段|结果|证据/边界|
|---|---|---|
|冻结源码/IP/新规范身份及旧数值迁移|PASS|verify_input.py：596旧leaf值一致，全部生成定义再生匹配，旧核心/IP未改|
|实际PS启用HP1/原DDR与存储属性保持|PASS配置审核|554项不变；HP1启用+64bit，HPF/FSBL内部HP0/HP1 soft reset释放尚未执行|
|完整实际九GPIO+RS485+双HP六窗口顶层|PASS构建/资源审核|独立system_wrapper；source ports、A33与13针约束保留|
|100MHz综合/布局/布线|PASS route内部STA|gate −1.739/+0.000、place +2.152/+0.000、route +0.104/+0.021ns，双corner99.99%，参考speed2|
|硬件诊断/完整IO签核|FAIL/BLOCKED|SYN-5066；RS485缺input_delay1/output_delay2，dummy2保留；实物速度未确认|
|六路地址/读写所有权|PASS仿真|391项含A33高位、窗口边界、背压与应答唯一所有权|
|真实S2MM-only长度/错误|PASS RTL模型|2251项；精确64/1024/192B、提前TLAST actual64、超长error4012、缺TLAST不完成|
|真实双controller系统隔离|PASS RTL模型|23044562项，3事件、HP0读288/HP1写16、32运动点，取消/reset期间STEP/DIR/EN一致；不是硬件等价签核|
|parser/cache/FIFO/IRQ/C decoder/GP/多速率回归|PASS|新tag日志；180s主机超时保留，同判据900s复验通过|
|原GP/DMA/运动/Golden回归|PASS|15个既有回归命令，冻结旧结果/原始证据恢复原字节|
|provider IRQ LENGTH/cookie/retire逻辑|PASS受控软件检查|提取实际函数65项；非物理DDR静止证明|
|匹配ARM模块与验收程序|PASS编译|provider/新owner/原motion client及rs485-accept，vermagic匹配6.1.111-rt42-bsp-sd1；未加载|
|编译DT资源/GIC预览|PASS预览审核|全地址cells/ranges、继承interrupt-parent、六窗口与SPI82..88；新节点disabled，不是最终HPF配套DTB|
|bit/HPF/FSBL/BOOT/rootfs/SD新发布|NOT_EXECUTED|硬件签核门禁拒绝发布；旧scope回退镜像保持|
|SD当次身份/写入/完整读回|NOT_EXECUTED|卡暂不在；没有按历史disk1/盘符写入|
|本候选冷启动/模块/profile/IRQ空闲验收|NOT_EXECUTED|未部署；用户未被要求释放COM4|
|实板独立RX/快照/取消/恢复/DDR写静止|NOT_EXECUTED|在途中断RX无资格证明时保留buffer并quarantine，DT没有验证drain属性|
|实体RS485有效反馈|NOT_EXECUTED|从机型号/地址/电气未就绪；不能用超时记录算反馈通过|
|用户手动GPIO与示波器|NOT_EXECUTED本任务|不自动REBASE/ENABLE/START；沿用scope手册|
|并发HP0补给/HP1压力与Linux间隔/丢弃|NOT_EXECUTED|两HP仍共享DDR，仿真不证明最坏提交界或绝对隔离|

资源：LUT6 32720/52480、Slice44346/52480、Slice寄存器48872/104960+PAD9、ERAM34/280、DSP15/240、GCLK1/32、SCLK6/72、IO13/126。完整占比/剩余、其他资源、层级和旧工程对照见RESOURCE_REPORT.md；没有叠加夹具数字。

诊断结论与厂商复现材料见IP_DIAGNOSTIC.md。首轮脚本在完整来源清单漏含历史motion RTL身份时失败，补为对应GPIO封存身份；原失败构建日志保留。30分钟主机超时后输入/约束不变从gate.db续跑，后续布线中负setup/hold、修复过程及最终报告保留。首次新模块Werror失败、mock编译/错误IRQ二次W1C预期失败与修正、180s仿真超时都保留，未当作通过或覆盖旧证据。

最终软件哈希：provider `8a1f88a1725bffacc6f1073abdb3e057dcc0cd4809b5dd328fafbf9d000425f5`；新owner `ccd33ed525455432b83375c4b17ca6baa264b5bfa4cfa8089e843ae8ae0321fa`；匹配原motion client `e7084e477d36c7e6fc39c5ad58d1c4436a27c928d05db042c5817488f5aa6242`；rs485-accept `e5fdcd54fece2105f67e4a2415efbf5e269b5b937f530371bdc0498fce123f79`。详情/尺寸/vermagic及压缩包哈希见evidence/telemetry-software-20261014/modules.json，完整来源/IP/证据清单见DELIVERY.json。

结束状态：本任务没有打开板端串口、加载新模块、分配实体DMA buffer或启动传输；COM4未占用，用户板上原模块/buffer/运动状态未读取或接管，不能据过去验收宣称当前板上全部静止。新模块仅在VM编译，模型/软件mock已退出。大文件和旧回退镜像保留在bsp/artifacts；log/、td_*.log/logw及他人文件未处理。
