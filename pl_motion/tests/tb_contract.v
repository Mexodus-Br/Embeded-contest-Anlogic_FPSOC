`timescale 1ns/1ps
module tb_contract;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0, enable_req=0,disable_req=0,rebase_req=0,open_req=0,cmd_valid=0;
    reg fault=0;
    wire stopped;
    wire enabled,step,dir,valid,busy,done,accepted,rejected,ready;
    wire signed [63:0] position;
    // Delays deliberately larger than the pulse period.
    axis_motion #(.STEP_HIGH_CYCLES(2),.STEP_LOW_CYCLES(2),
        .DIR_SETUP_CYCLES(3),.DIR_HOLD_CYCLES(8),.EN_SETUP_CYCLES(10),
        .EN_DISABLE_CYCLES(6),.STEP_PERIOD_CYCLES(4),.MAX_STEP_HZ(25000000)) dut(
        .clk(clk),.rst_n(rst_n),.enable_req(enable_req),.disable_req(disable_req),
        .rebase_req(rebase_req),.rebase_position(64'sd0),.open_req(open_req),
        .open_session_id(64'd1),.cmd_valid(cmd_valid),.cmd_session_id(64'd1),
        .cmd_target(64'sd0),.stop_req(1'b0),.underflow(1'b0),.fault(fault),
        .clear_fault(1'b0),.step(step),.dir(dir),.en(enabled),.position(position),
        .position_valid(valid),.busy(busy),.done(done),.cmd_accepted(accepted),
        .rejected(rejected),.cmd_ready(ready),.stopped(stopped));
    wire invalid_default,invalid_high,invalid_period,invalid_rate,invalid_sum;
    axis_motion defaults(.config_valid(invalid_default));
    axis_motion #(.STEP_HIGH_CYCLES(0),.STEP_LOW_CYCLES(1),
        .STEP_PERIOD_CYCLES(2),.MAX_STEP_HZ(100000000)) bad_high(.config_valid(invalid_high));
    axis_motion #(.STEP_HIGH_CYCLES(2),.STEP_LOW_CYCLES(2),
        .STEP_PERIOD_CYCLES(3),.MAX_STEP_HZ(100000000)) bad_period(.config_valid(invalid_period));
    axis_motion #(.STEP_HIGH_CYCLES(1),.STEP_LOW_CYCLES(1),
        .STEP_PERIOD_CYCLES(2),.MAX_STEP_HZ(49999999)) bad_rate(.config_valid(invalid_rate));
    axis_motion #(.STEP_HIGH_CYCLES(64'hffffffffffffffff),.STEP_LOW_CYCLES(1),
        .STEP_PERIOD_CYCLES(64'hffffffffffffffff),.MAX_STEP_HZ(100000000))
        bad_sum(.config_valid(invalid_sum));
    task check;
        input condition;input [511:0] message;
        begin if(condition!==1'b1)begin $display("FAIL contract: %0s",message);$fatal(1);end end
    endtask
    task tick;begin @(posedge clk);#2;end endtask
    integer i,stop_events=0;
    always @(posedge clk)begin #1;if(stopped)stop_events=stop_events+1;end
    initial begin
        tick;check(!invalid_default && !invalid_high && !invalid_period &&
            !invalid_rate && !invalid_sum,"unsafe and overflowing config rejected");
        @(negedge clk);rst_n=1;rebase_req=1;tick;
        @(negedge clk);rebase_req=0;enable_req=1;open_req=1;tick;
        check(rejected && !enabled,"conflicting controls rejected atomically");
        @(negedge clk);open_req=0;tick;
        @(negedge clk);enable_req=0;open_req=1;tick;
        @(negedge clk);open_req=0;cmd_valid=1;tick;
        check(rejected && !accepted,"command before EN setup rejected");
        @(negedge clk);cmd_valid=0;repeat(12)tick;check(ready,"EN setup becomes ready");
        @(negedge clk);cmd_valid=1;tick;check(accepted,"zero target accepted");
        @(negedge clk);cmd_valid=0;tick;
        check(done && !step && dir && enabled && position==0,"zero displacement preserves outputs");
        @(negedge clk);disable_req=1;fault=1;tick;
        check(!valid && enabled,"disable invalidates before EN release");
        @(negedge clk);disable_req=0;
        // Already pulse-safe, but drain completion precedes the OFF delay.
        tick;for(i=0;i<6;i=i+1)begin tick;check(enabled,"EN disable delay preserved");end
        tick;check(!enabled && !busy,"explicit disable releases EN");
        repeat(12)tick;
        check(stop_events==1 && !busy && !enabled,
              "persistent fault plus disable completes once and cannot restore EN");
        // Asynchronous reset must act between clocks.
        @(negedge clk);rst_n=0;#1;
        check(!enabled && !step && !valid && position==0,"asynchronous reset assertion");
        $display("PASS contract: invalid config/control/zero/EN delays/reset");$finish;
    end
endmodule
