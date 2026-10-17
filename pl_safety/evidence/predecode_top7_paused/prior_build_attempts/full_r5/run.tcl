cd D:/Works/Embedded_contest/dev/pl_safety/build/full_r5
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project system.al
elaborate -top system_wrapper
read_adc -file gp/gp.adc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
optimize_rtl
optimize_gate -maparea gate.area
report_timing_summary -file gate.timing -path_num 10
export_db gate.db
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 10
export_db place.db
route
update_timing -mode final
report_timing_summary -file route.timing -path_num 10
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
export_db route.db
puts SAFETY_RESOURCE_BUILD_COMPLETE
exit
