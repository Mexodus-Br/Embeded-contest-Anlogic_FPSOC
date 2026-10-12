# DMA BSP实际状态

2026-10-13实际验收完成：用户冷启动此前已完整部署的恢复修正版，FSBL→U-Boot→Linux完整日志保存，SD根a3d29e67-02/1GiB/128MiB CMA与配套内核、DTS、provider/client/GP/app哈希门禁通过。GP前后各41项通过；DMA两轮各222场景，共444，正常传输426次/2161698B逐字节与guard通过，12次预期超时、6次显式在途terminate，18异常场景均观测实际在途，随后正常包恢复通过。444次pair检查均quiescent=1，errors=0；client卸载前再次停止，buffer释放后重载重新分配并完整复测通过。两路GIC115/116各426次、GP GIC114最终6次、Err0；额外闲置一秒DMA IRQ计数稳定。GP时间戳47186631→65559292，DMA-only reset/重载保持epoch。最终client/provider/GP已加载、无活动传输，缓冲区由client持有。下方暂停和未验证状态属于历史检查点，已由本次实板证据替代。

提交延迟8.010–16.770μs；提交至IRQ完成17.160–104.970μs，均值25.403μs。聚合199.756MB/s仅为总payload除以累计提交至IRQ完成时间；测试包括每次复位/guard等待/串口打印，不作为持续总线带宽或生产运动吞吐。原始完整冷启动dma-coldboot-20261013-01.log、验收dma-board-accept-20261013-01.log及metadata、只读收尾dma-idle-20261013-01.log均保存；结构化结果dma-board-result-20261013.json，可由summarize_dma_board.py复核。

本批独立Linux→DDR→DMA→PL回环→DMA→DDR及受控恢复验收完成。接运动FIFO前仍须共同冻结记录/packet/TLAST、FIFO容量与预取提前量、欠流/STOP/代际取消、持续负载吞吐与Linux调度裕量、整合运动顶层的真实约束/CDC/复位和停止排空证明；DMA完成不等同运动完成。当前专用client独占双通道、同步串行提交的约束不可直接用于其他并发消费者或任意hot-remove。实物DDR供电/颗粒/速度等级、长时DDR/CMA/存储压力、实体IO和电机另验收，eMMC未修改。

当前检查点（2026-10-12 22:34 Asia/Taipei）：用户因5h额度耗尽要求暂停。恢复修正版交付包dma-recovery-release.tar.gz SHA256 d832216b0d97b1dc7eca66c8cb945f69bbb480d6e5caec353fda99edde6b61fd，本地23发布文件校验通过；修正版SD镜像afa13b144ff165d171d3b6c5c7ebe8403a2ef216bfc2bbca3f3de8f88420050d、根a3d29e67-02。同一Windows USB磁盘1在管理员授权后无缓存写入512MiB24.609秒，完整无缓存读回18.359秒，哈希一致、分区/签名通过，退出0。原始证据dma-sd-windows-recovery-write.log及.json；配套镜像校验和独立串口kit已保存。修正版尚未冷启动、GP回归或DMA恢复复验；未打开第二次COM4采集。下文正常回环通过与恢复失败仅指首版6be6...镜像，不能归为修正版验收。

恢复时先确认修正版卡已装入断电板卡、SD拨码及COM4状态，再使用新的stop-file和独占日志名采集完整冷启动。按根a3d29e67-02、provider faf67264...387c63及现有GP ABI门禁执行board_dma_accept.sh：222场景后只有全部成功才卸载/释放client缓冲区并重载，再跑222场景，核对两路IRQ、epoch保持及GP回归。任何pair-stop失败保留缓冲区，不继续复用/卸载。本批运动FIFO/电机未接入。

板测更新：首版Windows部署后完整SD冷启动通过，GP门禁/41项及204次正常DMA逐字节回环通过，GIC115/116各204次。首个RX无TX超时恢复失败，rx terminate=-110/pair post=-16，client保留缓冲区并pin模块，禁止复用/卸载。故障后GP41项再次通过。停止流程修正版provider W=1编译通过（SHA faf672643a879453328f4ef56a3b481a295633c3adb2afb4503c21965c387c63），保留原内核/GP/PL；正在生成独立修正版交付包。首版恢复未通过，详细原始证据与统计见../BOARD_VALIDATION.md。

最新状态（2026-10-12 22:21 Asia/Taipei）：同一SD改由Windows部署成功，512MiB无缓存写入24.657秒、完整无缓存读回18.375秒，SHA256与源6be6b27d1b67d56dc289c85704a1e9d46b7d74d43e96a0e0e258b8a755617897一致。MBR/分区/FAT/EXT4签名及根a1604a87-02通过，脚本退出0；源fsck已通过，Windows未另跑fsck。eMMC未操作。用户已装卡，COM4冷启动采集就绪，尚未记录板测通过。下文暂停/不可启动卡状态属于此前失败历史，已由此次成功全量覆盖替代。

2026-10-12 Asia/Taipei。PL交付及真实IP身份校验通过；最终PS+GP0+HP0+DMA布局布线、bit/HPF、匹配FSBL/BOOT.bin及DTS构建通过，配套Linux provider/client W=1和dma-accept -Wall/-Wextra/-Werror构建通过。完整SD镜像、rootfs文件内产物、地址/IRQ/simple/mask/BTT、FAT/EXT4与本地交付包通过主机校验。原GP内核模块/测试程序逐字节保留，内核.config及主符号匹配。

SD目标为用户已确认的同一张29.2GiB卡，VM唯一USB可移除盘sdb、读卡器20121112761000000、61132800×512B；系统盘sda排除。本次按新SHA256和a1604a87-02写入512MiB，1315.97秒完成；USB反复复位，power/control=auto→on、ums_realtek ss_en=1→0未消除故障。72.4483秒完整direct读回后哈希不匹配：期望6be6b27d1b67d56dc289c85704a1e9d46b7d74d43e96a0e0e258b8a755617897，实际378bfb27c734a3d108cd383343d652426892aba1ad337378731024a92711e7d0。脚本退出1，烧写进程已退出，后续分区fsck/UUID验收未执行，最终两分区未挂载。失败后只读重算源镜像SHA仍为期望值，源文件未变。

按照用户此前“无法完成写入就暂停任务”的明确指令，本批已暂停，不重试，不启动板卡。当前SD不具备可启动的已验证镜像；不得使用。主机交付包与23个发布文件仍通过本地校验，原GP已板测交付包保留；eMMC未操作。原始失败证据为../evidence/dma-sd-write.log和dma-sd-transport.log。恢复须先解决或更换不可靠的USB写入通路，再核对同一目标并重新全量烧写/读回，换卡须确认。

本批启动、GP回归、新两路IRQ、DMA传输、吞吐/延迟、超时/terminate/恢复及buffer释放后重分配均为NOT_TESTED；已经准备验收程序不代表已通过。不能沿用旧GP板测结果作为DMA通过。

首次软件编译module_platform_driver(driver)与内核driver_init名称冲突，修正bsp_loop_driver后成功；厂商两个W=1告警在副本中按配置/正确注释修正。首轮Python校验使用text=True与VM Python3.6不兼容，改universal_newlines后通过；失败日志保留在VM logs。TD report_route_status -drc实际输出在raw log，没有生成请求的独立.drc文件，完整checker输出仍保留。

DDR物理供电/颗粒/速度等级、长时存储/CMA压力、动态运动快照、运动FIFO/电机及接入生产运动前的吞吐/调度裕量仍未验证。暂停检查点保留；本批Git尚未提交，恢复实际验收后记录并提交。
