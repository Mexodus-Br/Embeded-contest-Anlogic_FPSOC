# Scope-only ASYNCHRONOUS observation interface; no external clocked receiver.
# 10ns internal clocks remain unchanged. Output_delay names the reference only.
# The nine GPIO paths have an explicit datapath-only bound, not synchronous receiver setup.
create_clock -name board_100m -period 10 [get_ports clk_100m]
set_output_delay -clock board_100m -max 0 [get_ports {a0_step a0_dir a0_en a1_step a1_dir a1_en a2_step a2_dir a2_en}]
set_output_delay -clock board_100m -min 0 [get_ports {a0_step a0_dir a0_en a1_step a1_dir a1_en a2_step a2_dir a2_en}]
set_max_delay -to [get_ports {a0_step a0_dir a0_en a1_step a1_dir a1_en a2_step a2_dir a2_en}] -datapath_only 20

# Four new asynchronous safety inputs: only pad -> first synchronizer stage is excepted.
set_false_path -from [get_ports {safety_limit_n[*] safety_estop_n}]
