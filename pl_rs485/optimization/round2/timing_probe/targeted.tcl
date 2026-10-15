cd D:/Works/Embedded_contest/dev/pl_rs485/optimization/round2/timing_probe
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp_route.db
read_adc -file D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp/gp.adc
read_sdc D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp/gp.sdc
read_sdc D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp/ps-generated-properties.tcl
update_timing -mode final
foreach pattern {*missed* *scheduled_operand* *missed_operand* *aw_snapshot* *snap*} {
 set regs [get_regs -hier -quiet $pattern]
 puts "REG_PATTERN $pattern COUNT [llength $regs] FIRST [lrange $regs 0 7]"
}
report_timing_path -to [get_regs -hier -quiet *collector*missed*] -path_num 10 -file collector_missed.timing
report_timing_path -from [get_regs -hier -quiet *aw_snapshot*] -path_num 10 -file gp_snapshot_decode.timing
report_timing_summary -path_num 1 -file replay.timing
puts ROUND2_TARGETED_TIMING_COMPLETE
exit
