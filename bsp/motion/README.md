# Linux → MM2S → 内部四轴运动验证

本目录是 BSP 集成与受控 Linux client；冻结 PL、规范与 Golden 保持只读。源码身份、最终时序、镜像哈希与验收范围见 [BUILD_STATUS.md](BUILD_STATUS.md)，机器清单见 [DELIVERY.json](DELIVERY.json)。全板历史见 [../BOARD_VALIDATION.md](../BOARD_VALIDATION.md)。

`/dev/bsp-motion` 仅提供有类型的 ioctl，单打开者且要求 CAP_SYS_RAWIO；不提供 mmap、任意物理地址或任意寄存器访问。生成 C 定义来自唯一规范，MOT2 为72B小端、CRC32/ISO-HDLC。每包1..910条；设备 DMA API/coherent/mask32/地址8B对齐，BTT=count×72，提交前 PACKET_ARM。只提交 MM2S，S2MM仅预约用于共享 controller reset，不投 RX。IOC 与 packet_closed 均确认后才归还 buffer；record_accepted、point_done、session_done 从真实新运动窗口分别确认。

命令 writer 与 STOP/快照分离，等待 PAUSE 不持有 STOP 所需锁。显式 LINK_RECOVER → DISABLE/维护 REBASE → ENABLE → OPEN_SESSION → 按信用预缓存 → START；PAUSE/RESUME、END 和 DISABLE 分别验收。恢复先阻断生产并 GP STOP，等待 pulse-safe 后 terminate_sync 两方向，同步 IRQ/tasklet/描述符队列并确认 HALTED/reset clear，再稳定复查、检查 PL 半包与队列清空、新 generation/LINK_RECOVER、处理 fault、读取保留位置。恢复不会重新 OPEN/START 旧 session。释放前必须显式 MOTION_RELEASE；停止失败 quarantine 保留 coherent buffer、通道和模块引用，禁止释放、重用、自动继续。

测试配置仅内部 STEP/DIR/EN：3/2/4/7/5/3 cycles、验证 max10MHz、raw64/prepared8/START32。冻结 RTL 默认参数0不允许运行。注入接口受 DTS `bsp,isolated-motion-test` 和权限门禁控制；不作为驱动器参数或产品性能冻结。

## 复现

Windows 在已有已验收 `bsp/work/gp_soc_prj` 上生成独立工程（不要覆盖参考工程）：

```powershell
python pl_motion/verify_motion_delivery.py
python bsp/scripts/prepare_motion_hardware.py
python bsp/scripts/regenerate_motion_ps.py --hp0
python bsp/scripts/integrate_motion_hardware.py
python bsp/scripts/build_motion_hardware.py --dma
python bsp/scripts/regenerate_motion_ps.py --export-hpf
python bsp/scripts/audit_motion_hardware.py
```

本次实际因首次 supervisor 中断，从 place DB 完整重跑 route/STA/诊断/bitgen，原始 Tcl 与日志位于 `bsp/evidence/motion-hardware-20261013`，不是引用 PL 参考签核。HPF exporter 本次产物匹配但进程未退出而超时，后续脚本增加 exit。独立 Linux VM 使用固定基线 kernel/vendor/toolchain；TASK=$HOME/embedded-bsp-motion，vendor 指向原基线、SDK 为独立复制，上传 LF 的 bsp 源码与匹配 system.hpf，先运行：

```sh
TASK=$HOME/embedded-bsp-motion GP_RESET_BOOT=1 PLATFORM_NAME=project_motion_isolated FSBL_VARIANT=fsbl_motion_isolated bash "$TASK/bsp/scripts/build_fsbl.sh"
bash "$TASK/bsp/scripts/build_motion_software.sh"
DMA_STATUS=okay bash "$TASK/bsp/scripts/stage_motion_boot.sh"
DMA_RESTAGE=1 bash "$TASK/bsp/scripts/stage_motion_rootfs.sh"
python3 "$TASK/bsp/scripts/make_sd_image.py" "$TASK"
python3 "$TASK/bsp/scripts/verify_motion_image.py" "$TASK"
```

不要设置 BSP_DIR 给 SDK make；其厂商含义与脚本目录冲突。工具路径与固定内核/config/symvers门禁写在脚本内。完整源、FSBL map/disassembly、编译日志、镜像/debug 均封装在 `bsp/artifacts/motion-validated-release.tar.gz`；Git 保存源码、哈希清单和原始证据，镜像文件按既有规则忽略。部署使用 `write_sd_windows.py`，每次重新核对 disk UniqueId/容量/USB/非系统、全512MiB读回；只接受清单中的镜像和 PARTUUID。回退镜像保留，禁止 eMMC/QSPI。

冷启动使用 `capture_serial.py`、COM4/115200/8N1/DTR=RTS=false，由用户上电；全部身份门禁通过后 `serial_exec.py --script bsp/scripts/board_motion_accept.sh --arg 2176bfe4-02`。root 密码通过 stdin，不写文件。原始日志旁 JSON 记录脚本、参数、收发字节、哈希及退出码。

普通SCHED_OTHER在最终两路满CPU负载复验发生欠流，必须保留该限制。显式新session的FIFO50有限隔离调度测试用 `serial_exec.py --script bsp/scripts/board_motion_supply_fifo.sh`；此脚本仍是测试配置，不自动恢复旧轨迹、不证明Linux最坏界。失败后安全释放使用 `board_motion_safe_release.sh`。`summarize_motion_board.py`校验原始日志哈希、6400批时间数据、四轴脉冲积分和最终IRQ静止；仅在内存去除插入的console printk，原始日志不改写。
