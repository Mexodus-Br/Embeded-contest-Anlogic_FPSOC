# 独立遥测controller：补审与最终确认项

2026-10-14。覆盖DMA_CONTRACT_PROPOSAL.md中共享controller及五端点路由的建议，其余已接受数据/缓存/封装/容量/精确BTT/批量规则保留。用户选择独立controller并要求先补审HP/仲裁及资源；64B封装、15组缓存规则及256条FIFO/16条批量/10ms形成包/精确BTT已接受。用户随后明确接受本增补的独立HP1、资源及局部恢复契约；共享恢复建议已被下文独立恢复规则取代。唯一规范与实现按此冻结，实板资源仍须BSP复核。

## 实际补审证据

执行 `python pl_dma/audit_telemetry_candidate.py`，当前TD2026.1 SP2原厂xmlipgen在pl_dma/build/ps_telemetry_candidate中仅启用HP0/HP1，未修改BSP源配置；证据位于pl_dma/reports/telemetry_candidate/audit.json、generate.log、配置副本及生成Tcl。

- 实际生成PS原始RTL SHA256：df5d61e903b47ce1e9db19e43e83bc179a18ceb5bcf5af6bb1eb37c4fa83b310。HP0与HP1各38个公开端口，HP0逐项方向/位宽与既有HP0_PORTS.json一致，GP0 A33及f2p_irq[15:0]保留。
- HP1实际A33、D64、ID6、LEN4、SIZE2、LOCK1、QoS4、WSTRB8，无WID；wrapper未公开独立HP reset输出，不虚构reset端口。
- 审计六份BSP现有expanded DTS（含motion-validated-release），0x80800000/4KiB、0x80900000/4KiB数字CPU窗口未发现重叠，未发现SPI87/88的直接三cell中断匹配。每份来源SHA见audit.json。不是完整child-bus翻译/最终HPF/中断控制器映射验收，BSP须最终审核。
- 原厂AXI DMA Component.xml和公开RTL参数支持AL_INCLUDE_MM2S/AL_INCLUDE_S2MM独立选择；候选参数AL_INCLUDE_MM2S=0、AL_INCLUDE_S2MM=1，其余沿用simple/SG0/Micro0、地址32、memory/stream64、burst16、DRE/SF1、BTT16、ASYNC0、100MHz。S2MM-only受保护IP尚未在本轮运行功能仿真，须在实现阶段使用真实IP验证，不把组件参数存在当作功能验收。

## 推荐接线与资源

```text
原运动controller（0x80500000，IRQ1/2）→ 原转换器 → HP0 → PS/DDR
独立遥测controller（0x80900000，IRQ6）→ 新原厂转换器 → HP1 → PS/DDR
原GP/运动/RS485诊断窗口保留
新增缓存/遥测GP（0x80800000，IRQ5）→ 配置、快照与包credit
```

1. HP0完全留给现有controller，保留MM2S运动和旧S2MM默认行为；新controller只启用S2MM，独占HP1，不实现HP0多master仲裁。新转换器是另一个实例，使用当前同版本原厂AXI4→AXI3 IP；DMA地址32补高位0，不能截LEN，ID合法适配实际HP1，无WID。HP1读方向闲置，不产生读请求。
2. 新 `dma_rs485_s2mm_v1` 候选控制窗口0x80900000/4KiB，前1KiB按原厂寄存器，由完整A33/D32 guard保护；控制访问4B对齐/完整字写，数据buffer地址8B对齐、32bit DMA mask、BTT合法1..65535（本业务只提交N×64，N=1..16）。未知/禁用MM2S访问由明确白名单拒绝，不提供备用运动入口。
3. 新S2MM中断f2p_irq[6]、SPI88/INTID120，高有效level；不为禁用MM2S分配IRQ。缓存profile保留候选0x80800000、f2p_irq[5]/SPI87/INTID119。原0x804..0x807和SPI82..86保持。
4. 新验证顶层需要六个GP Lite端点（probe、旧DMA、motion、旧RS485诊断、新cache/telem、新DMA）。复用既有PS GP0转换器及所有权适配；新增明确路由，不将从机并联，不修改旧默认生成顶层。旧GP桥内部完成事件及generation通过显式只读观测接口供新分支使用，不能用层级引用代替公开接线。
5. 板载H16同源100MHz驱动GP/HP0/HP1、两controller和转换器；ASYNC0。不新增独立运行时间epoch，time_us仍直接复用64bit/1MHz系统输入。真实PS模型GEN_PL_HP1和最终整体STA必须验证，当前端口审计不替代时序结果。

## 独立复位与恢复：替代共享STOP流程

- 本地遥测CANCEL/错误/软件reset只影响新controller、新转换链及遥测FIFO/半包/credit/transport_generation；不连接原controller primary reset、不写原DMA寄存器，不触发运动GP STOP、取消会话或自动重新启动。采集/cache/旧GP诊断及系统time_us保持原规则。
- BSP为新controller建立独立DMAengine设备与生命周期owner。先关闭新提交/ARM，terminate_sync新S2MM，按该实例作用域协调reset、确认HALTED/reset/IRQ/tasklet/callback和HP1在途DDR写静止；失败buffer quarantine，静止证明后新transport_generation显式RECOVER，重新投RX再ARM。缓冲区/旧callback必须按新controller和transport_generation隔离。不能复用旧双向controller的pair取消助手来“顺便”复位运动controller。
- CANCEL与VALID/READY仍按已接受协议：不能仅撤回held VALID或清FIFO假装DMA已静止；primary reset属于协议复位边界，重建后禁止残留拼新generation。旧GP采集LOCAL_RESET仍使cache无效，已排队遥测保留各自collector_generation送完，不自动reset新controller。
- common p2f_rst0_n/整域重配置仍影响运动与遥测和系统epoch；仅用于启动/受控整域重建，不能作为独立遥测恢复手段。PS侧GP/HP内部soft reset释放和影响范围须BSP核对；不通过reset公共PS/DDR来宣称独立恢复。
- 独立HP端口和controller可实现PL接线及controller reset隔离，**仍共享PS内部互连/DDR带宽**，不能承诺绝对吞吐或最坏运动补给时限隔离。需验证长HP1背压、并发HP0补给及反复遥测reset时运动信号/会话不变；common reset则按原运动安全取消规则处理。
- 上述隔离是待实现/验证的契约，现阶段只完成端口与资源补审；不宣称已验证实板HP1或Linux恢复。

## 后续验证与迁移

已接受的64B CRC封装、不可变完成事件分支、缓存失败保留、原GP FIFO唯一消费、遥测FIFO256/满丢新、精确N×64 RX准备后ARM、最多16条和包槽空闲时10ms形成待发包均不改。新controller仍需真实Anlogic IP检查精确/过大/过小BTT、提前/缺失TLAST、实际长度回读与DDR字节；生产路径不依赖当前simple驱动固定0的residue推断短包长度。

新增独立IP/HP1资源与六端点整体需要独立100MHz综合布局布线，分层报告资源避免重复累计封装。保留旧交付源码/规范数值/证据；BSP只读，不制作启动镜像、不下载板卡、不接电机。确认本增补后才按独立方案实现并最终提交RS485_DMA_HANDOFF.md。
