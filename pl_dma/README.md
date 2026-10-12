# 独立 AXI DMA / HP0 回环

2026-10-13 新增独立运动集成入口 `rtl/motion_gp_ps_top.v`，见 [MOTION_HANDOFF.md](../pl_motion/MOTION_HANDOFF.md)。它采用新运动 GP profile 和 MM2S 记录解包；S2MM 不产生回环响应。下面原回环入口及其契约、行为继续保留，BSP 不得把回环 client 的双向提交流程直接用于运动。

本批仅验证 DDR→MM2S→16拍回环FIFO→S2MM→DDR。没有运动 FIFO、电机或新 GP 命令。唯一契约为 `pl_interface/schema.json/dma_loopback_profiles/dma_loopback_v1`；GP probe ABI/实现及 Golden Model 保持。

BSP 可集成入口为 `rtl/dma_gp_ps_top.v`：共用 GP0 控制，保留原 GP 窗口/IRQ，并新增 DMA 窗口/两路 IRQ。`dma_loopback_top.v` 是独立 AXI-Lite 控制子系统，供已有共享互连的系统使用；不得将两个完整 GP 从机直接并接。

完整连接、源码/IP身份、复现、验收与部署边界见 [DMA_HANDOFF.md](DMA_HANDOFF.md)。受保护 IP 不入库，由 `prepare_ip.py` 从当前安装目录原样复制并校验。`build/` 为可再生输出，不提交。
