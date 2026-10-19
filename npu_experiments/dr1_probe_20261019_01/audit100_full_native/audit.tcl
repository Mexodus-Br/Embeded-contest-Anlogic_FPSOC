cd {D:/Works/Embedded_contest/dev/npu_experiments/dr1_probe_20261019_01/audit100_full_native}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db {D:/Works/Embedded_contest/dev/npu_experiments/dr1_probe_20261019_01/ip_full_native/gate.db}
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "NPU_THREADS [get_param flow thread]"
get_num_thread
clear_user_sdc
read_sdc fixture.sdc
update_timing
if {[llength [get_clocks *]] != 2} {error "Expected two clocks"}
puts "CLOCKS [get_clocks *]"
report_timing_summary -file gate_100m.timing -path_num 5
puts "NPU_CLOCK_AUDIT_DONE"
exit
