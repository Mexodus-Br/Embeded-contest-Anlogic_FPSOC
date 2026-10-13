cd {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/ip/axi_dma.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/ip/axi_protocol_converter_merge.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/axi_lite_three_way.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/axi_lite_two_way.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/axis_loop_fifo.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/dma_gp_full_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/dma_gp_ps_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/dma_lite_guard.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/dma_loopback_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/dma_shared_lite_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/motion_dma_lite_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/motion_gp_full_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/motion_gp_ps_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/motion_shared_lite_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/axis_motion.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/continuous_motion.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/four_axis_motion.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/gp_control_regs.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/gp_control_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/gp_ps_control_top.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/gp_ps_write_adapter.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/motion_executor.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/motion_fifo.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/motion_planner.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/motion_service.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/motion_stream_rx.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/ps/RTL/ARM_Processor_System_f6ddd1d59490.v}
analyze -file {D:/Works/Embedded_contest/dev/pl_dma/build/motion_soc_gpio_scope/top.v}
elaborate -top motion_soc_scope
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
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
all_clocks -verbose
export_db route.db
bitgen -bit scope-test.bit
puts MOTION_GPIO_SCOPE_COMPLETE
exit
