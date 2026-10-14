cd {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/ip/axi_dma.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/ip/axi_protocol_converter_merge.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/axi_lite_six_way.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/axi_lite_three_way.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/axi_lite_two_way.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/axis_loop_fifo.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/dma_gp_full_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/dma_gp_ps_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/dma_lite_guard.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/dma_loopback_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/dma_shared_lite_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/motion_dma_lite_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/motion_gp_full_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/motion_gp_ps_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/motion_shared_lite_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_gp_full_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_gp_ps_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_probe_time_regs.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_shared_lite_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/telemetry_dma_guard.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/telemetry_dma_lite_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/axis_motion.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/continuous_motion.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/four_axis_motion.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/gp_control_regs.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/gp_control_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/gp_ps_control_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/gp_ps_write_adapter.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/motion_executor.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/motion_fifo.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/motion_planner.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/motion_service.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/motion_stream_rx.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/div_u64_u32.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/record_fifo.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_gp_bridge.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_gp_regs.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_latest_cache.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_light_parse.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_master.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_multirate.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_telem_regs.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_telem_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_telemetry.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/rs485_transaction.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/uart_rx.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/uart_tx.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/ps_telemetry_candidate/RTL/ARM_Processor_System_f6ddd1d59490.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/telemetry_soc_packed/top.v}
elaborate -top telemetry_soc_reference
optimize_rtl
read_adc clock.adc
read_sdc ps-properties.tcl
read_sdc clock.sdc
optimize_gate -maparea gate.area
update_timing
report_timing_summary -file gate.timing -path_num 3
export_db gate.db
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 3
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
