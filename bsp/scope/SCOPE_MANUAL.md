# 用户自行操作的无电机 GPIO 实测

本次不接驱动器或电机。A0..A2 是逻辑测试轴，不是最终机械 M1..M3 标定。软件门禁通过不能替代示波器证据。下列测量由用户自行执行；没有测量数据的项目保持未验证。

## 1. 接线与仪器

板卡断电接线，按实际 J12 针 1 标记确认方向。J12-2 接探头地；J12-1 为电源，不能接探头地。每根信号只接示波器，不能同时连接驱动器/其他输出源。

| 轴 | STEP | DIR | EN |
|---|---|---|---|
| A0 | J12-3 / Y12 | J12-4 / Y13 | J12-5 / T9 |
| A1 | J12-6 / U10 | J12-7 / T5 | J12-8 / U5 |
| A2 | J12-9 / V6 | J12-10 / W6 | J12-11 / U7 |

使用 10× 探头，示波器通道衰减也设 10×，DC 耦合、高阻输入，关闭 50Ω 端接。预期约 0/3.3V。地线尽量短，两个探头共用 J12-2 的板端地参考。若仪器接地方式、板卡针序或占用与以上不同，先停止并确认。

先记录型号、通道数、探头、采样率、记录长度及触发设置。两通道也能逐次完成；四通道可以一次看三轴 STEP 和一个 DIR/EN。每次重新接探头时先 STOP、shutdown，确认 EN=0，再断电调整连接。

## 2. 打开终端及受控程序

确认 Codex 已关闭 COM4 后，用自己的串口终端打开 COM4，115200/8N1，无流控，DTR/RTS=false；登录 root/root。不要让两个程序同时占用 COM4。上电不会自动使能或运行。

确认本轮镜像的根分区与文件身份：

```sh
bsp-readonly-check 8aea5f8d-02
sha256sum -c /etc/delta-scope/files.sha256
uname -r
```

内核应为 `6.1.111-rt42-bsp-sd1`，哈希全部 OK 才继续。软件模型固定向量可先查看，它不操作 GPIO：

```sh
delta-scope model --xyz 0 0 -140
delta-scope model --xyz 5 0 -140
```

目标必须分别是 `[-1090,-1090,-1090]`、`[-1089,-966,-1213]`。随后显式装载并启动唯一的受控进程：

```sh
modprobe bsp_gp
modprobe anlogic-dma-engine
modprobe bsp_motion
delta-scope serve --no-motor-test > /tmp/delta-scope-server.log 2>&1 &
scope_pid=$!
sleep 1
cat /tmp/delta-scope-server.log
delta-scope snapshot
```

应出现 `SCOPE_SERVER_READY`；冷启动初态 `signals=0xf0`（STEP=0、DIR=1、EN=0），`dma_owned=0 quarantine=0 buffered=0`。配置有效位为三轴 7，M4 禁用。任何 FAIL、quarantine、异常身份都停止后续测量；不要绕过 `/dev/bsp-motion` 写寄存器或物理地址。

## 3. 固定去程

初始化是无电机维护 REBASE，不是机械 HOME。只做一次初始化，后续 move 从保留的实际 STEP 位置出发：

```sh
delta-scope init --xyz 0 0 -140
```

应打印 `INIT_PASS`，三轴位置 -1090，STEP=0、EN=7。EN 高有效；三轴使能本身可以作为单独一次 EN 捕获。调整触发、按示波器 Single，最后由你执行：

```sh
delta-scope move --xyz 5 0 -140 --duration-ms 500 > /tmp/scope-outbound.log 2>&1
result=$?
cat /tmp/scope-outbound.log
echo result=$result
```

应为 result=0、`MOVE_PASS`、END 增加一次、位置 `[-1089,-966,-1213]`，脉冲增量 `[1,124,123]`，DIR `[正,正,负]`（逻辑电平 `[1,1,0]`）。M4 位置及脉冲为 0。IOC 和 packet_closed 时间戳只是传输/消费节点，不能作为运动完成；程序等待 END 并检查实际位置/计数。500ms 是记录从 START 执行的 duration，不是两个任意脉冲之间的间距。

## 4. 示波器捕获

全程计数：建议 100ms/div（总记录至少 600ms），STEP 上升沿触发约 1.5V，少量预触发。确认实际采样率足以分辨 5µs，建议至少 2MSa/s，600ms 需至少 1.2M 点/通道的有效存储；以仪器实际采样率/存储为准，不能只看面板设置。可保存完整波形/CSV后数上升沿，或使用能针对完整采集记录计数的仪器功能。普通频率显示不证明脉冲总数。

