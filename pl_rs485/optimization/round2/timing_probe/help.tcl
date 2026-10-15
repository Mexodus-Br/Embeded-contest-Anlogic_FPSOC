cd D:/Works/Embedded_contest/dev/pl_rs485/optimization/round2/timing_probe
catch {report_timing_summary -help} result
puts $result
catch {report_timing -help} result
puts $result
exit
