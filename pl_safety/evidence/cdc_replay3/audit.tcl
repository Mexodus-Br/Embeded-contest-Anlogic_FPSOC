cd D:/Works/Embedded_contest/dev/pl_safety/evidence/cdc_replay3
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/pl_safety/build/sealed_top1/route.db
read_adc -file D:/Works/Embedded_contest/dev/pl_safety/build/sealed_top1/gp/gp.adc
read_sdc D:/Works/Embedded_contest/dev/pl_safety/evidence/cdc_replay3/replay.sdc
read_sdc D:/Works/Embedded_contest/dev/pl_safety/build/sealed_top1/gp/ps-generated-properties.tcl
update_timing -mode final
set pads [get_ports {safety_limit_n[*] safety_estop_n}]
set all [get_regs -hier -quiet *inputs*]
set first {}
set second {}
foreach item $all {
 if {[string match {*control/core/fabric/dma_core/motion/inputs/meta*} $item]} {lappend first $item}
 if {[string match {*control/core/fabric/dma_core/motion/inputs/sync*} $item]} {lappend second $item}
}
foreach group [list $pads $first $second] {
 puts "CDC_SELECTION_COUNT [llength $group] $group"
 if {[llength $group]!=4} {error "Expected exactly four synchronizer pins"}
}
report_timing_path -from $first -to $second -path_num 10 -file synchronizer_internal.timing
check_timing -verbose -file replay.check
puts SAFETY_CDC_SELECTION_AUDIT_COMPLETE
exit
