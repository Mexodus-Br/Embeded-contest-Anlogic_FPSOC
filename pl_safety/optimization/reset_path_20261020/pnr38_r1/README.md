# RTL37r5 full actual top build rtl_path38

2026-10-21 user requested: once build starts, provide query script and end turn.
Isolated candidate rtl37_candidate_r5; main product RTL still29. Task
Codex-PL38-PnR-20261021-R1 is a one-shot hidden normal-user worker, zero triggers.
Confirmed10:42:08+08:00: worker9108, builder2512, TD12824; task state4,
16threads readback true; complete synthesis/place/route, currently synthesis.

Original device/speed2/10ns/GPIO/dualHP retained. Post-route command is explicitly
phys_opt -post_route -effort high, with original SDC before/after. It has not yet
entered HIGH during synthesis. Before/after physical optimization reports remain
separate. Flow completion is not target or release approval; final setup>1ns,
hold>=0 remain mandatory. No deployment/BSP/board/bitgen or protected IP edits.

RTL changes:1 atomic active-query qualification bit;586 private GP source payload
bits no longer asynchronously reset (mapped count still pending); timestamp
subtraction sign -> XOR/63bit borrow;65bit saturating add ->33bit + high-bit OR;
separate sole STEP-register process fed by local original-cycle stop cofactor,
existing high pulse drain retained. Original state/receive/management behavior
still exact. No externally added cycles.

Validation:375 original safety cases PASS (rtl37_suite_r3), service66799cycle
miter PASS (rtl37_service_r2), time65536vectors PASS, sat262208vectors PASS,
GP32800cycle oracle PASS, transport41330cycle/fullFIFO/CRC/reset PASS,
control complete collector/GP differential PASS rtl37_control_r1.
All-output safety-service cycle miter and33original regressions still running;
real-IP three serial scenarios rtl37_real_r2 currently protection running.
No final functional signoff; do not mix candidate29 real-IP evidence with37.

Failures preserved:37prepare_r1 ambiguous replacement;37r2/r3 direct stop cofactor
incorrectly treated HOME enable as stop (legacy recovery test9). Fixed r4 and
all375 passed. r1GP test qualifier typo compile failure fixed without relaxed
valid-data assertions. Actual Questa r1 detected an implicit wire followed by
initialized net redeclaration in inherited continuous_motion. r5 only moves that
same scalar net declaration before first use and converts initializer to assign;
exact byte transformation verified in declaration_compatibility.json and builder.
Real-IP r2 compiled and started. No source modifications after these snapshots.

Query PowerShell:
& 'D:\Works\Embedded_contest\dev\pl_safety\optimization\reset_path_20261020\pnr38_r1\status.ps1' -Watch
Ctrl+C ends query only. Logs/reports:pl_safety/build/rtl_path38. Worker result/state
beside this README. Prior gate-only rtl_path37 uses37r4, native exec session90976,
TD23572, and is independent evidence, not the current complete build.
Native ongoing sessions: safety diff23936;33regressions44878; real-IP83777.
No Git commit yet. Preserve owner changes and all old failure/evidence directories.
