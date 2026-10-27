cd D:/Works/Embedded_contest/dev/integration/home_calibration_20261027/hardware
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db route.db
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "HOME_TD_THREADS [get_param flow thread]"
get_num_thread
bitgen -bit system.bit
puts HOME_CALIBRATION_BIT_COMPLETE
exit
