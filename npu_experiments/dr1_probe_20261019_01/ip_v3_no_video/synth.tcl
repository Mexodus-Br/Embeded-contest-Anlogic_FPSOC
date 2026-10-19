cd {D:/Works/Embedded_contest/dev/npu_experiments/dr1_probe_20261019_01/ip_v3_no_video}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project -single_run probe.al
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "NPU_THREADS [get_param flow thread]"
get_num_thread
set_param flow syn_ip_flow off
if {[get_param flow syn_ip_flow] ne "off"} {error "Expected native synthesis flow"}
elaborate -top design_0_Video_NPU_0
read_adc -file boundary.adc
create_clock -name npu_data -period 10 [get_ports M_AXI_ACLK]
create_clock -name npu_config -period 10 [get_ports S_AXILite_ACLK]
report_param -all -file effective_parameters.tcl
optimize_rtl
export_db rtl.db
optimize_gate -maparea gate.area
legalize_phy_inst
report_area -file gate_full.area
report_timing_summary -file gate.timing -path_num 5
export_db gate.db
puts "NPU_SYNTH_DONE"
exit
