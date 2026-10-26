# 第2、3、4阶段实板验收登记

当前全部实板步骤为 **NOT_EXECUTED**。离线镜像生成不等于阶段通过、写卡或运动许可。第1阶段为用户报告 cf764ad 基础三电机测试完成，保留其原始记录；本任务没有重新执行。

## 当次前置检查

1. 先核对最终 manifest、SD 型号/容量/序列/UniqueId、系统盘排除、原卡与回退卡保存位置。单独申请该卡的覆盖授权；不沿用历史 disk1，不操作 eMMC/QSPI。写入后按最终镜像长度完整无缓存读回比对，再核对 MBR 与 PARTUUID。
2. 确认当次串口未被其他程序占用，再使用实际端口、115200/8N1、无流控、DTR/RTS=false。用户负责断电、接线、插卡、上电。不要用开串口推导上电或接线许可。
3. 第2阶段驱动不得收到 STEP：用户断电后断开脉冲输入或采用经确认的隔离方式；不能仅依赖 EN 或网页 STOP。控制侧保留供电，安全输入只接合规 3.3V 域，J12-2 为 GND，J12-1 不是探头地。
4. 记录本次固件/驱动地址、STP/EN模式、急停/接点接线和实际隔离状态。未知接点不做 HOME；PROFILE2 fixture 的配置有效位不是生产参数批准。

## 第2阶段：静态启动和安全链

启动后只读命令：

```sh
cat /etc/full-system-identity.json
uname -a
cat /proc/cmdline
cat /proc/meminfo
cat /proc/interrupts
ls -l /dev/bsp-motion /dev/bsp-saf2-exec
ps
ps-local state
ps-local telemetry
dmesg | tail -100
```

通过标准：根 PARTUUID 与交付一致；wifi1 内核、1GiB 内存配置/CMA和设备窗口/IRQ匹配；设备 root:root 0600，只有一个 hardware 服务；simulation=false，无新 owner、心跳提交、HOME、REBASE、ENABLE、START、R5S2 RUN 或旧任务重放。允许驱动绑定时 STOP、快照请求和运输静止检查，不把它写成完全无寄存器写。真实 XYZ 与 driver_feedback 必须保持 null；命令位置只标 PL STEP 累计。两个采样间的快照 ID/源时间应推进，250ms 未更新应标 stale，不能补零。

用户逐路操作 HOME/限位/急停触点，保存操作前后 `ps-local telemetry`、IRQ计数与原始安全快照；比较实际电平、低有效极性、故障原因与最大响应时间。急停动作反馈不是实测12V断电。任一路接点错误、意外 STEP/EN、身份不符、IRQ风暴或数据来源不明，立即停止，用户切断运动侧电源，保留日志。

无运动 STOP：

```sh
ps-local stop
ps-local state
ps-local telemetry
```

通过标准：返回 received 只算接收；必须在写后新快照中同时看到 MOT2 STOP_COMPLETE、SAF2 DRAINED 和 pulse_safe，且无后续 START。失败、超时、quarantine或身份变化均不得报告停止通过，不卸载模块、不释放未知DMA、不延时后强行复用。

### 配置、心跳与重启子项

配置维护与运行服务不能并开设备。先 `ps-local stop`，确认 pulse_safe、无 dma_owned/quarantine、未开始运动和旧owner情况。需要关闭观察服务以做维护时，在本阶段当次操作确认后才对 `/run/ps-hmi/pid` 记录的进程发 TERM；不卸载驱动。关闭会触发原运动驱动的停止/静止检查，保留结果。进程关闭后：

```sh
saf2-maint snapshot
# TXN 必须根据当前 accepted/applied 取新的非零递增值；不照抄历史值。
saf2-maint config TXN 7 2000000 2000000
saf2-maint snapshot
/etc/init.d/S47ps-hmi start
ps-local state
ps-local action open
ps-local telemetry
```

config 和 OPEN 都是显式实验操作，执行前另行核对本次无电机隔离与实际输入条件；OPEN失败保留错误，不伪造R5S2健康。当前没有服务内R5S2采集管理/原始帧发布，真实保护反馈资格不满足时这一子项停在此处，**第2阶段不能总记PASS**。

只有当实际 config accepted/applied、R5S2 身份/RUN/代际和本轮三轴有效0x3E反馈被唯一采集owner证明后，才验证健康心跳：源时间/last_sequence持续推进；挂起关键服务或终止后，旧owner在PL期限到期撤销、完整停止/失能和位置失效；重新启动服务不喂旧owner、不重放。记录实测PL时间，不以主机sleep证明精确期限。可用 `ps-local action close` 显式关闭合法本轮owner；新OPEN须满足PL空闲规则。

