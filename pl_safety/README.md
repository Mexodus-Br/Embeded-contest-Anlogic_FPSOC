# PL safety / parallel HOME

2026-10-18新增SAF2/R5S2联锁：行为与接入见[INTERLOCK_CONTRACT.md](INTERLOCK_CONTRACT.md)，
完成情况和门禁见[INTERLOCK_HANDOFF.md](INTERLOCK_HANDOFF.md)。旧SAF1/R5S1入口默认行为保留。
新验证使用interlocks.py、interlock_real_system.py、build_interlock.py及audit_interlock.py；
下文历史封存/验证脚本含扩大哈希范围的旧规则，未经修改不要用于新交付，AGENT.md §11.5优先。

SAF2复现入口（从仓库根目录；每个tag必须新建，Questa仅串行运行）：

```powershell
$py = 'C:\Users\boru\AppData\Local\Programs\Python\Python310\python.exe'
& $py pl_safety/generate_interlock.py --check
& $py pl_safety/verify_interlock.py
& $py pl_safety/tests/interlock_suite.py --tag NEW_SUITE
& $py pl_safety/tests/interlock_regressions.py --tag NEW_REGRESSION
& $py pl_safety/tests/interlock_real_system.py --tag NEW_REAL
# 以下也占用同一Questa许可，必须等上一项退出后串行运行。
& $py pl_safety/tests/interlock_real_system.py --tag NEW_REAL_WD --scenario watchdog
& $py pl_safety/tests/interlock_real_system.py --tag NEW_REAL_FB --scenario feedback_timeout
& $py pl_safety/build_interlock.py --tag NEW_BUILD
& $py pl_safety/verify_interlock_build.py --build NEW_BUILD --real NEW_REAL --tag NEW_IDENTITY
& $py pl_safety/audit_interlock.py --build NEW_BUILD --tag NEW_AUDIT
& $py pl_safety/report_interlock.py --build NEW_BUILD --audit interlock_audit_NEW_AUDIT --tag NEW_REPORT
```

新runner保留独立失败结果且不计算文件哈希。完整TD缓存依赖此前完整参考工程缓存；
真实系统将本轮实际编译RTL和头文件逐字复制到新run目录，验证副本不会随之后源码编辑漂移。
资源/时序使用含native PS的完整system_wrapper；真实IP仿真在GP/HP端以原BFM驱动真实
受保护转换器与两DMA。均不生成部署镜像，不执行COM4或板卡操作。
超时系统场景明确向已有统一时间寄存器注入非生产跳转；实际UART、GP、两DMA及背压
继续运行，用于隔离验证超时与取消逻辑，不据此证明两秒实体计时或机械保护。

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
