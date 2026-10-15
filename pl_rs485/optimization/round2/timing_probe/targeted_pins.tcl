cd D:/Works/Embedded_contest/dev/pl_rs485/optimization/round2/timing_probe
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp_route.db
read_adc -file D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp/gp.adc
read_sdc D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp/gp.sdc
read_sdc D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp/ps-generated-properties.tcl
update_timing -mode final
foreach pattern {*rs485/regs/snapshot* *missed_operand*} {
 set xs [get_regs -hier -quiet $pattern]
 puts "LOGICAL_SELECTION $pattern COUNT [llength $xs] FIRST [lrange $xs 0 4]"
}
foreach pattern {*rs485/regs/snapshot_reg* *missed_operand_reg*} {
 set xs [get_cells -hier -quiet -full_hier $pattern]
 puts "CELL_SELECTION $pattern COUNT [llength $xs] FIRST [lrange $xs 0 4]"
}
set capture [get_pins -hier -quiet -full_hier *rs485/regs/snapshot_reg*.ce*]
puts "CAPTURE_PIN_COUNT [llength $capture] FIRST [lrange $capture 0 4]"
if {[llength $capture]==0} {error "No GP snapshot capture pins"}
report_timing_path -to $capture -path_num 10 -file gp_snapshot_capture_pins.timing
set prefetch [get_pins -hier -quiet -full_hier *missed_operand_reg*.i*]
puts "PREFETCH_PIN_COUNT [llength $prefetch] FIRST [lrange $prefetch 0 4]"
if {[llength $prefetch]==0} {error "No collector prefetch data pins"}
report_timing_path -to $prefetch -path_num 10 -file collector_prefetch_pins.timing
puts ROUND2_TARGETED_PHYSICAL_PINS_COMPLETE
exit
