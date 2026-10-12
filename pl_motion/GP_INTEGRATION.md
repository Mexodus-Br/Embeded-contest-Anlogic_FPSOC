# GP 控制实现与 BSP 集成交接 — 2026-10-12

冻结契约：`gp_control_probe_v1`，规范提交 `ca50bbf`；唯一机器源 `pl_interface/schema.json`。本文件提供实现/连接和验证证据，不改变窗口、IRQ 或语义。用户在 BSP 任务明确答复“授权 PL 任务继续实现”，实现工作限 PL 文件；BSP 负责实际 PS 工程、HPF/FSBL/DTS/启动镜像。

## 实现与生成路径

- `pl_motion/rtl/gp_control_regs.v`：独立 Lite A33/D32 从机、完整窗口判断、事务捕获/缓存、NOP/SNAPSHOT、TEST_RW、IRQ、1MHz 时间戳。计数源只读，不能写位置或提交运动。需要已同步释放的 `rst_n`。
- `pl_motion/rtl/gp_control_top.v`：可集成 PS 边界模块；实例 `converter` 是当前 TD AXI Protocol Converter 1.0，AXI3 → Lite，A33/D32/ID12。自研两级共同复位释放链；四轴快照接 0/invalid 空闲源。没有电机或 DMA 端口。
- `pl_motion/prepare_gp_ip.py`：复制当前安装目录的**未经修改**厂商受保护 RTL 至 `pl_motion/build/gp_ip/axi_protocol_converter_merge.v`，输出 `manifest.json`（厂商库/Component/schema SHA256 与实例参数）。实例使用原厂参数化 RTL，**不是旧示例 wrapper，也不是 wizard 生成的 XML**；BSP 工程需将这份库作为 HDL source 一起导入。
- `pl_motion/tb/tb_gp_control_regs.v` / `tb_gp_control_top.v`：独立模块与真实厂商转换器集成自检，Verilog 编写。
- `pl_motion/tests/run_gp.py`：先 Icarus 独立模块，再 Questa 真实受保护 IP；不支持缺失仿真器时跳过或使用 stub。
- `pl_motion/build_gp_td.py`：真实 TD 综合与固定 10ns STA，可执行 OOC 布局布线。TD include 配置与本机手册存在差异，构建目录忠实展开唯一生成头文件后 analyze；不改变 RTL 逻辑、厂商库或 ABI。

该方案不要求 BSP 的 Design Integrator 自动生成转换器 XML：可在 system wrapper 中实例化 `gp_ps_control_top` 并将四个自研 RTL、完整厂商库和唯一生成头文件加入 TD project。若另用 DI 生成实例，必须核对全部同值参数并重新做集成仿真/STA，不能直接复制 AXI4/13bit-ID UART 示例。

## 实际 PS 端口适配（本次核对结果）

**BSP 应实例化 `rtl/gp_ps_control_top.v`**，并加入 `gp_ps_write_adapter.v`、`gp_control_top.v`、`gp_control_regs.v`、完整厂商库及唯一生成头文件。该PS封装沿用所有 `gp_*` 信号名，但SIZE为2bit、LOCK为1bit，并且没有gp_wid输入；PS实际生成模块为 `bsp/work/gp_soc_prj/system/ip/system_ARM_Processor_System_0/RTL/ARM_Processor_System_f6ddd1d59490.v`，read-only核对及SHA见 `GP_PS_PORTS.json`。GUI参数使能本身不能证明端口已生成。

封装明确补零到转换器内部SIZE3/LOCK2。AW接受时锁存AWID供内部WID；AW到B握手期间禁止新AW，W在AW接受以后才转发，**最后一个WLAST握手后也禁止下一笔W，直到本笔B完成且下一笔AW接受**。WID从所有权寄存器取值，绝不跟随实时AWID；复位清空所有权和数据完成状态。没有截断A33地址或12bit应答ID。

这是对实际PS不提供WID端口的保守串行写适配，不改变冻结A33/D32/ID12、寄存器行为或运动接口。额外等待仅影响GP写访问：W比其AW至少晚一拍，下一AW比前B完成至少晚一拍；未承诺GP吞吐数值。通用 `gp_control_top` 接口保持供独立转换器集成测试使用；其WID12是内部AXI3信号，**不是实际PS外部端口**。

适配器Icarus自检3,167检查（1–16拍写、先W、下一AW保持、不同ID、WLAST后迟到W、B背压、各阶段复位）通过；真实PS封装使用同一集成断言，Questa7,216检查通过。全幅AXI3封装也7,216检查通过。未宣称硬PS内部已完成全协议认证或板级GP可用。

## PS 接线（一个共同域）

