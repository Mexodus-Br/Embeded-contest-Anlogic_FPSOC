cd D:/Works/Embedded_contest/dev/integration/full_function_20261028/artifacts/route-startbest7
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/integration/full_function_20261028/hardware/refined3.db
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "FULL_FUNCTION_REFINE_THREADS [get_param flow thread]"
get_num_thread
clear_user_sdc
read_sdc ../../hardware/gp/gp.sdc
read_sdc ../../hardware/gp/ps-generated-properties.tcl
read_sdc ../../route_budget_05.sdc
update_timing -mode final
report_timing_summary -file refined7_budget_before.timing -path_num 2
phys_opt -post_route -effort high
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
clear_user_sdc
read_sdc ../../hardware/gp/gp.sdc
read_sdc ../../hardware/gp/ps-generated-properties.tcl
update_timing -mode final
report_timing_summary -file refined7.timing -path_num 20
report_area -io_info -file refined7.area
check_timing -verbose -file refined7.check
report_route_status -drc -file refined7.drc
export_db refined7.db
puts FULL_FUNCTION_REFINED7_COMPLETE
exit
