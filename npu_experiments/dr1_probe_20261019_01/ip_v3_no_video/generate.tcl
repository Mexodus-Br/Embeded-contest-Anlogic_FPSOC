cd {D:/Works/Embedded_contest/dev/npu_experiments/dr1_probe_20261019_01/ip_v3_no_video}
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "NPU_THREADS [get_param flow thread]"
get_num_thread
proc set_param {args} {}
set DW_AVB_ADDR 32
set DW_AVB_DATA 64
set DW_AVB_STB 8
set DW_AVB_LEN 8
set DW_AVB_ID 4
set SOFT_NN 1
set NN_POOLING 0
set NN_ACTIVATE 0
set NN_UPSAMPLE 1
set NN_ROUTE 1
set NN_SHORTCUT 1
set SOFT_YOLO 0
set SOFT_CSC 0
set SOFT_RESIZE 0
set NPU_SOFT 1
set YOLOV3TINY 0
set YOLOV3 1
set YOLOV4 0
set YOLOV5S 0
set MBFace 0
set AXIS_ADDR_WD 33
set AXIS_DT_WD 32
set AXIS_DT_NB 4
set AXIS_BURSTP_WD 4
set AXIS_ID_WD 12
set AXIM_ADDR_WD 33
set AXIM_DT_WD 64
set AXIM_DT_NB 8
set AXIM_BURSTP_WD 4
set AXIM_ID_WD 6
set SOFT_HDMI_DISPLAY 0
set PRE_PROCESS 0
set POST_PROCESS 0
set YOLOV8N 0
set ALL_OPERATOR 0
set SELECTABLE_NET 1
set YOLOV5 1
set YOLOV8 0
source {D:/Anlogic/TD_Release_2026.1_SP2.200.067/ip/depot/Video_NPU_1.1/Dependency.tcl}
if {[nn_pooling_def $NPU_SOFT $ALL_OPERATOR $YOLOV3TINY $YOLOV4 $YOLOV5S $YOLOV8N] != $NN_POOLING} {error "Dependency mismatch NN_POOLING"}
if {[nn_activate_def $NPU_SOFT $ALL_OPERATOR $MBFace] != $NN_ACTIVATE} {error "Dependency mismatch NN_ACTIVATE"}
if {[nn_upsample_def $NPU_SOFT $ALL_OPERATOR $YOLOV3TINY $YOLOV3 $YOLOV4 $YOLOV5S $YOLOV8N] != $NN_UPSAMPLE} {error "Dependency mismatch NN_UPSAMPLE"}
if {[nn_route_def $NPU_SOFT $ALL_OPERATOR $YOLOV3TINY $YOLOV3 $YOLOV4 $YOLOV5S $YOLOV8N] != $NN_ROUTE} {error "Dependency mismatch NN_ROUTE"}
if {[nn_shortcut_def $NPU_SOFT $ALL_OPERATOR $YOLOV3 $YOLOV4 $YOLOV5S $YOLOV8N $MBFace] != $NN_SHORTCUT} {error "Dependency mismatch NN_SHORTCUT"}
set ::env(IP_EXPORT_PATH) {D:/Works/Embedded_contest/dev/npu_experiments/dr1_probe_20261019_01/ip_v3_no_video}
xmlipgen -design_file Design.xml -designConfig_file DesignConfiguration.xml -component_file {D:/Anlogic/TD_Release_2026.1_SP2.200.067/ip/depot/Video_NPU_1.1/Component.xml} -usernamed_file design_0_Video_NPU_0.xml -mode behavior -package DR1M90GEG400
exit
