# S2MM-only protected IP diagnostic — release blocked

The installed TD 2026.1 SP2 AXI DMA protected source is unchanged. No encrypted body was edited, decrypted, or suppressed. The production frozen instance still has `AL_INCLUDE_MM2S=0`, `AL_INCLUDE_S2MM=1`, simple/SG0/Micro0, 32-bit addresses, 64-bit memory/stream, burst16, DRE/SF1, BTT16, ASYNC0, 100MHz. The parameter list and exact vendor hashes are in `pl_rs485/evidence/identity_telemetry.json` and the final BSP connections report.

The actual complete BSP GPIO top reproduces:

```text
SYN-5066 CRITICAL-WARNING: Disconnect the driver 'control/core/fabric/telemetry_dma/dma/vyjqtk/rucwti_i1' of the multi-driven net 'control/core/fabric/telemetry_dma/dma/vyjqtk/rucwti'
```

The same protected hierarchy is reported in `pl_dma/reports/telem_dma_r1/run.log` (`dut/dma/vyjqtk/...`) and `pl_dma/reports/telemetry_soc_final/run.log` (`pl/core/fabric/telemetry_dma/dma/vyjqtk/...`). It is inside the independent new DMA instance, not the GPIO output assignment or the six-way GP response mux. Prior scope bidirectional DMA did not report this diagnostic. That correlation does not prove which internal function the opaque net implements or that disconnecting one driver is harmless.

The real vendor RTL model passed 2251 checks (64/1024/192B, short IOC length64 for requested1024, oversize error 0x4012, missing TLAST not completing) and the two-controller system differential test passed 23044562 checks, 32 motion points, HP0 read288/HP1 write16, no STEP/DIR/EN difference during telemetry cancel/reset. These support RTL behavior but do **not** establish synthesis equivalence after the driver removal. A later tool stage's “0 critical issues” summary cannot erase the earlier raw SYN-5066.

Disposition: `diagnostics_closed=false`, `signoff_pass=false`; no bitgen, matching HPF/FSBL/BOOT or SD candidate release. Continue resources, STA, software and simulation only. UART external IO timing and real device speed remain separate qualification items.

Review package for the vendor/user consists of the fixed source/parameter/IP hashes, complete actual BSP wrapper and original PS properties, GPIO/RS485 ADC, unchanged 10ns SDC, initial and resumed logs, gate/place/route reports, and same-IP functional test logs. No message has been sent to a vendor.

Required resolution is one of:

1. Vendor-supported explanation identifying both internal drivers and their intended behavior for this exact parameter combination, with a documented synthesis equivalence/qualified tool result that closes the diagnostic.
2. Official corrected protected IP/tool release; record a new approved vendor identity, rerun all affected checks and final whole-top P&R before release.
3. If S2MM-only is unsupported, propose an explicit architecture/profile migration for user review. A separate bidirectional instance with unused MM2S would be such a change; it has **not** been built as the production workaround or substituted here.

Driver recovery also needs a qualified guarantee that an interrupted RX reset/HALTED state implies all HP1/DDR writes are quiescent, together with drained IRQ/tasklets/callbacks/descriptors. Hardware `hp_idle` alone and a 10ms stable interval are insufficient. The owner defaults to retaining/quarantining an interrupted RX buffer without `bsp,validated-hp1-reset-drain`; the disabled DT preview deliberately omits that property. It must not be added merely to bypass a failed recovery. Normal successful IOC + captured error-free exact length is handled separately. On-board interrupted RX qualification remains NOT_EXECUTED.
