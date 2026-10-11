cd D:/Works/Embedded_contest/dev/bsp/work/soc_prj
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project system.al
elaborate -top system_wrapper
optimize_rtl
optimize_gate -maparea system_gate.area
legalize_phy_inst
place
route
update_timing -mode final
report_timing_summary -file system_pr.timing
report_area -io_info -file system_phy.area
export_db system_pr.db
bitgen -bit system.bit
puts BSP_BITSTREAM_COMPLETE
exit
