# 决策记录与依赖 — 2026-10-07

## 已确认，不在本次重新选择

PS/PL职责；四轴绝对目标且实际STEP命令位置差分；GP Lite控制+FIFO/HP/DMA数据；PL基础100MHz；u64上电初始化后零起点时间戳；对应STEP边沿<50μs（对应和测量位置未定）；PL三信号半双工RS485 Master/CHECKSUM-8/STP期间轮询；可关闭M4节点；PL整机安全+外部最终急停；唯一机器规范生成Verilog/C原则。本轮进一步确认见末节。

## 第一批集中确认（只决定起步所需项）

| ID | 推荐候选与理由 | 选择影响 / 备选 / 最小缺项 |
| --- | --- | --- |
| D01 | 每点显式相对duration_tick，固定周期可作为profile；预缓存后START连续执行 | 固定周期P更简；绝对execute_tick增加迟到处理。需确认时间语义；实际消费周期/最短最长duration可后续配置但上板前须给范围 |
| D02 | signed64绝对目标/位置、signed65差分，配置软界；STEP H/L、DIR setup/hold、EN延迟和max_rate用cycle/Hz参数，不填未知数 | signed32节省算术资源但需明确量程；需批准位宽与有效边沿。脉宽/最高频必须驱动手册+实测后批准；在此之前只能实现参数化模块、不能接电机 |
| D03 | 1MHz timestamp（1μs，100MHz除100）；STOP/清错/DMA复位保持，PL重配置重建epoch | 100MHz tick更细但单位/换算不同；需批准频率与复位规则、init完成条件 |
| D04 | 欠流/STOP禁止新STEP，完成当前高/低脉宽，取消session；上电position_invalid，HOME或显式维护REBASE建立；不自动EN恢复 | 平滑停需额外算法和轨迹。需确认基础停机/计数边沿/初始化；回零具体流程与失能恢复可继续TBD |
| D05 | JSON（标准库、无额外解析依赖）为唯一源，生成C/Verilog/表格；生成产物入库并check再生一致 | YAML更易注释但依赖解析库。需明确接受格式后提升candidate文件为权威；不因候选脚本能运行而标冻结 |
| D06 | Anlogic通用AXI DMA，首批HP0，64bit stream，simple direct、每记录一个packet，用Linux DMAengine回环 | 示例实际宽度和驱动有依据，但IP配置/Linux集成未验证；SG需额外匹配，FDMA可备选。需确认首批验证接口，不表示板上能力已验收 |

以上可逐项回答，也可只先接受D05以完成权威源迁移。数值时序仍TBD；不要求现在冻结RS485波特率/全部外设引脚或实物轴映射。

## 下一层依赖

- 首个参数化STEP/计数模块：D02/D04、有效边沿、故障同拍优先级、counter valid/rebase契约；H/L/S/Q/E/R可先参数化，驱动前必须定值。
- 调度器：再加D01/D03、共同D预算、对应边沿定义、暂停边界及END/欠流。
- GP寄存器模块：D05、命令/快照mailbox语义、GP时钟/复位/IP适配；地址表确认。
- DMA适配器：D06、TLAST边界、packet/buffer容量、驱动generation恢复；100MHz与DMA域CDC。
- 实物联调：M1–M3映射/极性、电气/限位/回零参数、EN恢复流程、串口STP并发、通信错误策略与安全响应预算、板级DDR电压/工具版本。

## 本轮用户确认（覆盖上文“候选”状态，限以下选择）

2026-10-07，D05答复“接受 JSON，生成产物入库”。D01/D02/D03答复“每点显式相对 duration_tick；目标/命令位置 signed64、差分 signed65；时间戳 1MHz，64位unsigned，STOP/清错/DMA复位保持，PL重配置建立新 epoch”。D04/D06答复“接受”，对应提问中完整推荐：欠流/STOP完成当前脉冲时序后停止且取消旧会话；上电位置无效、HOME或显式维护REBASE建立、不自动恢复EN；Anlogic AXI DMA/HP0/64bit stream/simple/每记录一packet/Linux DMAengine验证。

以上选择已冻结并更新PHASE0 §8与schema.confirmed_decisions。仍未确认：80/128B具体布局、CRC、register/error数值表、DDA算法、暂停/正常END行为、初始化完成条件、有效STEP边沿、配置合法性细节、具体脉宽/频率/消费周期范围、维护REBASE安全门、EN恢复、通信策略、容量/地址/DTS。D06只冻结首批接口选择与验证方向，未证明IP与Linux驱动配套或板上可用。

## 2026-10-09 单轴最小缺项确认（覆盖上文相应待定项）

用户集中答复“接受以上契约”，确认范围：

- STEP 上升沿有效且计数，闲置低；DIR=1 正向；EN 有效极性仍显式参数。
- STOP/欠流/普通故障同拍优先于新 STEP；既有边沿计数保留。
- REBASE 必须 EN 禁用、空闲、无旧会话/待执行命令，提交 signed64/valid；HOME 后续通过相同提交口接入。DISABLE 撤销位置有效性。人工维护授权和队列空由上游保证。
- STOP/欠流/普通故障取消会话并完成高/低及 DIR hold 后报告停止，保留 EN；DISABLE 在 pulse-safe 后按参数释放 EN。复位立即 STEP 闲置/EN 禁用/位置无效，可截短；清错不恢复会话/EN，新执行须显式新会话。

首批仅参数化单轴执行通道，Verilog 自检通过后提出四轴方案，详见 pl_motion/README.md 和 VALIDATION.md。脉宽、setup/hold、EN 延迟、最高频及全部驱动实测数值继续 TBD；80/128B 布局、DDA、正常 END/暂停、初始化完成条件等草案未冻结。