故障恢复须先人工排除原因、确认停稳/失能和本轮真实反馈，再按旧owner关闭/撤销、新OPEN、健康报活、安全CLEAR、显式MOTION_RECOVER分别观察ACK与新快照。工具入口为 `ps-local action clear` / `recover`，返回queued不是成功。STOP后的旧owner不能CLEAR/HOME。当前生产HOME未获准，**不得调用 `action home`，不得以PROFILE2参考步数代替机械参考**。中断HP1 RX缺DDR写静止证明时保持quarantine，不以PL drained解除。

## 第3阶段：本地同后端低速小范围运动

前置：用户明确确认第1、2阶段通过；第2阶段所有影响项关闭；真实位置来源/标定/参数revision、机械正向、复电旧目标一致性处理和HOME参考经批准。先在脉冲隔离情况下确认本镜像5µs STEP高/低及5µs DIR guard适合实际驱动，与cf764ad的31.25µs差异已被接受；若需修改参数，必须另做完整PL、HPF、FSBL/启动链并复测受影响RTL/时序/波形。

**当前产品缺口使本阶段 BLOCKED，尚无可执行的合格三轴运动命令。** 不能用模拟注入、最新目标、测试fixture参考或`delta-scope init/REBASE`绕过。不要直接启动第二个`ps_control hardware`与服务争抢设备。

补齐后，本地入口仍是同一服务的 `ps-local request < request.json`，按当前 `/state` 取得 boot、parameter_version、start_position_id，再请求 `/preview`，审阅绝对步数/方向/低速小范围时长，最后以当前preview_id、唯一client_command_id和未过期deadline提交 `/commands`。具体点位、速度、最大步数、持续时间和允许轴由用户在当次条件下确认；本清单不预填未经标定的XYZ。

通过标准：分别记录queued、accepted_seq、DMA IOC/packet_closed、done_seq、单次END和空队列，最终完成条件全满足；小范围往返的实际驱动响应与命令步数一致，M4不动。运动中 `ps-local stop` 验证取消；故障输入验证全轴停止与不复活。任一方向、脉冲、响应或停止不符立即停止、用户断运动侧电源，定位后仅复测受影响范围，不扩大行程。

## 第4阶段：网页与任务/日志

前置：用户确认第3阶段通过；使用同一镜像/后端；网页取得控制前本地执行 `ps-local release`。局域网地址须在本地明确配置到 `/etc/ps-hmi/bind-ipv4`，维护停止并重新启动服务后使用准确的 `http://板卡IPv4:18083/`；IP变更需重新显式绑定。默认127.0.0.1，Wi-Fi凭据/批准与HMI令牌均不随镜像分发，不关闭Host/Origin/CSRF检查来迁就地址。

用户在本地读取新生成令牌完成认证；核对真实后端标识、未知/stale与目标/命令位置分开显示。先只验证预览、保存/加载任务不运动、日志查询/详情/固定快照JSONL下载与历史boot来源。再按第3阶段同一低速范围显式运行；逐项测试方向长按、释放、失焦、页面隐藏、断线/超时STOP、重连不重放、任务完成/取消和日志关联。

通过标准：方向刷新丢失后按既定350ms输入租约请求STOP，并用真实写后快照确认停止；网络STOP不替代硬急停。取消/过期preview、旧boot/command不能执行，日志下载逐字节对比板端导出内容，不哈希日志。当前真实方向/XYZ/RS485发布未补齐时对应项保持BLOCKED；模拟浏览器回归不算实板通过。

## 逐项结果

|项目|结果|实际读数/证据|
|---|---|---|
|第1阶段基础电机|USER_REPORTED_PASS|cf764ad；本任务未复测|
|当次SD身份/覆盖许可/完整读回|NOT_EXECUTED|尚未申请写卡|
|当次串口/隔离/用户冷启动|NOT_EXECUTED|未打开串口|
|第2阶段启动/驱动/快照/输入/STOP|NOT_EXECUTED|待离线镜像完成后逐项执行|
|第2阶段R5S2发布/健康/完整恢复|BLOCKED|服务发布与管理缺口，真实反馈/实体资格未验|
|第3阶段本地运动|BLOCKED|真实XYZ、标定、生产HOME/参数与第2阶段未通过|
|第4阶段网页实际运行/方向|BLOCKED|沿用第3阶段阻塞|
|第4阶段网页只读/存储/日志|NOT_EXECUTED|宿主回归不替代实板|
