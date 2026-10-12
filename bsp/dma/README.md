# 独立Anlogic AXI DMA/HP0回环

2026-10-13实板验收完成：恢复修正版冷启动、SD根a3d29e67-02与配套哈希/资源门禁通过；GP前后各41项，DMA444场景全部通过（426正常、12预期超时、6在途terminate、errors0），buffer释放/重分配后复测通过、GP epoch保持、新IRQ各426次且闲置稳定。原始日志和199.756MB/s提交至IRQ口径见../BOARD_VALIDATION.md。下文修正版待测/暂停及首版恢复失败为历史，不覆盖失败证据。专用双通道独占client约束保持；运动FIFO/电机和生产吞吐/停止联锁未验收。

最新状态：首版SD启动、GP41项和204正常DMA逐字节回环通过；GIC115/116各204次，首个RX无TX超时恢复失败，保留buffer/pin模块。恢复修正版在loopback-pair simple专用域跳过依赖packet完成的RUNSTOP等待，采用controller reset，在释放当前描述符前核对两个方向HALTED及RUNSTOP/RESET清；client仍须双向terminate_sync、队列和IRQ/tasklet同步及延迟稳定性，不依据reset自清释放buffer。修正版已构建/校验并部署，未板测；用户要求暂停，详见BUILD_STATUS.md。一般DMA域保留halt/reset错误传播，不擅自切换SG。

当前修正版不可变包bsp/artifacts/dma-recovery-release.tar.gz（SHA256 d832216b0d97b1dc7eca66c8cb945f69bbb480d6e5caec353fda99edde6b61fd）；SD镜像afa13b144ff165d171d3b6c5c7ebe8403a2ef216bfc2bbca3f3de8f88420050d、根a3d29e67-02，provider faf672643a879453328f4ef56a3b481a295633c3adb2afb4503c21965c387c63。首版包和首版失败证据不覆盖。下文原先6be6...和ab260...身份是首版历史。修正版独立串口测试kit为dma-recovery-validation-kit.tar.gz/对应evidence JSON。

PL固定交付7de13f1c5260c8ffad255eb43a28342e7eb32e06、封存9c198a4；唯一profile为pl_interface/schema.json/dma_loopback_v1。本批只集成原GP控制与独立DMA回环，不接运动FIFO或电机。

实际系统入口dma_gp_ps_top，替换旧GP顶层，不并接两完整从机。GP0保留0x80400000/4KiB及SPI82；新增DMA0x80500000/4KiB、MM2S SPI83/INTID115、S2MM SPI84/INTID116 level-high。真实PS HP0为A33/D64/ID6，LEN4/SIZE2/LOCK1/QoS4，无WID；全部H16同源100MHz。DDR保持1GiB、32bit、1333MT/s、1.35V，实际生成DDR初始化不变，仅新增HP0 reset-release/width写；实物供电/颗粒/速度等级仍未测量。

TD全系统100MHz gate/place/route通过，route setup+3.117ns/hold+.020ns，GEN_PL_GP0S及GEN_PL_HP0纳入；speed2为参考。厂商内部dummy2保留，未加false-path或隐藏诊断。bitstream及匹配HPF已导出，FSBL隔离平台project_dma_loop及fsbl_dma_loop中使用原启动common reset0补丁，SDK AlTop_GPPortEnable启动时释放GP/HP内部reset。

Linux内核、.config及主Module.symvers保持原配套；DMA provider以外部模块在此树编译，保留原GPL源输入哈希和补丁，新增provider.Module.symvers供受控client链接。DTS为simple，无include-sg；驱动读取DMASR实际SG位，client拒绝SG并验证mask32。原驱动未使用clock-names，DTS的fixed-clock只描述真实H16时钟，不宣称驱动通过clk API门控该时钟。

修复厂商simple分支一次仅启动首描述符却移动全部pending的问题、非法多SG/超长/未对齐提交、未初始化num_frames/addr_width、错误状态报告、terminate忽略halt/reset错误和synchronize未同步IRQ的缺项。禁止错误时偷偷reset单通道破坏另一方向。双向terminate_sync后额外验证两个方向HALTED、RUNSTOP/RESET清、三描述符队列空，IRQ/tasklet同步，再恢复两个IRQ使能。失败时测试client保留coherent缓冲区和模块引用，禁止复用或卸载，等待人工冷复位；不把单个reset位自清视作恢复完成。

测试client通过provider设备的DMA API分配固定coherent buffer，mask32，地址8B对齐，64B前guard及尾guard；用户ioctl只接受长度/模式/场景，不接受任何地址。CPU填充后dma_wmb，先S2MM再MM2S；双回调和DMA_COMPLETE后dma_rmb逐字节比较。coherent无需streaming cache sync，不假定HP0自动snoop。每次恢复后延迟检查目的buffer未继续变化，未终止前不释放或复用buffer。缓冲区在模块移除且再次通过双向停止后释放；模块加载期间固定保留。

dma-accept预设17种长度（含非整拍、页边界、65535B最大值）×4数据模式×3轮，共204正常传输；3轮接收无发送超时、发送无接收背压超时和显式在途terminate，每次异常后4097B正常包验证恢复，共222场景。记录原始callback、提交/完成/全流程纳秒、累计错误/超时/恢复、代际和停止前状态；要求异常场景实际未完成交易被观测到。aggregate MB/s由提交至IRQ完成时长计算，不称纯总线带宽。DMA完成不是运动完成。新的两路IRQ、数据与恢复仍须实板记录证明。

构建：prepare_dma_hardware.py→regenerate_gp_ps.py --work-dir dma_soc_prj --hp0→integrate_dma_hardware.py→build_gp_hardware.py --work-dir dma_soc_prj --dma→regenerate_gp_ps.py --work-dir dma_soc_prj --hp0 --export-hpf。prepare_dma_dts.py及prepare_dma_provider.py生成候选/头与隔离补丁；VM TASK=~/embedded-bsp-dma运行build_fsbl.sh（PLATFORM_NAME=project_dma_loop FSBL_VARIANT=fsbl_dma_loop GP_RESET_BOOT=1）、build_dma_software.sh、stage_dma_rootfs.sh、stage_dma_boot.sh（审核后DMA_STATUS=okay）、make_sd_image.py、collect_dma_release.sh。

当前完整镜像SHA2566be6b27d1b67d56dc289c85704a1e9d46b7d74d43e96a0e0e258b8a755617897，根PARTUUID a1604a87-02；本地dma-release.tar.gz归档SHA256 ab260d45bf745eea9d9f31a0d052cfedd38f75da4fa3ac9e79fe00570ee8e1c1，23发布文件本地校验通过。已归档镜像之后新增的串口验收脚本/记录单独保存，不改变不可变包。实际部署/板测状态见BUILD_STATUS.md。
