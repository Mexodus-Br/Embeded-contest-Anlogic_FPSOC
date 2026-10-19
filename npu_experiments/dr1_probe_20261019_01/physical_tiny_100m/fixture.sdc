# Both interface clocks must be copies of the same external source.
create_clock -name npu_data -period 10 [get_ports M_AXI_ACLK]
create_generated_clock -name npu_config -source [get_ports M_AXI_ACLK] -divide_by 1 [get_ports S_AXILite_ACLK]
