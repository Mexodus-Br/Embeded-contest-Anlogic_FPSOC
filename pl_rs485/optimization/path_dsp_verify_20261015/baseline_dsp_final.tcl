cd D:/Works/Embedded_contest/dev/pl_rs485/optimization/path_dsp_verify_20261015
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/bsp/work/telemetry_soc_prj/gp_route.db
report_cells -dsp -mode final -file baseline_dsp.rpt
puts BASELINE_DSP_VERIFIED
exit

