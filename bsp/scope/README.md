# XYZ → Golden IK → MOT2 → GPIO scope test

This is an explicitly started, no-motor test. It uses the original firmware reference configuration and unchanged Golden algorithm, with logical axes A0..A2. It does not establish mechanical calibration, HOME, driver timing, or a Cartesian straight-line interpolator. Each `move` submits one coordinated joint endpoint with END; all records are buffered before START.

Fixed PL source: `df17b4ebd6e358d6626a227b5c0c152c1f6cb9ed`; GPIO handoff seal: `1ae5ce1218e06ab8d2a9674d6fa760a1d98529a9`. See `pl_motion/GPIO_HANDOFF.md` and `GPIO_RELEASE.json`. `verify_input.py` checks frozen source, evidence, vendor IP, generated definitions and Golden baseline without modifying them.

Build order: `prepare_project.py`, the existing `regenerate_motion_ps.py --work-dir scope_soc_prj --hp0`, `integrate_hardware.py`, `build_hardware.py`, PS HPF export, `audit_hardware.py`. Use a separate VM directory `$HOME/embedded-bsp-scope` and the existing vendor SDK/toolchain. Run `build_arm.sh` then `package_vm.sh`. Build logs are separate from the release hash manifest. Preserve the previous SD image for rollback. `vm.py --host IP` uses SSH/SFTP and prompts for an in-memory password.

Golden compilation is C++17, `-O0 -fno-fast-math -ffp-contract=off`, float32/double64, Linaro GCC 7.5. `delta-model` and the independent firmware oracle run all 1272 existing vectors on ARM. Capture their JSON using `board_scope_model.sh`, then use `extract_model_capture.py` and `model_vectors.py --results DIRECTORY`. Integer targets and persisted floating outputs are compared exactly; differences fail the gate and require diagnosis, without a baseline or tolerance change. The native/ARM `scope-unit` additionally exercises the application's exact parsing and codec functions without opening a device.

After cold boot and identity/model gates, `board_scope_ready.sh ROOT_PARTUUID` loads the controlled client and explicitly starts `delta-scope serve --no-motor-test`. It does not enable or start motion. Wait for human measurement authorization before using:

```sh
delta-scope init --xyz 0 0 -140
delta-scope move --xyz 5 0 -140 --duration-ms 500
delta-scope move --xyz 0 0 -140 --duration-ms 500
delta-scope stop
delta-scope snapshot
delta-scope shutdown
rmmod bsp_motion
```

`init` requires disabled, stationary, empty state before maintenance REBASE, then explicitly enables A0..A2. It is not HOME. `move` retains actual STEP position, recovers the DMA link, opens a new session, and submits one 72-byte little-endian MOT2 record (mask 7, M4 target 0, sequence 0, END). The kernel owns DMA allocation, ARM and transfer. The program checks capacity, complete packet/record acceptance and START_READY before START, then waits for session END and checks positions and pulse deltas. IOC is not motion completion. A separate STOP/snapshot path does not wait on the motion writer lock; cancellation prevents an old request from restarting.

| Vector | A0..A2 absolute steps | Expected pulse increment | DIR |
|---|---|---|---|
| Origin XYZ (0,0,-140) mm | -1090,-1090,-1090 | REBASE only | — |
| Endpoint XYZ (5,0,-140) mm, 500 ms | -1089,-966,-1213 | 1,124,123 | positive,positive,negative |
| Return, 500 ms | -1090,-1090,-1090 | 1,124,123 | negative,negative,positive |

Run invalid-input checks at the origin, before outbound motion. The 1 ms rejection test needs the nonzero endpoint delta. After in-flight STOP, a fresh move may return from the retained partial position; do not REBASE it away. A failed STOP/quarantine must retain the buffer and block further use. Explicit shutdown stops, disables, and releases; unload the client only after successful release. Keep raw serial command logs, server log, and final module/buffer state.

GPIO: A0 STEP/DIR/EN J12-3/4/5; A1 6/7/8; A2 9/10/11. Ground J12-2; J12-1 is power. Use the confirmed no-driver/no-motor wiring and 10× high-impedance probes. M4 is disabled and has no pad. Scope parameters are 100 MHz, 5 µs STEP high/low and DIR/EN guards, maximum 100 kHz, active-high EN. They are not driver/product parameters. Reset/disabled STEP=0, EN=0; reset DIR=1. END and safe STOP retain EN until explicit DISABLE.

For a two-channel instrument, repeat the same outbound vector after returning to origin, measuring A0/A1 STEP and A0/A2 STEP separately. Trigger on STEP rising, capture the full 500 ms interval with sufficient memory and sampling to count all 5 µs pulses, and take a separate high-resolution pulse-width capture. Measure DIR/EN with a STEP reference in additional repetitions. Record actual sampling, probes, trigger, pulse counts, polarity, widths, common-slot edge deviation, END and STOP evidence. Software and simulated counts do not prove physical waveform properties; unavailable instrument evidence remains unverified.

The full GPIO BSP build has route setup +0.031 ns / hold +0.021 ns at 100 MHz under reference speed2. Real device speed is unconfirmed. The nine outputs have LVCMOS33, 8 mA/SLOW and 20 ns asynchronous scope output budgets, not synchronous receiver timing signoff. Retained vendor ERAM reset/planner OFB diagnostics and SLATR-1036/1038 notes are in the evidence. No board deployment or measurement is implied by build success.
