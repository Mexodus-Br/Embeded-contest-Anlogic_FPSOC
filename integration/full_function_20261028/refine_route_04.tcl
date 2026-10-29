cd D:/Works/Embedded_contest/dev/integration/full_function_20261028/artifacts/route-lowbudget
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/integration/full_function_20261028/hardware/route.db
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "FULL_FUNCTION_REFINE_THREADS [get_param flow thread]"
get_num_thread
clear_user_sdc
read_sdc ../../hardware/gp/gp.sdc
read_sdc ../../hardware/gp/ps-generated-properties.tcl
read_sdc ../../route_budget_021.sdc
update_timing -mode final
report_timing_summary -file refined4_budget_before.timing -path_num 2
phys_opt -post_route -effort high
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
clear_user_sdc
read_sdc ../../hardware/gp/gp.sdc
read_sdc ../../hardware/gp/ps-generated-properties.tcl
update_timing -mode final
report_timing_summary -file refined4.timing -path_num 20
report_area -io_info -file refined4.area
check_timing -verbose -file refined4.check
report_route_status -drc -file refined4.drc
export_db refined4.db
puts FULL_FUNCTION_REFINED4_COMPLETE
exit
