# 首版受控集成审查

2026-10-21，Asia/Taipei。范围仅无电机离线集成及后续有条件验收。

本目录不是当前工作树的打包，也没有将优化候选提升为产品RTL。PL取自实际完成的`rtl_path38`工程输入和`rtl37_candidate_r5`；软件取自固定提交的干净源码，再在本目录应用明确适配。`07745a8`只用来提取软件/生成定义，不用来代替PL快照。逐文件来源见`sources.json`，适配见`adapt.py`、`add_dma_observation.py`和`hardware-changes.json`。

|项目|集成候选及审查结论|
|---|---|
|原PL身份|`pl_safety/build/rtl_path38`，完整native PS、真实GP转换器、双controller及GPIO顶层；19个候选覆盖文件逐字节匹配rtl37_candidate_r5|
|原最终STA|100MHz/10ns；setup +0.032ns、hold +0.020ns；Slice36694、ERAM69、DSP6；无负STA但原专项>1ns不通过，signoff=false|
|本次实际顶层|保留原完整PROFILE2逻辑，只将四路安全输入固定到已核对的J12 GPIO；须使用本次完整P&R结果，见`RESOURCE_REPORT.md`|
|生产配置|PROFILE2是资源/功能夹具；不批准用于真实运动。生产HOME配置仍未批准；原三轴scope时序也不是SERVO42C生产参数|
|时钟/时间|H16板载100MHz；GP0、HP0、HP1/两DMA共同100MHz；统一u64、1MHz时间，不降到50MHz|
|PS/DDR/存储|实际PS参数与scope基线比较，仅HP1启用/64bit差异；1GiB、32bit、1333MT/s、1.35V及原存储属性保持；实物电压/颗粒/速度未实测|
|复位|启动共同p2f reset；局部DMA恢复不重建时间epoch，不冒充整域复位；HP1恢复不复位HP0/运动。HPF/FSBL中的GP/HP0/HP1释放须在最终启动链单独核验|
|Wi-Fi|保留U02平面路径的11个正确相对别名、Python lstat权限检查、STA本地配置流程|
|HTTP|认证首页及固定只读下载；UID/GID498；新增固定`/files/integration-snapshot.json`，请求不执行采集、shell或控制动作|

所有窗口4KiB，完整A33译码。默认未命中路由到原DMA guard，再由guard拒绝非法/高位地址；没有别名或并联从机。

|窗口|用途|f2p_irq|GIC SPI / INTID|Linux所有者|
|---|---|---|---|---|
|0x80400000|原probe GP|0|82 / 114|bsp_gp，/dev/bsp-gp，原唯一入口|
|0x80500000|原双向DMA→HP0|1、2|83、84 / 115、116|匹配的anlogic-dma-engine；运动client独占申请|
|0x80600000|MOT2运动|3|85 / 117|bsp_motion，/dev/bsp-motion；仅编译验证，DT禁用，旧scope程序不进入候选|
|0x80700000|R5S2采集|4|86 / 118|bsp_rs485，/dev/bsp-rs485，root、单打开者|
|0x80800000|缓存/遥测运输|5|87 / 119|同一bsp_rs485，独占消费及buffer生命周期|
|0x80900000|独立S2MM-only→HP1|6|88 / 120|同一匹配provider的独立controller，只有S2MM child|
|0x80A00000|SAF2安全/联锁|7|89 / 121|bsp_saf2_diag，/dev/bsp-saf2-diag，root、单打开者；诊断子集|

IRQ均level-high。七窗口/八SPI已通过编译DT的cells/ranges、继承GIC和冲突审核；该DT只作禁用预览，仍使用既有scope/Wi-Fi展开头，不是新HPF配套启动DTB。所有GP/运动/DMA/采集/安全节点均disabled，不含validated-hp1-reset-drain属性。SAF2诊断bind核对实际GIC hwirq121/level-high并拒绝已有非零IRQ mask；不启用或W1C清除IRQ，异常IRQ只屏蔽来源、保留事件并递增诊断计数。

