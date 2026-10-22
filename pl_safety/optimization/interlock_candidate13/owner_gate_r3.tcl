set_param flow thread 16
get_num_thread
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/pl_safety/build/interlock_route13/gate.db
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads16"}
puts "OWNER_AUDIT_THREADS [get_param flow thread]"
get_num_thread
# get_regs returns a Q-net alias in this TD version. Query the real driver
# observed in the net connection report, then require a nonempty cell result.
set cells [get_cells -hier -quiet *controller/home_owner_q_reg]
if {[llength $cells] != 1} {error "Expected one exact mapped ownership FF"}
puts "OWNER_CACHE_PHYSICAL_CELL_COUNT [llength $cells]"
report_cells $cells -connection -attributes
puts OWNER_GATE_AUDIT_COMPLETE
exit
