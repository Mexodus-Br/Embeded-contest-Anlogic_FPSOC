/************************************************************\
**	Copyright (c) 2012-2024 Anlogic Inc.
**	All Right Reserved.
\************************************************************/
/************************************************************\
**	Build time: Nov 12 2024 10:45:07
**	TD version	:	5.9.135718
************************************************************/
`timescale 1ns/1ps
module system_ARM_Processor_System_0
(
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
      .i2c0_scl_in(i2c0_scl_in),
      .i2c0_scl_oe(i2c0_scl_oe),
      .i2c0_sda_in(i2c0_sda_in),
      .i2c0_sda_oe(i2c0_sda_oe),
      .p2f_clk0(p2f_clk0)
  );
endmodule