|实体信号|连接器/球位|资格|
|---|---|---|
|A0 STEP/DIR/EN|J12-3/4/5，Y12/Y13/T9|原已确认九GPIO示波器映射|
|A1 STEP/DIR/EN|J12-6/7/8，U10/T5/U5|同上|
|A2 STEP/DIR/EN|J12-9/10/11，V6/W6/U7|同上；M4参数0，无实体pad|
|A0限位/HOME|J12-12，V7|用户授权从未用GPIO选择；外部3.3V上拉、低有效|
|A1限位/HOME|J12-13，U9|同上|
|A2限位/HOME|J12-14，U8|同上|
|急停动作反馈|J12-15，V11|同上；不证明运动12V已断电|
|RS485 TX/RX/DE+RE_N|L17/N16/N15；J11-4GND、5A、6B|原手册接线；实际从机/端接/转换模块待验收|

J12为BANK11/LVCMOS33；手册p23的球位表与底板原理图p16连接器/33Ω串阻已视觉核对。J12-2是GND；J12-1是电源，不能作为GPIO或探头地。外部上拉必须接3.3V域，不能将12V接入输入。上拉电阻值、线缆/保护/干扰与实物断线检测尚未资格确认。TD默认pullup不是外部上拉已经安装的证据。

软件资格与恢复边界：

- 七模块均针对同一个wifi1源码、输出、.config、Module.symvers构建；逐项检查vermagic和全部导入CRC，AIC模块间导出也纳入核对。未复用sd1模块。
- R5S2使用新compatible，严格检查version/profile/caps/features；不重定义R5S1常量。配置要求RUN读回为0；配置accepted/applied及最终RUN读回均检查，PL继续拥有最终资格拒绝权。
- 旧bsp_motion仅保留MOT2/容量/版本兼容编译；其程序不具SAF2资格管理，不能作为新执行后端。旧delta-scope等入口从新rootfs排除，旧镜像不变。
- SAF2诊断仅提供原子快照、显式空闲配置及明确的无电机新owner超时实验。无HOME、REBASE、ENABLE、START、清错、任意MMIO/mmap或shell接口；设备open/close不OPEN/CLOSE或喂PL owner，服务重启不接管旧owner。
- 未安装执行后端或独立续命线程。将来唯一执行后端须由健康控制循环报活；本轮不以诊断定时器替代。完整清错/新owner连续报活/真实HOME恢复仍待该后端及实体资格，不把诊断子集宣称完整运动控制服务。
- provider保留IRQ前锁存实际长度/status/cookie、精确N×64、IOC/实际长度/CRC检查、独占消费和COMPLETE。HP1取消仍保留terminate/reset/回调/描述符/模块引用及quarantine语义；未添加未经证明的DDR drain属性。
- 新只读sysfs观察由现有bsp_rs485提供，不打开设备、不consume、不取消或分配buffer；不新增控制所有者。PL stopped/drained、HALTED、hp_idle或稳定等待都不单独证明DDR写静止。

当前发布门禁集中如下，用户已确认暂不具备实体/厂商资格，继续保持：

|门禁|具体影响|可选处置与所需输入|
|---|---|---|
|SYN-5066受保护S2MM多驱动|综合删除内部驱动的等价性未证明，禁止bit/HPF/启动链发布|提供同参数厂商资格结论，或批准官方修正版并补测；架构迁移须另审，不能直接换实验IP|
|同步器/CDC与IO时序|async_reg源码标记和当前端口false-path不能替代物理同步资格；RS485外部时序未关闭|核验映射同步链、恢复/撤销复位路径、实际外部时序/电气；不扩展false-path或编造delay|
|实物速度等级/DDR|speed2只是工具参考；配置保持不等于实物压力测试通过|核心板/FPGA丝印、修订、供电与DDR训练/压力证据|
|安全输入电气与接线|球位/低有效已选定，实物触点与断线可检出性未证明|实际上拉值、触点/接口保护、急停NO/NC独立性及测量；无电机逐路拉低验收|
|生产HOME与驱动参数|PROFILE2夹具有效位不是生产批准，不能真实运动|确认机械方向/参考/退离/上限、驱动脉宽/极性、复电旧目标恢复；另建生产参数并重跑受影响验证/P&R|
|HP1中断RX后的DDR写静止|取消成功不能释放未知在途写buffer|厂商reset/drain保证加实板验收；未证明则quarantine，不能用延时或PL排空代替|
|实体485保护资格|无从机超时运输不能算有效保护反馈|实际型号/地址/固件、0x3E语义、STP查询及换向/迟到边界证据|

没有联系厂商、操作示波器、占用COM4、写SD/eMMC/QSPI或启动实体DMA。本任务新生成的rootfs仅离线软件交付物，不能与旧scope BOOT/bit混装启动。
