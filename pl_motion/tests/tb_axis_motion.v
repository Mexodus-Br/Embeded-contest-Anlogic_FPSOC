`timescale 1ns/1ps
module tb_axis_motion;
    parameter H=3, L=2, S=4, Q=7, E=5, OFF=3, P=8, POL=1;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, enable_req=0, disable_req=0, rebase_req=0, open_req=0;
    reg cmd_valid=0, stop_req=0, underflow=0, fault=0, clear_fault=0;
    reg signed [63:0] rebase_position=0, cmd_target=0;
    reg [63:0] open_session_id=0, cmd_session_id=0;
    wire step,dir,en,position_valid,session_valid,fault_latched;
    wire config_valid,cmd_ready,busy,cmd_accepted,rebase_accepted;
    wire open_accepted,rejected,pulse_event,done,stopped,cancelled;
    wire signed [63:0] position;
    wire [63:0] session_id;
    axis_motion #(.STEP_HIGH_CYCLES(H),.STEP_LOW_CYCLES(L),
        .DIR_SETUP_CYCLES(S),.DIR_HOLD_CYCLES(Q),.EN_SETUP_CYCLES(E),
        .EN_DISABLE_CYCLES(OFF),.STEP_PERIOD_CYCLES(P),
        .MAX_STEP_HZ(100000000),.EN_ACTIVE_LEVEL(POL)) dut (
        .clk(clk),.rst_n(rst_n),.enable_req(enable_req),.disable_req(disable_req),
        .rebase_req(rebase_req),.rebase_position(rebase_position),
        .open_req(open_req),.open_session_id(open_session_id),
        .cmd_valid(cmd_valid),.cmd_session_id(cmd_session_id),.cmd_target(cmd_target),
        .stop_req(stop_req),.underflow(underflow),.fault(fault),.clear_fault(clear_fault),
        .step(step),.dir(dir),.en(en),.position(position),.position_valid(position_valid),
        .session_valid(session_valid),.session_id(session_id),.fault_latched(fault_latched),
        .config_valid(config_valid),.cmd_ready(cmd_ready),.busy(busy),
        .cmd_accepted(cmd_accepted),.rebase_accepted(rebase_accepted),
        .open_accepted(open_accepted),.rejected(rejected),.pulse_event(pulse_event),
        .done(done),.stopped(stopped),.cancelled(cancelled));
    integer cycle=0, rise_at=-100000, fall_at=-100000, dir_at=-100000;
    integer enable_at=-100000, edges=0, checks=0, done_count=0, stop_count=0;
    reg prev_step=0,prev_dir=1,prev_en=0, sampled_safety;
    reg signed [63:0] expected=0;
    task check;
        input condition; input [511:0] message;
        begin
            checks=checks+1;
            if (condition !== 1'b1) begin
                $display("FAIL cycle=%0d: %0s",cycle,message); $fatal(1);
            end
        end
    endtask
    // Scoreboard observes physical output transitions, not planned step counts.
    always @(posedge clk) begin
        sampled_safety=stop_req||underflow||fault||disable_req;
        #1; cycle=cycle+1;
        if (!rst_n) begin
            expected=0; prev_step=0;prev_dir=1;prev_en=0;
            rise_at=-100000;fall_at=cycle;dir_at=cycle;enable_at=cycle;
            check(!step && en != POL && !position_valid && !session_valid,
                  "reset outputs and validity");
        end else begin
            if (en == POL && !prev_en) enable_at=cycle;
            if (dir != prev_dir) begin
                check(!step && !prev_step,"DIR only changes while inactive");
                check(cycle-rise_at >= Q,"DIR hold"); dir_at=cycle;
            end
            if (step && !prev_step) begin
                check(!sampled_safety,"safety beats new edge");
                check(en == POL && position_valid,"edge requires EN/valid position");
                check(cycle-enable_at >= E,"EN setup");
                check(cycle-dir_at >= S,"DIR setup");
                check(cycle-fall_at >= L,"STEP low width");
                check(cycle-rise_at >= P,"maximum rate/period");
                rise_at=cycle; edges=edges+1;
                expected=expected+(dir ? 64'sd1 : -64'sd1);
            end
            if (!step && prev_step) begin
                check(cycle-rise_at == H,"exact high width"); fall_at=cycle;
            end
            if (rebase_accepted) expected=rebase_position;
            check(position === expected,"position equals actual edge count/rebase");
            check(pulse_event === (step && !prev_step),"event equals physical rising edge");
            if (done || stopped) begin
                check(!step && cycle-fall_at >= L && cycle-rise_at >= Q,
                      "completion requires low and hold");
            end
            if (en != POL && prev_en) begin
                check(!step && cycle-fall_at >= L && cycle-rise_at >= Q,
                      "disable after safe pulse");
            end
            if(done)done_count=done_count+1;
            if(stopped)stop_count=stop_count+1;
            prev_step=step;prev_dir=dir;prev_en=(en==POL);
        end
    end
    task tick; begin @(posedge clk); #2; end endtask
    task reset_axis;
        begin
            @(negedge clk); rst_n=0;
            enable_req=0;disable_req=0;rebase_req=0;open_req=0;cmd_valid=0;
            stop_req=0;underflow=0;fault=0;clear_fault=0;
            tick;tick; @(negedge clk);rst_n=1;tick;
        end
    endtask
    task wait_idle;
        integer n;
        begin n=0; while(busy && n<1000) begin tick;n=n+1;end
            check(!busy,"bounded completion"); end
    endtask
    task base;
        input signed [63:0] value;
        begin @(negedge clk);rebase_position=value;rebase_req=1;tick;
            check(rebase_accepted,"REBASE accepted");
            @(negedge clk);rebase_req=0;tick;end
    endtask
    task start_session;
        input [63:0] id;
        begin
            @(negedge clk);enable_req=1;tick;
            @(negedge clk);enable_req=0;open_req=1;open_session_id=id;tick;
            check(open_accepted,"new session accepted");
            @(negedge clk);open_req=0;
            repeat(E+2)tick;
            cmd_session_id=id;
        end
    endtask
    task command;
        input signed [63:0] value;
        begin @(negedge clk);cmd_target=value;cmd_valid=1;tick;
            check(cmd_accepted,"target accepted");
            @(negedge clk);cmd_valid=0; end
    endtask
    task move;
        input signed [63:0] value; input integer count;
        integer before_edges,before_done;
        begin before_edges=edges;before_done=done_count;command(value);wait_idle;
            check(position===value,"absolute target reached");
            check(edges-before_edges==count,"exact pulse count");
            check(done_count==before_done+1,"one completion"); end
    endtask
    integer i,kind,variant,before_edges,before_stop;
    reg signed [63:0] snapshot;
    initial begin
        reset_axis;
        check(config_valid,"explicit timing configuration valid");
        @(negedge clk);enable_req=1;tick;check(rejected,"invalid position blocks enable");
        @(negedge clk);enable_req=0;
        base(0);start_session(1);
        move(5,5);move(-3,8);move(-3,0);move(2,5);
        before_edges=edges;
        @(negedge clk);stop_req=1;cmd_valid=1;cmd_target=100;tick;
        check(!cmd_accepted && rejected && !session_valid && edges==before_edges,
              "STOP beats command acceptance");
        @(negedge clk);stop_req=0;cmd_valid=0;wait_idle;
        @(negedge clk);cmd_valid=1;tick;
        check(rejected,"late cancelled-session command rejected");
        @(negedge clk);cmd_valid=0;start_session(4);
        @(negedge clk);rebase_req=1;tick;check(rejected,"enabled REBASE blocked");
        @(negedge clk);rebase_req=0;cmd_session_id=999;cmd_valid=1;tick;
        check(rejected,"stale command rejected");
        @(negedge clk);cmd_valid=0;cmd_session_id=1;

        reset_axis;base(64'sh7ffffffffffffffe);start_session(2);
        move(64'sh7fffffffffffffff,1);move(64'sh7fffffffffffffff,0);
        @(negedge clk);cmd_target=64'sh8000000000000000;#1;
        check(dut.delta===-65'sh0ffffffffffffffff,"full-range negative signed65 delta");
        command(64'sh8000000000000000);
        while(edges<24)tick;
        check(position===64'sh7ffffffffffffffa && !dir,
              "full-range negative target emits negative steps without wrap");
        @(negedge clk);stop_req=1;tick;@(negedge clk);stop_req=0;wait_idle;
        reset_axis;base(64'sh8000000000000001);start_session(3);
        move(64'sh8000000000000000,1);move(64'sh8000000000000000,0);
        @(negedge clk);cmd_target=64'sh7fffffffffffffff;#1;
        check(dut.delta===65'sh0ffffffffffffffff,"full-range positive signed65 delta");
        command(64'sh7fffffffffffffff);repeat(P+S+5)tick;
        check(position>64'sh8000000000000000 && dir,
              "full-range positive target emits positive steps without wrap");
        @(negedge clk);stop_req=1;tick;@(negedge clk);stop_req=0;wait_idle;

        // Exhaustive cycle offsets include acceptance/setup, rising-edge slot,
        // high pulse, falling slot, low pulse and between-pulse slots.
        for(kind=0;kind<4;kind=kind+1) begin
          for(variant=0;variant<2;variant=variant+1) begin
            for(i=0;i<2*P+S+Q+H+L+8;i=i+1) begin
                reset_axis;base(0);start_session(100+kind*100+i);
                command(variant==0 ? -100 : -1);repeat(i)tick;
                before_edges=edges;before_stop=stop_count;
                @(negedge clk);
                case(kind) 0:stop_req=1;1:underflow=1;2:fault=1;3:disable_req=1;endcase
                tick;
                check(!session_valid,"safety cancels session immediately");
                check(edges==before_edges,"safety inhibits same-cycle edge");
                @(negedge clk);stop_req=0;underflow=0;disable_req=0;
                wait_idle;check(stop_count==before_stop+1,"one stopped event");
                snapshot=position;repeat(P+Q+5)tick;
                check(position===snapshot && edges==before_edges,"no resumed old motion");
                if(kind==3)check(en!=POL && !position_valid,"DISABLE invalidates position");
                else check(en==POL && position_valid,"STOP retains EN/position");
                if(kind==2) begin
                    check(fault_latched,"fault latched");
                    @(negedge clk);clear_fault=1;tick;
                    check(fault_latched,"active fault cannot clear");
                    @(negedge clk);fault=0;tick;
                    check(!fault_latched && !session_valid,"clear does not restart");
                    @(negedge clk);clear_fault=0;
                end
                if(kind!=3) begin
                    @(negedge clk);open_req=1;open_session_id=session_id;tick;
                    check(rejected,"cancelled session ID cannot reopen");
                    @(negedge clk);open_req=0;
                    start_session(10000+kind*100+i);move(snapshot+1,1);
                end
            end
          end
        end
        // Reset at every phase explicitly permits pulse truncation.
        for(i=0;i<P+S+H+L+8;i=i+1)begin
            reset_axis;base(0);start_session(20000+i);command(100);
            repeat(i)tick;reset_axis;
            check(position==0 && !position_valid && en!=POL && !session_valid,
                  "reset clears count and cancels execution");
            repeat(P+3)tick;check(!step,"reset cannot auto-resume");
        end
        $display("PASS axis checks=%0d edges=%0d safety_offsets=%0d reset_offsets=%0d",
                 checks,edges,8*(2*P+S+Q+H+L+8),P+S+H+L+8);
        $finish;
    end
    initial begin #2000000; $display("FAIL timeout");$fatal(1);end
endmodule
