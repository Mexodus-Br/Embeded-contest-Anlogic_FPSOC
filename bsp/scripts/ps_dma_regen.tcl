set_param_value -param_id DDRC_IO_VOL -value 1.35
set_param_value -param_id Master_AXI_GP0_Interface -value 1
set_param_value -param_id Slave_AXI_HP0_Interface -value 1
set_param_value -param_id Slave_AXI_HP0_DATA_WIDTH -value 64
set_param_value -param_id F2P_IRQ_Available -value 1
set_param_value -param_id P2F_Reset0_Available -value 1
ps_gui_select_dialog Processor_System
ps_gui_click_push_button Processor_System PsIpCfg.OK
