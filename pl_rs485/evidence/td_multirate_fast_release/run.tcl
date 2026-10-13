cd {D:/Works/Embedded_contest/dev/pl_rs485/build/td_multirate_fast_release}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
analyze -file {D:/Works/Embedded_contest/dev/pl_rs485/build/td_multirate_fast_release/div_u64_u32.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_rs485/build/td_multirate_fast_release/record_fifo.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_rs485/build/td_multirate_fast_release/rs485_master.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_rs485/build/td_multirate_fast_release/rs485_multirate.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_rs485/build/td_multirate_fast_release/rs485_transaction.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_rs485/build/td_multirate_fast_release/uart_rx.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_rs485/build/td_multirate_fast_release/uart_tx.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_rs485/build/td_multirate_fast_release/probe.v}
elaborate -top td_probe
optimize_rtl
read_sdc clock.sdc
report_area -file rtl.area
optimize_gate -maparea gate.area
read_sdc clock.sdc
update_timing
report_timing_summary -file gate.timing -path_num 3
export_db gate.db
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 3
report_area -io_info -file place.area
export_db place.db
route
update_timing -mode final
report_timing_summary -file route.timing -path_num 3
report_area -io_info -file route.area
check_timing -verbose -file check.timing
report_route_status -drc -file route.drc
export_db route.db
puts RS485_TD_COMPLETE
exit
