# Coordinate scope candidate — 2026-10-13

This record concerns the independent GPIO BSP candidate; prior internal-motion releases and rollback images are retained. No automatic enable or start is installed.

| Gate | Current status | Evidence |
|---|---|---|
| Frozen GPIO/Golden/schema/vendor-IP identity | PASS, read-only | `verify_input.py`; fixed source/seal in `integration.review.json` |
| Full PS+GP+HP+GPIO build, 100 MHz | PASS under reference speed2; actual speed unconfirmed | `../evidence/scope-hardware-20261013/`, `integration.review.json` |
| Route STA | setup +0.031 ns, hold +0.021 ns | Full routed reports, not prior internal-output signoff |
| ARM application/model/oracle compilation | PASS, Linaro GCC 7.5 | `../evidence/scope-build-20261013/arm-build.log` |
| Native and physical ARM application parser and codec | PASS, canonical Python byte-exact | `unit-host.log`, `codec-comparison.json`, ARM raw capture |
| Matched FSBL/BOOT/DTS/rootfs/image integrity | PASS | `image-verification.json`, `manifest.json`, `SHA256SUMS` |
| SD complete readback | PASS, all 536870912 bytes | `../evidence/scope-sd-windows-write-20261013-01.log` and JSON identity/readback |
| Final cold boot and identity gate | PASS | Full FSBL→U-Boot→Linux `scope-cold-20261013-02.log`; model and ready captures |
| ARM vector execution/comparison | PASS | 1272 cases, 826 valid / 446 invalid; exact host/oracle/model values, no differences |
| XYZ coordinate submission/PL dynamic execution | NOT EXECUTED by user request | User elected to operate all GPIO measurement; see SCOPE_MANUAL.md |
| Physical GPIO instrument evidence | NOT VERIFIED | Model/channel count unresolved; no captures yet |
| In-flight STOP | NOT EXECUTED by user request | No coordinate trajectory submitted in this task |
| Idle STOP/DISABLE/RELEASE/client unload | PASS | `scope-release-20261013-01.log`; both DMA channels HALTED, no buffer owner |

Final board state: accepted/active/done/END=0, all position/pulse counters=0, STEP0/EN0; no coordinate initialization or move occurred. The root-only test server exited; motion client unloaded and coherent buffer released. GP and DMA provider remain loaded with reference count 0. MM2S/S2MM IRQ counts 0, IRQ Err=0. All serial capture/command processes have exited and COM4 is closed. The user can open COM4 and follow `SCOPE_MANUAL.md`.

The first COM4 capture open was rejected by sandbox access; an authorized retry succeeded. The zero-byte failed-open log and metadata are retained, followed by the complete 19009-byte cold log. Its SHA256 is `50c83b9d4679d24bcf81185bd5f28bbfd4762d593076ec97ce103a27cd1cb364`. FSBL reports 1024MB/1333Mbps and GP reset0 release; Linux root matches `8aea5f8d-02`. Pure model, provider/client profile and all initial counters/configuration checks passed without GPIO ENABLE/START.

Fixed candidate image SHA256: `66d1b0cff5e56db5b8572eb879a3d9781e25c1028fa3168c2ec6142e6e3a6ff6`, root PARTUUID `8aea5f8d-02`. Matching HPF: `609639dec28432912e7bcbddee90328edbeaca1a1ee46193d657e8cffa79103b`; bitstream: `b597de9d2e453f47056e91b743c449bce79717aba6c0a79e7e4d84dcddbcda74`. ARM application: `99d43db6e924a4991a1bd6ab0711a806e61f10b092f2647535a017c0ac2a56b9`. Complete file/module hashes are in the evidence manifests.

## 2026-10-21 independent MOTOR3125 comparison image

The original scope release above remains unchanged. A separate scope-derived motor bench image uses STEP high/low minimum 3125 cycles (31.25us), DIR/EN guards500 cycles, maximum16kHz, and explicit `serve --motor-bench-test`. Full100MHz route is setup+0.087ns/hold+0.020ns under reference speed2, actual16 threads. Kernel self-check, real protected MM2S/GP simulation, ARM compilation, matched HPF/FSBL/BOOT/DTB/rootfs and full Windows file-image verification passed. See `../motor_test/BUILD_STATUS.md` and `README.md`; this excludes independent HP1/RS485/safety/HOME and does not qualify mechanical parameters.

Image: `bsp/artifacts/motor3125/sdcard.img`,536870912B; SHA256 `f9fbe564a5cec7662c2fd9267f5ce437db0d5f3097e6e41eef73f4ef573b17a3`; root PARTUUID`f330c1cf-02`. User confirmed SD absent and requested ending this round here. No physical SD write/readback, cold boot, ARM board execution, GPIO/motor/physical STOP validation performed. No COM4 access, board module loading or board DMA allocation by this task; existing board state was not taken over. HOLD ignores EN, so GPIO DISABLE is not a physical driver-disable guarantee. This image has not yet demonstrated a fix for the reported motor issue.

Subsequent user-authorized Windows deployment completed2026-10-21 22:16+08:00: currently enumerated USB card31299993600B matched the scope target identity, system NVMe excluded; first536870912B written and fully read back unbuffered with the exact image SHA256 above, partition/filesystem signatures and PARTUUID passed. Rollback scope image retained and verified. Writer exited0 with all handles closed. This supersedes only the SD NOT_EXECUTED state in the preceding historical paragraph; cold boot and physical motor/STOP checks remain NOT_EXECUTED. Evidence:`../evidence/motor3125-20261021/sd-write.log.json`.

Vendor baseline warnings are retained without modifying Golden. Remaining implementation diagnostics are vendor ERAM reset/planner mapped OFB and SLATR-1036/1038 notes. The nine scope GPIO outputs use 20 ns asynchronous budgets, not driver input synchronization signoff. Build/software observations do not establish physical pulse widths or mechanical performance.

The VM moved from 192.168.43.133 to the user-confirmed 192.168.43.134. Connection timeout at the old address preceded authentication; final build and download succeeded at the new address. Build logs remain outside the release manifest so rebuilding cannot silently invalidate release hashes by overwriting logs afterward.
