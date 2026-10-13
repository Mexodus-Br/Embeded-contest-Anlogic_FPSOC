cd D:/Works/Embedded_contest/dev/bsp/work/motion_soc_prj
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project system.al
import_db gp_place.db
read_adc -file gp/gp.adc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
route
update_timing -mode final
report_timing_summary -file gp_route.timing -path_num 5
report_area -io_info -file gp_route.area
check_timing -verbose -file gp_route.check
report_route_status -drc -file gp_route.drc
all_clocks -verbose
export_db gp_route.db
bitgen -bit system.bit
puts BSP_MOTION_BOARD_BITSTREAM_COMPLETE
exit
