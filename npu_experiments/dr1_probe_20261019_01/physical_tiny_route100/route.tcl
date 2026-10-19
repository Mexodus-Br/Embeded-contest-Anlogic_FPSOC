cd {D:/Works/Embedded_contest/dev/npu_experiments/dr1_probe_20261019_01/physical_tiny_route100}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db {D:/Works/Embedded_contest/dev/npu_experiments/dr1_probe_20261019_01/physical_tiny_100m/place.db}
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "NPU_THREADS [get_param flow thread]"
get_num_thread
clear_user_sdc
read_sdc fixture.sdc
update_timing
report_timing_summary -file before_route.timing -path_num 1
route
update_timing -mode final
report_area -file route.area
report_timing_summary -file route.timing -path_num 5
report_route_status -file route.status
export_db route.db
puts "NPU_ROUTE_DONE"
exit
