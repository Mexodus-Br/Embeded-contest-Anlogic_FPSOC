cd D:/Works/Embedded_contest/dev/pl_safety/evidence/margin_semantics2
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db D:/Works/Embedded_contest/dev/pl_safety/build/rxcarry_top6/route.db
# threads=16; TD 6.2 uses the singular property name "thread".
set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "SAFETY_TD_THREADS [get_param flow thread]"
get_num_thread

update_timing -mode final
report_timing_summary -file original.timing -path_num 1
set clocks [get_clocks -include_generated_clocks *]
puts "MARGIN_CLOCK_SELECTION [llength $clocks] $clocks"
if {[llength $clocks]<4} {error "Expected board and three PS domain clocks"}
set_clock_uncertainty -setup 1.25 $clocks
update_timing -mode final
report_timing_summary -file margin.timing -path_num 1
set_clock_uncertainty -setup 0 $clocks
update_timing -mode final
report_timing_summary -file restored.timing -path_num 1
check_timing -verbose -file restored.check
puts SAFETY_MARGIN_PROBE_COMPLETE
exit
