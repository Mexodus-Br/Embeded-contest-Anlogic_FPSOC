cd D:/Works/Embedded_contest/dev/pl_rs485/optimization/path_dsp_verify_20261015
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/bsp/work/telemetry_soc_prj/gp_route.db
report_cells [get_cells {control/core/fabric/telemetry/cache/mult0_syn_167}] -connection -attributes
report_cells [get_cells {control/core/fabric/telemetry/cache/mult0_syn_260}] -connection -attributes
report_cells [get_cells {control/core/fabric/telemetry/cache/mult0_syn_168}] -connection -attributes
puts BASELINE_DSP_CONNECTIONS_VERIFIED
exit
