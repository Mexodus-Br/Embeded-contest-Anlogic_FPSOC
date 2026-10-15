cd D:/Works/Embedded_contest/dev/pl_rs485/optimization/round2/timing_probe
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp_route.db
read_adc -file D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp/gp.adc
read_sdc D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp/gp.sdc
read_sdc D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp/ps-generated-properties.tcl
update_timing -mode final
report_timing_path -to [get_regs -hier -quiet *rs485/regs/snapshot*] -path_num 10 -file gp_snapshot_capture.timing
report_timing_path -to [get_regs -hier -quiet *missed_operand*] -path_num 10 -file collector_prefetch.timing
report_timing_path -to [get_regs -hier -quiet *scheduled*] -path_num 10 -file collector_scheduled.timing
puts ROUND2_TARGETED_CAPTURE_COMPLETE
exit
