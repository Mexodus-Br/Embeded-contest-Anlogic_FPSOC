`timescale 1ns/1ps
module tb_home_overflow;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,rebase=0,owner=0,hen=0;reg [2:0] run=0;
wire [3:0] step,valid,faults;wire [2:0] hfault;wire safe;wire [255:0] position;
motion_executor #(.HOME_SUPPORT(1),.STEP_HIGH_CYCLES({4{64'd3}}),.STEP_LOW_CYCLES({4{64'd2}}),
 .DIR_SETUP_CYCLES({4{64'd4}}),.DIR_HOLD_CYCLES({4{64'd7}}),.EN_SETUP_CYCLES({4{64'd5}}),
 .EN_DISABLE_CYCLES({4{64'd3}}),.MAX_STEP_HZ({4{64'd10000000}})) dut(
 .clk(clk),.rst_n(rst_n),.rebase_req(rebase),.rebase_mask(4'd7),.rebase_position({192'd0,64'h7fffffffffffffff}),
 .enable_req(1'b0),.enable_mask(4'd0),.disable_req(1'b0),.disable_mask(4'd0),.stop_req(1'b0),.fault(4'd0),.clear_fault(1'b0),
 .plan_valid(1'b0),.plan_data(1197'd0),.step(step),.position(position),.position_valid(valid),.fault_latched(faults),.pulse_safe(safe),
 .home_owner(owner),.home_enable(hen),.home_reference(1'b0),.home_complete(1'b0),.home_run(run),.home_direction(3'b111),
 .home_period({3{64'd10}}),.home_reference_position(192'd0),.safety_invalidate(owner ? 4'd7:4'd0),.home_fault(hfault));
integer cycles=0;
always @(negedge clk)if(rst_n && owner)begin
 cycles=cycles+1;
 if(step!=0)$fatal(1,"HOME overflow must suppress all simultaneous candidates step=%b",step);
 if(cycles>100)$fatal(1,"overflow watchdog");
end
initial begin
 repeat(4)@(negedge clk);rst_n=1;repeat(12)@(negedge clk);
 rebase=1;@(negedge clk);rebase=0;
 if(position[63:0]!=64'h7fffffffffffffff)$fatal(1,"low-level diagnostic seed");
 owner=1;hen=1;@(negedge clk);hen=0;run=7;
 while(hfault==0)@(negedge clk);repeat(4)@(negedge clk);
 if(position[127:64]!=0 || position[191:128]!=0 || valid[2:0]!=0 || faults!=15)$fatal(1,"group atomic overflow result");
 $display("PASS home overflow group suppression cycles=%0d",cycles);$finish;
end
endmodule
