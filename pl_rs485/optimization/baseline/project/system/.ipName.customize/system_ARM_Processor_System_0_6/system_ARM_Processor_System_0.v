/************************************************************\
**	Copyright (c) 2012-2024 Anlogic Inc.
**	All Right Reserved.
\************************************************************/
/************************************************************\
**	Build time: Feb 17 2025 15:31:10
**	TD version	:	5.9.135718
************************************************************/
`timescale 1ns/1ps
module system_ARM_Processor_System_0
(
  input                         can0_rx_in,
  output                        can0_stby,
  output                        can0_tx_out,
  input                         i2c0_scl_in,
  output                        i2c0_scl_oe,
  input                         i2c0_sda_in,
  output                        i2c0_sda_oe,
  output                        p2f_clk0
);

  ARM_Processor_System_f6ddd1d59490
  #(
      .p2f_clk0_1st_Divisor(8)
  )ARM_Processor_System_f6ddd1d59490_Inst
  (
      .can0_rx_in(can0_rx_in),
      .can0_stby(can0_stby),
      .can0_tx_out(can0_tx_out),
      .i2c0_scl_in(i2c0_scl_in),
      .i2c0_scl_oe(i2c0_scl_oe),
      .i2c0_sda_in(i2c0_sda_in),
      .i2c0_sda_oe(i2c0_sda_oe),
      .p2f_clk0(p2f_clk0)
  );
endmodule
