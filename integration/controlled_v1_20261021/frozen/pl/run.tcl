cd D:/Works/Embedded_contest/dev/pl_safety/build/rtl_path38
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project -single_run system.al
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread

elaborate -top system_wrapper
read_adc -file gp/gp.adc
clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl

set_param place hfn_opt_effort high
set_param place max_fanout 128
set_param place opt_timing high
set_param place logic_level_opt on
report_param -all -file effective_parameters.tcl
optimize_rtl
optimize_gate -maparea gate.area
report_timing_summary -file gate.timing -path_num 10
export_db gate.db
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread

read_sdc place_budget.sdc
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place_budget.timing -path_num 10
clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl

update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 10
export_db place.db
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread

clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl

read_sdc route_budget.sdc
route
update_timing -mode final
report_timing_summary -file route_budget.timing -path_num 10
clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl

update_timing -mode final
report_timing_summary -file route_before_physopt.timing -path_num 20
report_area -io_info -file route_before_physopt.area
export_db route_before_physopt.db
set_param flow thread 16
if {[get_param flow thread]!=16} {error "Expected sixteen threads"}
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread
puts RTL_POST_ROUTE_HIGH_BEGIN
phys_opt -post_route -effort high
puts RTL_POST_ROUTE_HIGH_END
set_param flow thread 16
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread
clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
export_sdc -file nominal_route.sdc
update_timing -mode final
report_timing_summary -file route.timing -path_num 10
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
export_db route.db
puts INTERLOCK_FULL_TOP_COMPLETE
exit
