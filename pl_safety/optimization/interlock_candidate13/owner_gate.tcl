set_param flow thread 16
get_num_thread
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/pl_safety/build/interlock_route13/gate.db
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads16"}
puts "OWNER_AUDIT_THREADS [get_param flow thread]"
get_num_thread
set owners [get_regs -hier -quiet *home_owner_q*]
puts "OWNER_CACHE_REGISTER_COUNT [llength $owners]"
foreach cell $owners {
 puts "OWNER_CACHE_REGISTER $cell"
 report_cells [get_cells -quiet $cell] -connection -attributes
}
set nets [get_nets -hier -quiet *home_owner*]
if {[llength $nets] > 0} {report_nets $nets -connection -pin_display_limit 1000}
puts OWNER_GATE_AUDIT_COMPLETE
exit
