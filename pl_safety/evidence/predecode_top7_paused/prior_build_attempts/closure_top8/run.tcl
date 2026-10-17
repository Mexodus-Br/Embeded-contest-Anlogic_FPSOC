cd D:/Works/Embedded_contest/dev/pl_safety/build/closure_top8
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/pl_safety/build/predecode_top7/place.db
# threads=16; TD 6.2 uses the singular property name "thread".
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "SAFETY_TD_THREADS [get_param flow thread]"
get_num_thread

read_adc -file gp/gp.adc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
read_sdc closure_margin.sdc
route
update_timing -mode final
report_timing_summary -file route_closure_margin.timing -path_num 10
read_sdc restore_nominal.sdc
update_timing -mode final
report_timing_summary -file route.timing -path_num 10
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
export_db route.db
puts SAFETY_RESOURCE_BUILD_COMPLETE
exit
