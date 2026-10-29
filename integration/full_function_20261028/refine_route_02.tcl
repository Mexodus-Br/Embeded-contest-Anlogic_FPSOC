cd D:/Works/Embedded_contest/dev/integration/full_function_20261028/hardware
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db route.db
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "FULL_FUNCTION_REFINE_THREADS [get_param flow thread]"
get_num_thread
clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
# Optimization target only. Final reports use the unchanged nominal constraints.
set_clock_uncertainty -setup 0.30 [get_clocks board_100m]
phys_opt -post_route -effort high
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
update_timing -mode final
report_timing_summary -file refined2.timing -path_num 20
report_area -io_info -file refined2.area
check_timing -verbose -file refined2.check
report_route_status -drc -file refined2.drc
export_db refined2.db
puts FULL_FUNCTION_REFINED2_COMPLETE
exit
