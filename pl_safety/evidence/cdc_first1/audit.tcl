cd D:/Works/Embedded_contest/dev/pl_safety/evidence/cdc_first1
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/pl_safety/build/sealed_top1/route.db
read_adc -file D:/Works/Embedded_contest/dev/pl_safety/build/sealed_top1/gp/gp.adc
read_sdc D:/Works/Embedded_contest/dev/pl_safety/build/sealed_top1/gp/gp.sdc
read_sdc D:/Works/Embedded_contest/dev/pl_safety/build/sealed_top1/gp/ps-generated-properties.tcl
update_timing -mode final
set pads [get_ports {safety_limit_n[*] safety_estop_n}]
set first [get_pins {control/core/fabric/dma_core/motion/inputs/meta_reg[*].d}]
set launch [get_pins {control/core/fabric/dma_core/motion/inputs/meta_reg[*].q}]
set second [get_pins {control/core/fabric/dma_core/motion/inputs/sync_reg[*].d}]
foreach group [list $pads $first $launch $second] {
 puts "CDC_SELECTION_COUNT [llength $group] $group"
 if {[llength $group]!=4} {error "Expected exactly four synchronizer pins"}
}
report_timing_path -from $launch -to $second -path_num 10 -file synchronizer_internal.timing
puts SAFETY_CDC_SELECTION_AUDIT_COMPLETE
exit
