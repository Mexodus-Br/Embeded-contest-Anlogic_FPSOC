cd D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r1
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project system.al
elaborate -top system_wrapper
read_adc -file gp/gp.adc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
optimize_rtl
optimize_gate -maparea gp_gate.area
report_timing_summary -file gp_gate.timing -path_num 5
export_db gp_gate.db
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file gp_place.timing -path_num 5
export_db gp_place.db
route
update_timing -mode final
report_timing_summary -file gp_route.timing -path_num 5
report_area -io_info -file gp_route.area
check_timing -verbose -file gp_route.check
report_route_status -drc -file gp_route.drc
export_db gp_route.db
puts BSP_TELEMETRY_RESOURCE_BUILD_COMPLETE
exit
