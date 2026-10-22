# Build rtl_path38 result — 2026-10-21 Asia/Taipei

Candidate: rtl37_candidate_r5; complete actual safety/GPIO/RS485/dual-HP
system_wrapper; DR1M90GEG400/reference speed2, original10ns final constraints.
Finished11:30:30+08:00. Explicit16 threads read back. Main product remains29.

**No negative setup/hold slack, but special acceptance FAILED: setup must be
strictly>+1ns, actual+0.032ns. No production signoff.**

|Resource|36 before|38 after|Total|After used|Remaining|Delta|
|---|---:|---:|---:|---:|---:|---:|
|LUT6|26053|28905|52480|55.08%|23575|+2852|
|Slice|34263|36694|52480|69.92%|15786|+2431|
|Slice FF|37308|37478|104960|35.71%|67482|+170|
|PAD FF|9|9|n/a|n/a|n/a|+0|
|ERAM|69|69|280|24.64%|211|+0|
|DSP|6|6|240|2.50%|234|+0|
|IO|17|17|126|13.49%|109|+0|

Clock resources unchanged:GCLK1/32 (3.12%,31remaining), SCLK6/72
(8.33%,66remaining); PLL0/8; LCLK0/20; MLCLK0/8; IOCLK0/16.
Slice increased2431 (4.63percentage points); slice FF+170. No ERAM/DSP cost.
Original candidate21 Slice37039 ->36694 (345fewer); do not substitute this
comparison for the regression against most recent36's34263.

|Stage|Setup ns|Hold ns|
|---|---:|---:|
|gate|-1.250|0.000|
|place, nominal|+2.363|0.000|
|route before HIGH, nominal|-0.147|+0.020|
|route after HIGH, nominal|+0.032|+0.020|

HIGH entered and ended, confirmed literal phys_opt -post_route -effort high
command. HIGH contributes+0.179ns on this same routed candidate, removes4
negative setup endpoints, area counts unchanged. Versus36 final setup improves
1.002ns and violations102 ->0. Final STA coverage99.97%; default clock
uncertainty remains enabled; source SDC/ADC/property files directly byte checked.
Existing1.25ns internal optimization budget is cleared before nominal reports.

Worst final: home_owner_q_reg_syn_11 -> a2_step_syn_4.ce, board_100m group,
10LUT levels, max path fanout48; data9.699ns = cell1.910 + net7.789ns,
clock skew0.209ns, default uncertainty0.060ns, WNS+0.032ns.
Cone still traverses ownership/qualification/monitoring/feedback expiry,
stop cofactor and STEP CE. A single middle net fo17 takes2.234ns between
x73y24 andx21y21. Path names can be shared/renamed logic: do not attribute
all logic to management or planner merely from synthesized instance labels.
Full data/CE/reset/clock fanout and CDC audit remains incomplete.

Gate actual connected async reset/set FFs:13301 ->13254, **net47 fewer**.
Source-level586 removed reset assignments are not586 mapped reset FFs.
GP regs1038 ->873 (-165); collector+1; motion service+68; kernel+37;
executor+4; planFIFO+8; net-47. Gate AL_MAP_SEQ counts35750 ->37006,
not interchangeable with routed slice FF counts. Evidence rtl36_async_r1 and
rtl38_async_r1, both explicit16thread audits, original DB bytes unchanged.
Combined rewrites increased physical ripple resources5595 ->7003 and DRAM
LUT16 ->456; per-change cause needs separate ablation builds. Do not claim
all arithmetic-to-logic transformations saved resources from source inspection.

Functional evidence:
- rtl37_suite_r3:375 original safety/stop-phase cases PASS.
- rtl37_safety_diff_r1:371 complete safety-service all-output cycle miters PASS
  versus preserved36. Candidate r4/r5 differs only explicit net declaration,
  verified by exact byte transformation; r5 fixes real Questa declaration error.
- rtl37_service_r2:66799-cycle service differential PASS.
- rtl37_control_r1:complete collector/GP differential PASS.
- rtl37_time_r2:65536 modulo-u64 timestamp oracle vectors PASS.
- rtl37_arithmetic_r1:262208 actual saturation function checks PASS.
- rtl37_gp_r2:32800-cycle GP frozen-read/capture/IRQ/reset oracle PASS;
  private cfg payload compared only while cfg_valid, original public assertions kept.
- rtl37_transport_r1:41330-cycle all-output transport differential, FIFO256 full
  simultaneous pop/push, single record, backpressure, CRC and60 subcycle resets PASS.
- interlock_regressions_rtl37_r1:33 original affected regressions PASS.
- rtl37_real_r2:three SERIAL real vendor-IP GP/dual-controller scenarios PASS:
  protection30112867, watchdog28558277, feedback timeout34335637 checks;
  each HP0read18/HP1write8, overlap18, accepted_overlap2. No vendor IP stubs.

Open:setup>1ns has NOT been achieved; slice and DRAM increase need review;
final CDC/all-net physical fanout audit not yet closed. check_timing reports
0invalid constraints/0combinational loops, retains2dummy-node categories,
5no-input-delay and2no-output-delay categories. report_route_status checker
ran and completed in run.log; TD did not create the requested route.drc file,
so no standalone DRC-file-clean assertion is made.
SYN-5066 protected S2MM-only multi-driver critical warning remains visible.
Electrical/input/real speed grade/external delays/BSP-DDR/board qualification
remain independent. No board, BSP, image or deployment operations performed.
No new RTL modification or build was started by this result-review turn.
Candidate not promoted; Git delivery still pending overall optimization closure.
