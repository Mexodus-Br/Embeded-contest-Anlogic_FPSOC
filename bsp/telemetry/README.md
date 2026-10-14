# Actual BSP GPIO + independent HP1 telemetry integration

Baseline branch `codex/rs485-telemetry-hp1`, source `f447116`; scope GPIO source `df17b4e`, seal `1ae5ce1`, accepted scope BSP `db5f75c`. Motion/GPIO/Golden and frozen RS485 contracts stay read-only. This candidate is blocked from deployment by `IP_DIAGNOSTIC.md`; it does not replace the approved scope SD image.

The one actual `system_wrapper` under `bsp/work/telemetry_soc_prj/system/hdl/` instantiates the regenerated vendor PS and `pl_dma/rtl/rs485_gp_ps_top.v`. It retains nine real STEP/DIR/EN pins, not separate test pulses, and uses the explicit public signals through the existing motion chain. Scope 500-cycle guards / 100kHz / raw64 / prepared8 / START32 apply to A0..A2; M4 parameters0 and no pin. RS485 uses the user-confirmed hardware manual TX L17 / RX N16 / DE+RE_N N15, J11 GND4/A5/B6. Slave addresses/models and full electrical topology remain unconfirmed; reference E0..E2 is not an actual-device acceptance.

Six full A33 windows, each4KiB: probe80400000/SPI82; motion DMA80500000/SPI83/84→HP0; motion80600000/SPI85; collector80700000/SPI86; cache/transport80800000/SPI87; independent S2MM-only80900000/SPI88→HP1. All level-high; original write/read response ownership and shared64bit/1MHz time source preserved. No duplicate parallel slaves or common reset used for local telemetry recovery.

Reproduce from dev with Python3.10/native TD:

```powershell
python bsp/telemetry/verify_input.py
python bsp/telemetry/prepare_project.py
python bsp/telemetry/regenerate_ps.py --hp0
python bsp/telemetry/integrate_hardware.py
python bsp/telemetry/audit_ps.py
python bsp/telemetry/build_hardware.py --dma
# A retained unchanged checkpoint can continue after a host timeout:
python bsp/telemetry/build_hardware.py --dma --resume-gate
python bsp/telemetry/audit_hardware.py
python bsp/telemetry/generate_kernel.py --check
python bsp/telemetry/generate_dts.py
python bsp/telemetry/test_router.py
python bsp/telemetry/test_provider.py --tag NEW_TAG
```

Use new isolated work/tag/evidence directories on later runs; never overwrite history. The existing project preparation intentionally refuses an existing directory. The hardware script has no bitgen. `regenerate_ps.py --export-hpf` requires a successful final review. The nine prior asynchronous scope output budgets remain; no new multicycle/false-path or relaxed100MHz constraint is introduced. RS485 missing external delay qualification is reported rather than guessed.

Run real IP tests serially with fresh tags: `pl_dma/tests/run_telemetry.py`, `run_telemetry_system.py`; then `run_regressions.py` / `run_remaining.py` cover parser/cache/FIFO/IRQ/C decoder, RS485/GP/multirate and the original motion/GP/DMA/Golden tests. The latter resumes after the original180s host timeout with the same vectors/markers and900s host allowance. Raw failures remain. Sealed earlier evidence/JSON is restored byte-for-byte. `verify_input.py` proves596 old schema leaf values unchanged and migrates the new whole schema/definition identities instead of bypassing them.

Linux compilation uses isolated `$HOME/embedded-bsp-integrated`, original matching `embedded-bsp/output/kernel`, Linaro7.5 and the unchanged81f7… kernel config. Upload source under bsp/telemetry, required bsp/motion headers/client, and pl_rs485/software/generated; run `build_software.sh`. Run `build_preview_dts.sh` only for the disabled new-node preview; its scope HPF clock/storage header is explicitly not a replacement for final matched HPF. `audit_dtb.py` walks actual address/size cells, ancestor ranges and inherited interrupt-parent, auditing windows and GIC collisions. Final boot release must regenerate this header from qualified new HPF.

The provider is an independent copy preserving the old motion API and behavior. Its new DT policy admits only one S2MM child at80900000. It latches S2MM_LENGTH + DMASR + cookie in the IRQ before W1C, callback or next programming; holds new simple RX until retire, and never infers length from residue0. Error logging avoids forbidden SG registers. Normal IOC does not trigger STOP; telemetry reset addresses only the new instance. Module/ABI compatibility is compiled with the original motion client.

`bsp_rs485` is a root-only, single open owner of collector/cache GP and its private RX. Typed ioctls provide configuration/application metadata, atomic cache snapshots, original complete diagnostic capture/consume, precise RX, COMPLETE, cancel/recover and release. No mmap/arbitrary offset/physical-address API. Coherent buffer1024 uses the controller's DMA API/mask32/address alignment8. RX issues exactN×64 before ARM, checks callback/latched status/actual length, packet/gen, CRC and canonical raw decoder. User receives bytes, preserves them, then COMPLETE retires ownership. Configuration output includes generation/revision/apply sequence/time; preserve mappings instead of re-labeling older rows. A single mutex covers diagnostic capture→read→copy→consume; snapshot IDs and whole row reads have their own mutex. CANCEL is independent of the RX wait, invalidates64bit software epoch, and cannot restart old callbacks. Failed/unqualified in-flight cancellation retains the buffer and pins the module.

The ARM `rs485-accept` modes are explicit: `idle`, `diagnostic-timeouts`, `cancel`, `release`. Diagnostic mode can send UART queries; it is not permitted as an implicit startup action or a valid-feedback claim. It preserves binary packets and a configuration ledger under/tmp before COMPLETE, requires at least one RX packet, and requires exporting those files before power-off. Unknown historical/default configuration mappings stay unknown. GPIO execution remains entirely user controlled by `bsp/scope/SCOPE_MANUAL.md`; this utility has no motion enable/start/rebase/stop operation.

Deployment, cold boot, IRQ runtime, independent RX/CRC/length, cancel/recovery/drain, real RS485 and concurrent HP0 supply/HP1 pressure are all gated. Do not load prototype modules into an old or mismatched bitstream. When gates close, generate matched HPF/FSBL/BOOT/DTB/rootfs, recheck card model/capacity/UniqueId/serial/non-system scope, full write/readback, and ask the user to release COM4 before capturing manual cold boot. No eMMC/QSPI writes and no automatic reset. Current task has not opened COM4 or launched any physical DMA; the user's board state has not been taken over.
