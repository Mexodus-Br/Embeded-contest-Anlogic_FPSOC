# Telemetry development failures and corrections

2026-10-14. No failure is counted as passing evidence; existing deliveries and
their result JSON are preserved. New build logs are under pl_dma/build until
archived by the telemetry delivery freezer; unit logs are in this directory.

- Initial Icarus compile: a generated hexadecimal macro immediately followed by
  `?` was lexed as a wildcard digit. Added token whitespace; compile passed.
- Opt-in wiring generator first compile: trailing comma copied from HP port
  list created an empty ANSI port. Removed the comma in the generator; original
  generators/tops unchanged. telemetry_ip_r1 compile log retained.
- telemetry_system_r1 compile: Questa rejects references before declarations;
  moved new observation assignments after wire declarations and the original
  rate function include after BIT_CYCLES declaration. Equations/state behavior
  unchanged. Old collector regression rerun, no vendor code changed.
- telemetry_unit_r1: encoder raw low enum byte is zero for payload ffffffff8000;
  corrected test's packed VALUE/ENUM expected word to00008000. No parser fix.
  Same-edge cancel/recover now suppresses new telemetry admission so all dropped
  events are accounted; successful packet completion has its own IRQ pulse.
- telemetry_system_r2: initial request start includes the collector's10ms
  minimum start gap, so first10ms flush notification can occur after20ms. Test
  bounded polling extended to40ms; status mask explicitly converted to bool
  before calling the one-bit check task.
- telemetry_system_r3: test held HP1 indefinitely stalled while expecting DMA
  reset to complete. Recovery cannot prove DDR quiescent under that condition.
  Test now releases backpressure during reset wait, drains accepted traffic,
  then explicitly recovers. r4 passed23044562 checks; original motion STEP/DIR/EN
  compared every cycle,32 motion points completed,288 HP0 read beats,16 HP1 write
  beats,3 actual UART completion events. This is not a hard-PS quiescence proof.
- TD cache_r1: unexpectedly tiny140 LUT6/296regs revealed the frontend inferred
  a RAM from the multiword snapshot array and optimized its updates away. Not
  accepted as functional timing evidence. Replaced snapshot storage with a
  packed parallel register vector; RTL selfcheck passed again. cache_packed and
  telemetry_soc_packed are the corrected implementations. telemetry_soc_r1 was
  explicitly stopped (exact command/PID identified) once invalidated; partial
  log retained. No clock relaxation or false-path masking used.
- telemetry_regression_r1: original GP real-IP test failed license checkout
  because the end-to-end Questa session held the single-session nodelocked
  license. Ran regressions again after that session completed; r1 logs retained.

Real S2MM-only probe ip_r2 passed2251 checks: exact64/1024/192B pass; BTT1024
with64B TLAST reports actual64/IOC; BTT64 with128B packet reports status
00004012, actual64; missing TLAST (BTT128,64B sent) remains incomplete in the
bounded observation. Production remains exact BTT, no simple residue inference.

- Final review: an unacknowledged packet aborted by primary reset must be counted even if all stream beats were already accepted. Added an in-flight result marker; reset counts it as failed/aborted once. Explicit failed completion is accepted in any armed phase without retracting VALID; contradictory completion results for the same ID are rejected. This affects statistics and cancellation only.
- dma_multirate_release: every bench passed, but the manifest guard exited1 because a telemetry test source changed during the run. Preserve those logs; rerun after source stabilization as dma_multirate_final.

- Final source runs: telemetry_unit_final87checks/17frames, telem_results_final104checks, telem_parse_final66vectors, software17frames/1088corruptions; final real system23044562checks; old GP/legacy/multirate and15 affected regressions pass.
- The final S2MM-only protected vendor implementation emits SYN-5066 (disconnect multi-driven internal net vyjqtk/rucwti), both isolated DMA and actual PS builds. Real-IP functional tests do not close synthesis equivalence. Keep this critical diagnostic open for vendor/BSP review; no protected-IP edits or silent enablement of MM2S. DMA scan fixture also emits PHY-5060 mixed clock/data fanout. Unassigned OOC IO and missing IO delays remain fixture limitations.

- Whole PS/HP0/HP1 build final: original driver timed out after1200s during physical placement, after emitting gate.db. Preserve initial_attempt.log. Resume the unchanged staged source/checkpoint with3600s timeout; no clock relaxation or functional change. physical.tcl/log and final combined run.log retained.

- Final physical completion: gate-1.368/0ns, place+1.708/0ns, route+0.018/+0.020ns at100MHz. Full source/constraint/PS/IP/evidence compatibility freeze passes. Reference route has no setup/hold violating endpoints, but only18ps setup margin and SYN-5066 remains open: timing_pass=true, diagnostics_closed=false, signoff_pass=false. Not board acceptance.
- New profile IRQ directed test telem_irq_final passes105checks including persistent READY and W1C/set races. Python zlib independently agrees on all17 actual RTL CRCs.
