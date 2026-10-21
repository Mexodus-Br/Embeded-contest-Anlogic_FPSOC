# 最终实际完整顶层资源与时序

采集时间：2026-10-21T14:56:22.607283+08:00。本报告对应`hardware/`的完整native PS/GP/双HP/九GPIO/SAF2/R5S2顶层，来自冻结rtl_path38 / rtl37_candidate_r5，只固定四路安全输入球位，保留完整PROFILE2资源/功能配置。PROFILE2仍未批准用于真实运动。

**最终名义route setup +0.078ns、hold +0.020ns。无负STA=True；严格setup>1ns=False；发布signoff=false。**

|资源|原rtl_path38|本次最终|总量|已用|余量|增量|
|---|---:|---:|---:|---:|---:|---:|
|lut6|28905|28802|52480|54.88%|23678|-103|
|slice|36694|36670|52480|69.87%|15810|-24|
|slice_ff|37478|37617|104960|35.84%|67343|+139|
|eram|69|69|280|24.64%|211|+0|
|dsp|6|6|240|2.50%|234|+0|
|io|17|17|126|13.49%|109|+0|
|gclk|1|1|32|3.12%|31|+0|
|sclk|6|6|72|8.33%|66|+0|
|pll|0|0|8|0.00%|8|+0|
|lclk|0|0|20|0.00%|20|+0|
|mlclk|0|0|8|0.00%|8|+0|
|ioclk|0|0|16|0.00%|16|+0|

PAD FF=9；完整功能资源配置保持检查=True。本次没有内部RTL、FIFO容量、IP参数、时钟/复位语义或生产功能变更，不将放置/布线差异说成新的逻辑优化成果。

|阶段|setup ns|hold ns|
|---|---:|---:|
|gate|-1.250|+0.000|
|place|+2.571|+0.000|
|route_before_high|+0.078|+0.020|
|route|+0.078|+0.020|

原100MHz/10ns SDC及PS属性约束保持，最终报告清除内部优化预算；没有新增false-path、multicycle或放宽周期。TD明确16线程，实际读回5次。参考DR1M90GEG400/speed2，实际速度等级未核验。STA覆盖99.97%；默认不确定性保留。

最终首条最差setup路径（完整路径和cell/net延迟见同目录reports/route.timing）：

```text
Max Paths
----------------------------------------------------------------------------------------------------
Slack               : 0.078ns
Begin Point         : control/core/fabric/dma_core/motion/interlocks$monitor/round_valid_reg_syn_73.clk (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })
End Point           : a0_dir_syn_4.ce (rising edge triggered by clock board_100m  { rise@0.000000ns  fall@5.000000ns  period=10.000000 })
Check Type          : setup
Process             : slow
Budget              : 10.000ns { board_100m rising@10.000ns - board_100m rising@0.000ns }
Data Path Delay     : 9.674ns (cell 1.876ns (19%), net 7.798ns (81%))
Clock Skew          : 0.163ns
Logic Level         : 10 ( LUT4=4  LUT5=3  LUT3=2  LUT6=1 )
Max Fanout          : 96
Clock Uncertainty   : 0.085ns (sdc uncertainty: 0.000ns, default uncertainty: 0.085ns)
```

check_timing：invalid约束0类，组合环0类；其余dummy/no-input-delay/no-output-delay及未约束路径必须按reports/route.check逐项审查。SYN-5066仍存在=True，不得用后续“0 issue(s)”覆盖综合删除内部驱动的警告。独立route.drc文件生成=False；缺失时不宣称独立DRC文件清洁。

四路实际位置须在reports/route.area中读回V7/U9/U8/V11，九输出保持Y12/Y13/T9、U10/T5/U5、V6/W6/U7。外部上拉、实物电气/IO delay及速度等级等仍未资格确认；当前STA不解除这些门禁。2026-10-21用户已移除CDC/同步器独立门禁，相关检查和未验证项继续记录，不表示已通过。全网data/CE/reset/clock物理扇出审计未关闭，不据最差路径Max Fanout代表全网高扇出已解决。

## 保留的失败配置尝试

`hardware_profile0_rejected/`完整保留。该尝试将未批准生产PROFILE0接入顶层，工具因配置资格为常量删除部分运动逻辑和九路输出寄存器；虽然route为+1.282/+0.020ns，但只有Slice26402、ERAM57、DSP2、PAD FF0，GPIO最大延迟约束无效1类。它不构成完整功能系统的时序通过，不用于本候选比较或发布。最终已恢复原完整PROFILE2并重新独立完成全流程。

原rtl_path38的+0.032/+0.020ns、Slice36694/ERAM69/DSP6及其>1ns失败记录保持。离线bit/HPF/FSBL/BOOT/SD生成=True，没有上板或运动验收。用户本次免除>1ns生成条件，但无负STA要求与其余发布门禁保持；见BOOT_CANDIDATE.md。
