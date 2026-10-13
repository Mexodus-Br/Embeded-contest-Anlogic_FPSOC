# Scope-only observation interface: 10ns reference and explicit 0ns observation delays.
# There is no clocked external receiver. These reference delays are not a driver timing contract.
create_clock -name board_100m -period 10 [get_ports clk_100m]
set_output_delay -clock board_100m -max 0 [get_ports {a0_step a0_dir a0_en a1_step a1_dir a1_en a2_step a2_dir a2_en}]
set_output_delay -clock board_100m -min 0 [get_ports {a0_step a0_dir a0_en a1_step a1_dir a1_en a2_step a2_dir a2_en}]