脉宽：另做一次相同去程，使用约 10µs/div、更高采样率（建议 ≥50MSa/s）单次触发，测 STEP 高电平 5µs。STEP 低电平的配置是**最小** 5µs；本次 500ms 低速轨迹的实际脉冲间隔通常更长，不应期待连续 100kHz 方波。测试上限 100kHz 并非本向量的实际频率。

两通道轮次：CH1=A0 STEP / CH2=A1 STEP，完成去程后保存；返回起点后 CH1=A0 STEP / CH2=A2 STEP 再做去程。DIR、EN 使用同轴 STEP 为另一个通道的时间参考，分次重复。要看使能 setup，请捕获 `init` 的 EN，再结合首次 STEP；要看 disable，在正常 END 后捕获最后的 shutdown。避免改线时带电。

同槽边沿：对照 `pl_motion/scope_test/expected_edges.csv`、`scope_test/evidence/observed_edges.csv`、`scope_test/evidence/scope_outputs.vcd` 和 `scope_test/scope_waveforms.png`（后三者也位于 pl_motion 下）。只比较同一个槽、同时产生的 STEP 边沿，不比较不同槽或相邻脉冲。A0 首次 STEP 上升沿发生在仿真 point_start 之后 10.02µs；point_start/done 没有实体针脚，不能把最后 STEP 到 END 的空档当作整个 duration。记录测得偏差、采样分辨率和探头通道偏差；软件同槽同步不证明物理焊球/连接器零偏差。完整 500ms 捕获与高分辨率局部捕获可分开做。若内存/通道能力不足，明确标未验证，不用快照替代仪器结果。

## 5. 返回、拒绝输入及运行中 STOP

返回采用同一程序、实际保留位置，不重新 init：

```sh
delta-scope move --xyz 0 0 -140 --duration-ms 500
```

应回到 `[-1090,-1090,-1090]`，STEP `[1,124,123]`，DIR `[负,负,正]`（`[0,0,1]`），END 再增加一次。

在起点验证拒绝输入；前后 snapshot 的位置、脉冲、END 应保持一致：

```sh
delta-scope snapshot
delta-scope move --xyz nan 0 -140 --duration-ms 500
delta-scope move --xyz 0 0 0 --duration-ms 500
delta-scope move --xyz 1e100 0 -140 --duration-ms 500
delta-scope move --xyz 5 0 -140 --duration-ms 1
delta-scope snapshot
```

以上应全部 FAIL。1ms 拒绝检查必须从起点开始，否则零位移可能合法。

运行中 STOP：起点出发，先按示波器 Single，再自行输入这个明确取消的测试：

```sh
delta-scope move --xyz 5 0 -140 --duration-ms 500 > /tmp/scope-stop-move.log 2>&1 &
mover=$!
sleep 0.1
delta-scope stop
wait "$mover"
echo move_result=$?
cat /tmp/scope-stop-move.log
delta-scope snapshot
```

应 STOP_PASS，move 失败/取消，停止后 STEP=0、位置保留为实际部分位置，EN 仍为 7，END 不应把取消的记录记为正常完成。Linux 的 0.1s sleep 不保证 STOP 到达时恰处于脉冲高电平；若要验证高电平排空需示波器实际捕获到该条件，不能从此命令推断。捕获最后脉冲不被截短、之后无多余 STEP。错误不能自动继续旧轨迹。成功安全停止后，可以显式发送新的返回命令，从保留位置回起点；不要重新 REBASE 抹掉停止位置。

## 6. 结束及证据

```sh
delta-scope stop
delta-scope shutdown
wait "$scope_pid"
rmmod bsp_motion
test ! -e /dev/bsp-motion && echo CLIENT_UNLOADED
cat /tmp/delta-scope-server.log
cat /proc/modules
```

应 `SHUTDOWN_PASS pulse-safe DISABLE RELEASE buffer freed`，三轴 EN=0、STEP=0、client 已卸载，无活动传输。provider/GP 可保持加载但无运动 client 占用。STOP 失败或 quarantine 时不要卸载、释放或重用 buffer，应保留现场与日志并停止操作。

保存输入/模型配置、角度/步数、前后 snapshot、IOC/packet_closed/END、完整 server/命令日志、示波器采样设置和完整波形或截图。记录每轮实际 counts、DIR、电平、宽度、同槽偏差、END/STOP；建议填写 `SCOPE_RESULTS_TEMPLATE.md`。实测结束后关闭终端 COM4。任何通过均限于无电机 GPIO，不扩展为机械或驱动器验收。
