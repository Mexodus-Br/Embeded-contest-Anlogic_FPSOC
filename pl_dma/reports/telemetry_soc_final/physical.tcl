cd {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_final}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db gate.db
read_adc clock.adc
read_sdc ps-properties.tcl
read_sdc clock.sdc
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 3
export_db place.db
route
update_timing -mode final
report_timing_summary -file route.timing -path_num 3
report_area -file route.area
check_timing -verbose -file route.check
report_route_status -drc
all_clocks -verbose
export_db route.db
puts TELEMETRY_SOC_REFERENCE_COMPLETE
exit
