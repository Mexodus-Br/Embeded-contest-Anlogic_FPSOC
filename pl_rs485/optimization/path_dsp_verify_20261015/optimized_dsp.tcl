cd D:/Works/Embedded_contest/dev/pl_rs485/optimization/path_dsp_verify_20261015
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/bsp/work/telemetry_opt_r1/gp_route.db
report_cells -dsp -file optimized_dsp.rpt
report_cells [get_cells {control/core/fabric/rs485/collector/sent_reg[387]_syn_3}] -connection -attributes
report_cells [get_cells {control/core/fabric/rs485/collector/missed_reg[296]_syn_2}] -connection -attributes
report_cells [get_cells {control/core/fabric/telemetry/cache/frozen_reg[7428]_syn_2}] -connection -attributes
puts OPTIMIZED_PATH_DSP_VERIFIED
exit
