import_device dr1_90.db -package DR1M90GEG400 -speed 2
puts "TIMING_COMMANDS [info commands *tim*]"
foreach cmd {{report_timing_summary -help} {report_timing -help} {help report_timing_summary} {help report_timing}} {
 puts "PROBE $cmd"
 catch {eval $cmd} result
 puts "RESULT $result"
}
exit