| PS 端口/系统资源 | GP 顶层端口 | 连接要求 |
| --- | --- | --- |
| H16 板载 100MHz | `clk_100m` | 合法全局时钟网络，真实系统顶层约束 10ns；不连接 p2f_clk0 替代 |
| `master_gp0_axi_aclk` | `gp0_aclk` | 输出是上述同一 100MHz 时钟，无分频或门控 |
| PS `p2f_rst0_n` | `arst_n` | 同时复位转换器/寄存器/时间戳；不得仅复位 GP 部分 |
| `f2p_irq[15:0]` | `f2p_irq[15:0]` | 唯一有效 bit0，其他为 0；电平高，不另加脉冲整形 |
| `master_gp0_axi_awid/arid/bid/rid` | `gp_awid/arid/bid/rid` | 全部 12bit，不截断 |
| `master_gp0_axi_awaddr/araddr` | `gp_awaddr/araddr` | 全部 33bit；不能在 PS wrapper 先截断 |
| `master_gp0_axi_awlen/arlen` | `gp_awlen/arlen` | AXI3 4bit |
| `master_gp0_axi_awlock/arlock` | `gp_awlock/arlock` | 实际PS1bit；PS封装内部补零到通用AXI3 2bit |
| 其他 GP0 AXI 同名尾缀 | `gp_*` | W/RDATA 32、WSTRB 4、实际PS SIZE 2（内部补零到3）、BURST 2、CACHE 4、PROT 3、RESP 2，VALID/READY/LAST 为 1bit |

GP0 ACLK 在厂商组件中为输入。当前安装 converter 的参数化端口声明及真实 Questa 编译/TD elaborate 已核对 A33/D32/ID12、AXI3 LEN4/LOCK2/WID12；转换器端口与实际生成PS raw端口均已read-only核对，差异由上述PS封装适配；不能据GUI字段或旧custom wrapper推断端口可用。启用 PS `Master_AXI_GP0_Interface` 与 `F2P_IRQ_Available` 后逐项核对；保持 DDR/存储配置不变。SPI82/INTID114 是冻结的资料推导映射，真实 HPF/DTS/板级中断仍须独立验证。

## PS p2f_reset0 作为共同复位来源

BSP 提出的启用 `P2F_Reset0_Available`、使用实际生成的 `p2f_rst0_n` 接 `arst_n` **符合共同复位契约**，前提是该实际生成信号为低有效且用于整个上述 PL 控制域。无需增加外部复位 IO，也不提供 GP-only reset/驱动 reset ioctl。

本机 FD SDK `fpsoc/chip/dr1x90/common/src/al_top.c` 第 48–69 行：`AlTop_P2F_RstAssert(Index)` 清全局 P2F reset 位，`AlTop_P2F_RstRelease(Index)` 置位；Index=0 表示第一路。SDK 操作证明复位控制的低有效语义，但实际生成端口和冷启动状态仍应由 BSP 核对。

建议启动流程：初始化期间 assert 第 0 路 → 配置 PL 完成且板载100MHz已工作 → 在 FSBL/受控启动路径 release 第 0 路 → 等待两级同步释放及初始化 → Linux 开放 GP MMIO。不要把 boot-time assert/release 操作放入 Linux probe，也不要运行中 toggle。整域重新复位前软件停止访问并使 AXI 通道静止，建立新 epoch；如果该 PS 信号也会被其他运行中流程自动拉低，须消除冲突后才部署。

SDK 同文件 `AlTop_GPPortEnable()` 还会切换 GP/HP 的 soft reset（不限 GP0）；BSP 须审核现有 FSBL 通路和释放顺序，不能在已运行的系统为测试 GP 直接调用该函数。GP port 内部 reset 与此共同 PL reset 是两项需协调的硬件状态，后者不能作为前者已经释放的证明。此处不给 Linux 添加安全寄存器直接写入或常数地址副本。

## 可复现验证

```powershell
python pl_motion/prepare_gp_ip.py --ps-rtl bsp/work/gp_soc_prj/system/ip/system_ARM_Processor_System_0/RTL/ARM_Processor_System_f6ddd1d59490.v
python pl_motion/tests/run_gp.py
python pl_motion/build_gp_td.py --tag ps_final --place-route
python pl_interface/generate.py --check
python pl_interface/tests/test_interface.py
python pl_interface/tests/check_verilog.py
```

Icarus 在 Windows 沙箱曾崩溃；使用已验证正常本地进程环境。Questa 使用本机 2025.2 的 `-batch work.tb_gp_control_top`；`-c` 模式在本机 localhost IPv6 RPC 初始化失败，绝对路径不能当作逻辑库名。`-batch` 正常运行受保护 IP，无需修改许可证或 IP 内容。

首次真实 IP Icarus 编译失败（受保护语法），IpTool 命令行尝试 exit1 未生成实例，Questa 初始 RPC/库名失败，写适配自检初始delta-cycle采样竞争，TD 初始 include 参数失败，原始诊断均留在 build，摘要及证据见 `GP_VALIDATION.md`。当前使用厂商正式支持的 Questa 仿真及 TD synthesis，不将任何先前失败冒充通过。

## 部署门槛

PL 自检和 OOC 10ns 报告不代表系统可下载。PS raw端口核对已经完成；BSP仍需将这些实际端口接入系统、集成共同100MHz和 reset/FSBL释放，审核全地址图/HPF/DTS、系统级 STA，再生成配套 bitstream/FSBL/BOOT.bin。首轮 GP 板级结果尚无：MMIO、IRQ 对应 GIC、时间戳、快照和恢复要在 SD 新系统中验收。电机输出和运动 DMA 始终未接入。
