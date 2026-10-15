cd D:/Works/Embedded_contest/dev/pl_rs485/optimization/round2/timing_probe
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r2main/gp_route.db
report_cells -dsp -mode final -file round2_dsp.rpt
report_cells [get_cells {control/core/fabric/rs485/regs/snapshot_reg[14841]_syn_2}] -connection -attributes
report_cells [get_cells {control/core/fabric/rs485/collector/missed_operand_reg[11]_syn_2}] -connection -attributes
puts ROUND2_DSP_PACKING_COMPLETE
exit
