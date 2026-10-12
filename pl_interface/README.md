# PS/PL 接口设计包

2026-10-13：用户接受 DMA→连续运动六项契约，唯一 schema 新增冻结 `motion_integration_profiles.gp_motion_v1` 和 `frames.motion_stream_v2`（72B/MOT2/version2）。新增 GP 独立窗口/profile，不改变原 probe ABI；历史 80B motion/128B telemetry 仍 Draft。执行/恢复和验证边界见 [MOTION_HANDOFF.md](../pl_motion/MOTION_HANDOFF.md)，宿主新格式 codec 为 `motion_v2.py`。

2026-10-07，整体状态 **Draft / 部分决策已确认**。用户本轮已确认项见DECISIONS；完整地址、报文布局、位域和具体时序尚未冻结。

2026-10-12：[GP 最小控制 profile](../pl_motion/GP_CONTROL_DRAFT.md) 已确认，唯一源为 `schema.json` 中 `gp_control_profiles.gp_control_probe_v1`。只有此子集冻结，其他报文/寄存器仍 Draft。生成定义含 profile 专属窗口、IRQ、特性掩码与 reset override；不能把全局草案条目当作支持项。GP RTL/IP/HPF/DTS 和实板验证尚未完成。

- [整体接口、时钟复位与安全](SPECIFICATION.md)
- [运动点及执行数学](MOTION.md)
- [遥测与通信策略](TELEMETRY.md)
- [寄存器与错误](REGISTERS.md)
- [Linux / DDR / DMA](DMA_LINUX.md)
- [厂商依据](VENDOR_REVIEW.md)
- [决策与最小实现门槛](DECISIONS.md)
- [实际验证](VALIDATION.md)

设计范围是接口文档、定义与宿主编解码验证；不含运动 RTL、Linux 驱动、BSP 或电机联调。Golden Model 的算法、配置与期望不变。读其有效目标作为**数值样例**，不能推定机械允许运动，也不继承 AVR16、RAMPS 微步、轴接线或十步补偿。

`schema.json` 是唯一机器规范（JSON及生成产物入库已获用户确认）。地址、错误码、字段offset均从此源派生，禁止手改generated。规范中标为Draft的布局/策略不会因生成而自动冻结。`generate.py`、`codec.py`、`reference_codec.h`、测试是手写工具；generated为派生定义/表格。

```powershell
python pl_interface/generate.py
python pl_interface/generate.py --check
python pl_interface/tests/test_interface.py
python pl_interface/tests/check_verilog.py
python pl_interface/codec.py motion encode pl_interface/examples/motion.json
python pl_interface/codec.py motion decode pl_interface/examples/motion.hex
```

Python标准库即可生成/编解码。宿主一致性测试还要求gcc：实际编译C并核对Verilog字面定义。check_verilog.py是独立HDL编译/常量仿真入口，要求iverilog/vvp，失败非零退出，不自动重试或跳过。本机Icarus间歇进程崩溃见VALIDATION。无运动RTL。示例duration=1000 ticks仅供字段演示，不冻结实际消费周期或批准实物执行。C助手显式按字节读写，envelope检查不等于完整语义校验。
