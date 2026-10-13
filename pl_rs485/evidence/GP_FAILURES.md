# GP bridge failures and corrections

Every failed run is retained; failures are not counted as passing evidence.

- Initial standalone compile (2026-10-14): exit1, `rs485_gp_regs.v:57` undefined RS_QUERY_PROTECT macro. The unchanged wire generator emits query_code(), rather than Verilog query macros. Corrected to generated query_code(3'd4); next standalone compile exit0. These initial diagnostics were captured in the tool transcript; later runner logs persist command/exit/output on disk.
- `sim_gp_r1`: regs bench passed; e2e compile exit1 because copied serial slave checksum byte `k` conflicted with main loop integer `k`. Renamed checksum byte; no RTL change. `sim_gp_r2` both benches passed, seed20261014.

Additional revisions and final evidence are recorded below as runs occur. No board interaction or automatic retry is part of these runners.

- TD gp_r1 finished synthesis/place/route with positive setup/hold and RS485_TD_COMPLETE. Packaging exited1 because report_route_status -file did not create route.drc in this tool version (diagnostics are in run.log). Corrected packaging to the actual route.qor file; preserved all r1 reports. This is a packaging failure, not an RTL timing failure.

- sim_gp_stress_r1 exit1 at full exchange: reference scoreboard overwrote the full ring head before comparing same-edge pop. Corrected scoreboard to check old head before accepting new tail. RTL unchanged; both actions remain same edge.

- Final packaging/source freeze: shared pl_interface has LF attributes. Normalized new schema and generator to LF, regenerated all headers before final runs; earlier TD r1/release reports retained as intermediate evidence, final/final-fast bind the final byte identities. sim_gp_final and both legacy release suites pass; pressure producer seed derives from supplied seed, 209 attempted / 46 admitted+consumed / 163 dropped.
