# PL safety / parallel HOME

现行行为与接口见 [CONTRACT.md](CONTRACT.md)。2026-10-16 用户已授权 RTL/自检；生产参数、接线/电气、实体轴映射和板级验收仍未完成。production.json 默认禁止启动。仿真和资源夹具禁止用于电机。

实现位于 rtl/；旧运动底座只扩展 motion_executor、continuous_motion、motion_service 的可选私有接口，HOME_SUPPORT 缺省 0。新安全候选入口是 generated/safety_rs485_gp_ps_top.v，生产 CONFIG_PROFILE 缺省 0。generated/safety_*.v 是独立候选，不覆盖历史顶层；从实际六窗口架构增加第七窗口，并通过真实 GP/HP/DMA 通路验证。

单一接口源仍为 ../pl_interface/schema.json；本目录 generate.py 生成 safety_defs.h/vh 和版本化安全配置参数。generate_top.py 生成接入连线。不要手改生成物。

```powershell
python pl_interface/generate.py --check
python pl_safety/generate.py --check
python pl_safety/generate_top.py --check
python pl_safety/verify_delivery.py
# 每个 tag 必须未存在，旧日志不覆写；Windows 仿真器需普通本地进程环境。
python pl_safety/tests/inputs.py new_inputs_tag
python pl_safety/tests/router.py new_router_tag
python pl_safety/tests/overflow.py new_overflow_tag
python pl_safety/tests/resource_fixture.py new_resource_fixture_tag
python pl_safety/tests/run.py --tag new_unit_tag
python pl_safety/tests/run.py --tag new_phase_tag --sweep --mode 2 --mode 3 --mode 11 --mode 12 --mode 13 --mode 14 --mode 15
# 以下涉及唯一 Questa license，串行执行。
python pl_safety/tests/real_system.py --tag new_real_tag
python pl_safety/tests/regressions.py --tag new_regression_tag
python pl_safety/build_td.py --tag new_full_top_tag
# 严格余量目标候选：高扇出/逻辑级数优化，时钟仍10ns。
python pl_safety/build_td.py --tag new_closure_tag --optimize-physical
# 可选：先核验工具预算语义，再从同一RTL的已完成布局独立再布线。
python pl_safety/probe_margin.py --build completed_full_tag --tag new_margin_proof
python pl_safety/route_closure.py --build placed_full_tag --tag new_route_tag --margin-proof new_margin_proof
```

tests/run.py 的模式 16/17/18 向时间接口注入加速时间，专门验证三阶段超时先到；不用于证明1MHz时间基准。其他集成模式及真实 IP 系统使用共同100MHz/1MHz。testbench 依据实际引脚边沿核对 signed64位置、脉冲总数、H/L/DIR/EN时序和固定退离，不以控制器内部计数作参考答案。

build_td.py 校验 round2 封存的完整实际工程输入，然后在本目录 build/ 新 tag 建立独立候选，保留原厂 IP/PS/DDR和原九输出/RS485约束。完整顶层参考 speed2、10ns，CONFIG_PROFILE=2 为匹配500cycle脉冲参数的资源夹具；不生成 bit/HPF/FSBL/启动镜像。四个新安全输入未分配经核验针脚；工具自动 pad 不可用作接线。全顶层 STA 与实体输入/板级资格分开。

2026-10-17起启动脚本固定threads=16：TD Tcl实际属性为`set_param flow thread 16`，并用`get_num_thread`记录实际值。最终封存要求布线setup WNS严格>1ns、hold≥0和有效约束；默认线程数的历史试验不满足本次要求。`audit_cdc.py --build TAG --tag NEW_TAG`也显式16线程。

原发布、日志及 verifier 保留；原身份门禁会拒绝本轮新源码/新 schema，这是预期保护，不应放宽旧门禁。新交付用本目录独立身份核验。PL 队列清空不证明 DMA/DDR 静止；BSP 按原生命周期处理在途 buffer/quarantine。

原 SYN-5066、RS485 IO 时序资格、实物 speed 和驱动复电行为等问题继续保留。该交付不增加 Watchdog/RS485自动停机策略，不包含 BSP驱动/设备树/镜像/实体接线，不操作COM4或板卡。

最终结果与接续工作见 SAFETY_HANDOFF.md；失败与中断说明见 FAILURES.md。独立封存清单为 SAFETY_RELEASE.json，使用 verify_delivery.py 核对源码、Git blob 和证据身份。
