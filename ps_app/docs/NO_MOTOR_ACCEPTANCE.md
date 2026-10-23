# 无电机实板验收清单（待另行授权执行）

本轮只准备清单，所有板端步骤为 NOT_EXECUTED。本清单不是连接串口、写卡、启动 HOME/ENABLE/START 或机械运动的授权；既有受控 ACCEPTANCE 的阶段和实物门禁继续适用。PROFILE0/生产 HOME 未批准时不能越过对应停止点。

1. **固定离线输入。** 保存本任务 Git 提交、对应直接源码和编译器版本。用匹配内核源码/输出/.config/Module.symvers 构建 `bsp_saf2_exec.ko`，检查 vermagic/导入 CRC。核对 PS ELF 加载器、GLIBC/GLIBCXX/CXXABI、rootfs 与内核。当前仅 Linaro7.4 用户态交叉链接通过，不代替目标7.5资格。哈希如需使用，仅限最小最终部署交付物及其直接源码；不哈希日志或整目录。
2. **生成独立候选。** 保留当前已验收系统/回退介质；新 DT 安全节点只替换 compatible 为 `bsp,saf2-execution-v1`，地址/大小/IRQ不变，初始 disabled。保留 MOT2、SAF2、R5S2 身份和配置 ID。未批准 HP1/DDR drain 时不得添加 validated 属性。检查不会同时绑定诊断/执行两个安全 owner，不调用旧 board_scope_ready/init。
3. **取得当次连接/启动/介质操作授权。** 记录实际无电机、驱动与机构隔离方式、电源/急停/接点状态、回退方法与当次候选身份；确认没有其他程序占用 GP/DMA/串口。SD/eMMC/QSPI 操作须明确授权，不能从本清单推导。
4. **静态身份。** 用户启动同一候选后，核对启动根、内核、PL/profile/config ID、1GiB/CMA和 IRQ 前后计数。显式装载已核对模块，执行 snapshot/ACK，只读核对全部初始状态。启动服务后确认无 OWNER_OPEN/FEED、REBASE、HOME、ENABLE、START、RUN 改动；位置未知，日志标 hardware。若存在旧 owner/旧 session/owned DMA，记录 unknown，禁止接管或重放。
5. **旧 owner 与重启。** 在另行批准的无电机看门狗实验中显式 open；从 OPEN 起计首次期限。杀死/挂起关键服务循环，观察旧 owner 到期、完整取消、位置失效、输出排空和失能；重启服务不得喂旧 owner。确认新 OPEN 只在原 owner 失效/明确关闭及 PL 空闲门满足后成功。记录实际源时间与状态，不能用主机 sleep 当精确硬件期限证明。
6. **R5S2 资格停止点。** 通过既有唯一采集 owner 核对 R5S2 身份、当前 config accepted/applied、RUN、generation/revision、每轴本轮0x3E有效枚举2与期限。缺真实应答、任一轴过期/保护1、身份不一致即停止验收；无从机超时不是健康反馈。服务的32B/64B发布接入尚缺，当前 null 必须保留；先补齐 BACKEND.md 中的类型化采集管理/只读发布缺口，才能验收完整产品链。
7. **明确恢复顺序。** 故障原因已人工排除、停稳失能；建立本轮真实全轴反馈；显式关闭尚活动的本轮旧 owner（已撤销则无需关闭）、新 OPEN、首次健康报活；显式安全 CLEAR；获准配置和当次实验条件齐全后才可完整 HOME。STOP 后 BSP 会拒绝旧 owner 的 HOME/CLEAR，验证迟到写无法重启。分别记录请求txn、ACK_ID/accepted/error、全局 HOME状态和完成位置。配置未批准或接点/极性未实测则停在此处。被打断 HOME 必须完整重做，不用 REBASE 替代。
8. **无电机供给（需另行明确允许输出）。** 使用批准的无电机测试参数/接点仿真器与独立测量方案。绑定 boot/command/参数/起点/generation/cancel epoch，测试短 END、多个32条包、水位、正负/零目标、M4不动。分别保存 packet_closed/IOC、accepted_seq、done_seq/valid、END、队列与脉冲计数；IOC 不得先完成命令。测CPU/内存、供给最坏间隙及 underrun；本轮5ms循环/100ms等待不构成实板供给保证。真实 XYZ 产品入口仍受位置估计缺口限制。
9. **STOP/取消/失败。** 在提交前、DMA在途、已接受未完成、包背压、HOME、故障时分别 STOP。比较请求、写完成之后的 pulse_safe/STOP_COMPLETE/DRAINED、位置有效性和 EN；模拟写失败、超时、owner丢失及迟到IOC/反馈不得复活。显式 recover 只允许原 BSP 全部静止证明通过；不确定 RX/TX buffer保持 quarantine，保存故障后状态，禁止卸载/重配/释放绕过。重新规划必须新身份，不恢复旧队列。
10. **只读/来源/并发。** 串口 supervisor 与 Web 接到同一 Service，不启动两个设备 owner；验证认证/CSRF、STOP 独立接纳、SSE/日志/遥测慢消费者。真实/模拟、命令计数/驱动编码器/XYZ、valid/stale、源时间/观察时间与代际分别展示；拔掉反馈或停止发布后变 stale/unknown，不补零。原始32B/64B必须来自唯一owner副本，禁止HTTP注入。退出/重连不自动开 owner 或执行运动。
11. **收尾登记。** 按每步 PASS/FAIL/NOT_EXECUTED 记录实测值、失败和未关闭门禁；仅在 DMA/DDR 全部静止被证明后释放buffer，记录回退。保留故障证据，不计算日志哈希。无电机测试通过也不授权接电机、机械运动、生产参数或正式部署。
