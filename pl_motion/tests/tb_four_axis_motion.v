`timescale 1ns/1ps
module tb_four_axis_motion;
    parameter SCALE=1, POL=15, TEST_GROUP=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,rebase_req=0,enable_req=0,disable_req=0,open_req=0,cmd_valid=0;
    reg stop_req=0,underflow=0,clear_fault=0;
    reg [3:0] fault=0,rebase_mask=15,enable_mask=15,disable_mask=15,cmd_mask=15;
    reg [255:0] rebase_position=0,cmd_target=0;
    reg [63:0] open_session_id=1,cmd_session_id=1,duration_tick=2;
    wire [3:0] step,dir,en,position_valid,fault_latched,config_valid,pulse_event;
    wire [255:0] position;
    wire [63:0] session_id,slot_id;
    wire session_valid,cmd_ready,busy,cmd_accepted,rebase_accepted,open_accepted;
    wire rejected,point_start,done,stopped,cancelled,slot_event;
    wire [3:0] default_config;
    four_axis_motion unconfigured(.clk(1'b0),.rst_n(1'b0),.rebase_req(1'b0),
        .rebase_mask(4'b0),.rebase_position(256'b0),.enable_req(1'b0),.enable_mask(4'b0),
        .disable_req(1'b0),.disable_mask(4'b0),.open_req(1'b0),.open_session_id(64'b0),
        .cmd_valid(1'b0),.cmd_session_id(64'b0),.cmd_mask(4'b0),.cmd_target(256'b0),
        .duration_tick(64'b0),.stop_req(1'b0),.underflow(1'b0),.fault(4'b0),
        .clear_fault(1'b0),.config_valid(default_config));
    wire [3:0] invalid_config;
    four_axis_motion #(
        .STEP_HIGH_CYCLES({64'd1,64'hffffffffffffffff,64'd1,64'd1}),
        .STEP_LOW_CYCLES({64'd1,64'hffffffffffffffff,64'd1,64'd1}),
        .DIR_SETUP_CYCLES({64'd0,64'd0,64'hffffffffffffffff,64'd0}),
        .DIR_HOLD_CYCLES({64'd0,64'd0,64'hffffffffffffffff,64'd0}),
        .EN_SETUP_CYCLES({64'hffffffffffffffff,64'd0,64'd0,64'd0}),
        .MAX_STEP_HZ({64'd100000000,64'd100000000,64'd100000000,64'd0}))
        bad_config(.clk(1'b0),.rst_n(1'b0),.rebase_req(1'b0),
        .rebase_mask(4'b0),.rebase_position(256'b0),.enable_req(1'b0),.enable_mask(4'b0),
        .disable_req(1'b0),.disable_mask(4'b0),.open_req(1'b0),.open_session_id(64'b0),
        .cmd_valid(1'b0),.cmd_session_id(64'b0),.cmd_mask(4'b0),.cmd_target(256'b0),
        .duration_tick(64'b0),.stop_req(1'b0),.underflow(1'b0),.fault(4'b0),
        .clear_fault(1'b0),.config_valid(invalid_config));
    localparam [255:0] H={64'd5*SCALE,64'd1*SCALE,64'd4*SCALE,64'd3*SCALE};
    localparam [255:0] L={64'd2*SCALE,64'd3*SCALE,64'd1*SCALE,64'd2*SCALE};
    localparam [255:0] S={64'd3*SCALE,64'd8*SCALE,64'd0,64'd4*SCALE};
    localparam [255:0] Q={64'd12*SCALE,64'd2*SCALE,64'd10*SCALE,64'd7*SCALE};
    localparam [255:0] E={64'd0,64'd7*SCALE,64'd3*SCALE,64'd5*SCALE};
    localparam [255:0] OFF={64'd6*SCALE,64'd1*SCALE,64'd4*SCALE,64'd3*SCALE};
    localparam [255:0] RATE={64'd12500000/SCALE,64'd25000000/SCALE,
                           64'd5000000/SCALE,64'd10000000/SCALE};
    four_axis_motion #(.STEP_HIGH_CYCLES(H),.STEP_LOW_CYCLES(L),.DIR_SETUP_CYCLES(S),
        .DIR_HOLD_CYCLES(Q),.EN_SETUP_CYCLES(E),.EN_DISABLE_CYCLES(OFF),
        .MAX_STEP_HZ(RATE),.EN_ACTIVE_LEVEL(POL)) dut(
        .clk(clk),.rst_n(rst_n),.rebase_req(rebase_req),.rebase_mask(rebase_mask),
        .rebase_position(rebase_position),.enable_req(enable_req),.enable_mask(enable_mask),
        .disable_req(disable_req),.disable_mask(disable_mask),.open_req(open_req),
        .open_session_id(open_session_id),.cmd_valid(cmd_valid),.cmd_session_id(cmd_session_id),
        .cmd_mask(cmd_mask),.cmd_target(cmd_target),.duration_tick(duration_tick),
        .stop_req(stop_req),.underflow(underflow),.fault(fault),.clear_fault(clear_fault),
        .step(step),.dir(dir),.en(en),.position(position),.position_valid(position_valid),
        .session_id(session_id),.session_valid(session_valid),.fault_latched(fault_latched),
        .config_valid(config_valid),.cmd_ready(cmd_ready),.busy(busy),.cmd_accepted(cmd_accepted),
        .rebase_accepted(rebase_accepted),.open_accepted(open_accepted),.rejected(rejected),
        .point_start(point_start),.done(done),.stopped(stopped),.cancelled(cancelled),
        .pulse_event(pulse_event),.slot_event(slot_event),.slot_id(slot_id));
    integer cycle=0,checks=0,points=0,edges=0,slots=0,stops=0,safety_cases=0,reset_cases=0;
    reg [3:0] prev_step=0,prev_dir=15,prev_enabled=0,sampled_safety;
    integer rise_at[0:3],fall_at[0:3],dir_at[0:3],enable_at[0:3];
    reg signed [63:0] model_pos[0:3];
    reg signed [64:0] model_next;
    // Independent closed-form oracle: no DUT planner state is read.
    reg tracking=0,oracle_ok;
    reg [63:0] expected_n[0:3],expected_master,expected_guard,expected_cycles;
    reg [3:0] expected_positive,expected_mask;
    reg [255:0] expected_target;
    reg [127:0] math_product,math_cycles;
    reg signed [63:0] oracle_target;
    reg signed [64:0] oracle_diff;
    reg [64:0] oracle_mag;
    reg [63:0] guard_lane,slot_min;
    integer start_at,last_stop_at=-100000;
    reg [63:0] expected_slot;
    reg [3:0] expected_emit,rising;
    task check;
        input condition;input [639:0] message;
        begin checks=checks+1;
            if(condition!==1'b1)begin $display("FAIL four cycle=%0d: %0s",cycle,message);$fatal(1);end
        end
    endtask
    task prepare_oracle;
        integer j;
        begin
            expected_master=0;expected_guard=0;expected_positive=dir;
            expected_target=cmd_target;expected_mask=cmd_mask;
            math_cycles={64'b0,duration_tick}*128'd100;
            expected_cycles=math_cycles[63:0];
            oracle_ok=duration_tick!=0 && math_cycles[127:64]==0;
            for(j=0;j<4;j=j+1)begin
                expected_n[j]=0;
                if(cmd_mask[j])begin
                    oracle_target=$signed(cmd_target[j*64+:64]);
                    oracle_diff=$signed({oracle_target[63],oracle_target})-
                                $signed({model_pos[j][63],model_pos[j]});
                    oracle_mag=oracle_diff[64] ? -oracle_diff : oracle_diff;
                    expected_n[j]=oracle_mag[63:0];
                    if(oracle_mag!=0)begin
                        expected_positive[j]=!oracle_diff[64];
                        if(expected_n[j]>expected_master)expected_master=expected_n[j];
                        guard_lane=Q[j*64+:64]+S[j*64+:64];
                        if(E[j*64+:64]>guard_lane)guard_lane=E[j*64+:64];
                        if(L[j*64+:64]>guard_lane)guard_lane=L[j*64+:64];
                        guard_lane=guard_lane+2;
                        if(guard_lane>expected_guard)expected_guard=guard_lane;
                    end
                end
            end
            if(expected_master!=0)begin
                if(expected_cycles<=expected_guard)oracle_ok=0;
                else begin
                    slot_min=(expected_cycles-expected_guard)/expected_master;
                    for(j=0;j<4;j=j+1)if(expected_n[j]!=0)begin
                        math_product={64'b0,slot_min}*{64'b0,RATE[j*64+:64]};
                        if(slot_min<H[j*64+:64]+L[j*64+:64] ||
                           slot_min<Q[j*64+:64] || math_product<100000000)oracle_ok=0;
                    end
                end
            end
        end
    endtask
    integer m;
    always @(posedge clk)begin
        sampled_safety={4{stop_req||underflow||(|fault)||disable_req}};
        #1;cycle=cycle+1;
        rising=step & ~prev_step;
        if(!rst_n)begin
            tracking=0;prev_step=0;prev_dir=15;prev_enabled=0;
            last_stop_at=-100000;
            for(m=0;m<4;m=m+1)begin
                model_pos[m]=0;rise_at[m]=-100000;fall_at[m]=cycle;
                dir_at[m]=cycle;enable_at[m]=cycle;
            end
            check(step==0 && en==(4'b1111 ^ POL) && position_valid==0 && !session_valid,
                  "reset disables all axes and invalidates position/session");
        end else begin
            if(|sampled_safety)begin
                tracking=0;
                check(rising==0 && !point_start,"safety atomically inhibits all new edges/start");
            end
            if(point_start)begin
                check(cmd_accepted && oracle_ok,"only feasible whole group starts");
                tracking=1;start_at=cycle;expected_slot=0;points=points+1;
                check(rising==0,"preflight/start cannot emit early pulses");
            end
            expected_emit=0;
            if(tracking && expected_master!=0 && expected_slot<expected_master)begin
                math_product={64'b0,expected_slot}*{64'b0,(expected_cycles-expected_guard)};
                if(cycle-start_at==expected_guard+math_product/expected_master)begin
                    for(m=0;m<4;m=m+1)if(expected_n[m]!=0)begin
                        if(expected_slot==0)expected_emit[m]=1;
                        else begin
                            math_product={64'b0,expected_slot}*{64'b0,expected_n[m]};
                            // Emit where floor(k*Ni/Nmax) increases; all nonzero axes at k=0.
                            expected_emit[m]=(math_product/expected_master)>
                                 ((math_product-expected_n[m])/expected_master);
                        end
                    end
                    check(slot_event && slot_id==expected_slot,"exact closed-form slot time/ID");
                    check(rising==expected_emit,"corresponding slot edges occur on the same clock");
                    expected_slot=expected_slot+1;
                end else check(!slot_event && rising==0,"no pulse or slot outside its scheduled cycle");
            end else if(tracking)check(rising==0 && !slot_event,"zero point or tail emits no pulse");
            check(pulse_event===rising,"events equal actual registered STEP edges");
            if(slot_event)slots=slots+1;
            if(stopped)last_stop_at=cycle;
            for(m=0;m<4;m=m+1)begin
                if(en[m]==((POL>>m)&1) && !prev_enabled[m])enable_at[m]=cycle;
                if(dir[m]!=prev_dir[m])begin
                    check(!step[m] && !prev_step[m] && cycle-rise_at[m]>=Q[m*64+:64],"DIR hold/inactive");
                    dir_at[m]=cycle;
                end
                if(rising[m])begin
                    check(en[m]==((POL>>m)&1) && position_valid[m],"edge requires valid position/EN");
                    check(cycle-dir_at[m]>=S[m*64+:64] && cycle-enable_at[m]>=E[m*64+:64],"DIR/EN setup");
                    check(cycle-fall_at[m]>=L[m*64+:64],"minimum STEP low");
                    math_product=(cycle-rise_at[m])*{64'b0,RATE[m*64+:64]};
                    check(math_product>=100000000,"instantaneous maximum STEP rate");
                    check(dir[m]==expected_positive[m],"direction matches signed65 target delta");
                    model_next=$signed({model_pos[m][63],model_pos[m]})+(dir[m] ? 65'sd1 : -65'sd1);
                    check(model_next[64]==model_next[63],"no signed64 count overflow");
                    model_pos[m]=model_next[63:0];rise_at[m]=cycle;edges=edges+1;
                end
                if(!step[m] && prev_step[m])begin
                    check(cycle-rise_at[m]==H[m*64+:64],"exact STEP high width despite stop");fall_at[m]=cycle;
                end
                if(rebase_accepted && rebase_mask[m])model_pos[m]=$signed(rebase_position[m*64+:64]);
                check($signed(position[m*64+:64])===model_pos[m],"position follows only physical edges/rebase");
                if(en[m]!=((POL>>m)&1) && prev_enabled[m])begin
                    check(!step[m] && cycle-fall_at[m]>=L[m*64+:64] &&
                          cycle-rise_at[m]>=Q[m*64+:64],"EN release waits for pulse-safe state");
                    check(cycle-last_stop_at>=OFF[m*64+:64],"per-axis EN disable delay preserved");
                end
                if(done||stopped)check(!step[m] && cycle-fall_at[m]>=L[m*64+:64] &&
                    cycle-rise_at[m]>=Q[m*64+:64],"all lanes pulse-safe at group completion");
            end
            if(done)begin
                check(tracking && cycle-start_at==expected_cycles,"done exactly at duration boundary");
                check(expected_master==0 || expected_slot==expected_master,"all slots completed");
                for(m=0;m<4;m=m+1)if(expected_mask[m])
                    check(model_pos[m]==$signed(expected_target[m*64+:64]),"exact final absolute targets");
                tracking=0;
            end
            if(stopped)stops=stops+1;
            prev_step=step;prev_dir=dir;
            for(m=0;m<4;m=m+1)prev_enabled[m]=(en[m]==((POL>>m)&1));
        end
    end
    task tick;begin @(posedge clk);#2;end endtask
    task reset_axes;
        begin @(negedge clk);rst_n=0;rebase_req=0;enable_req=0;disable_req=0;
            open_req=0;cmd_valid=0;stop_req=0;underflow=0;fault=0;clear_fault=0;
            tick;tick;@(negedge clk);rst_n=1;repeat(30*SCALE)tick;end
    endtask
    task setup;
        input [255:0] base;input [63:0] id;
        begin reset_axes;
            @(negedge clk);rebase_position=base;rebase_mask=15;rebase_req=1;tick;
            check(rebase_accepted,"disabled group REBASE accepted");
            @(negedge clk);rebase_req=0;enable_mask=15;enable_req=1;tick;
            @(negedge clk);enable_req=0;open_req=1;open_session_id=id;tick;
            check(open_accepted,"session opens explicitly");
            @(negedge clk);open_req=0;cmd_session_id=id;repeat(15*SCALE)tick;
        end
    endtask
    task submit;
        input [255:0] targets;input [3:0] mask;input [63:0] duration;
        begin @(negedge clk);cmd_target=targets;cmd_mask=mask;duration_tick=duration;
            prepare_oracle;cmd_valid=1;tick;@(negedge clk);cmd_valid=0;end
    endtask
    task wait_idle;
        integer n;
        begin n=0;while(busy && n<2000)begin tick;n=n+1;end check(!busy,"bounded completion");end
    endtask
    task complete_point;
        input [255:0] targets;input [3:0] mask;input [63:0] duration;
        integer old_points,old_edges;
        begin old_points=points;old_edges=edges;submit(targets,mask,duration);wait_idle;
            if(oracle_ok)check(points==old_points+1 && session_valid,"feasible point completes preserving session");
            else check(points==old_points && edges==old_edges && !session_valid,"infeasible group has zero partial output");
        end
    endtask
    task guard_rejection;
        input [255:0] targets;input [3:0] mask;
        integer old_edges,old_points;
        begin old_edges=edges;old_points=points;submit(targets,mask,2*SCALE);
            oracle_ok=0;wait_idle;
            check(edges==old_edges && points==old_points && !session_valid,
                  "guard failure cancels whole group without partial output");end
    endtask
    integer j,k,kind,before_edges,before_points,before_stops;
    reg [255:0] snapshot,random_target;
    reg signed [63:0] random_lane;
    reg [3:0] random_mask;
    reg [63:0] random_duration;
    initial begin
      if(TEST_GROUP==0)begin
        setup(0,1);check(config_valid==15,"all timing lanes configured");
        check(default_config==0,"default unconfigured lanes cannot execute");
        check(invalid_config==0,"zero rate, H+L/guard overflow and EN guard overflow rejected");
        complete_point({64'sd2,-64'sd3,64'sd5,64'sd7},15,4*SCALE);
        complete_point({-64'sd1,64'sd0,-64'sd2,-64'sd3},15,6*SCALE);
        complete_point(position,15,1); // zero step dwell, exact 100-cycle duration
        complete_point({4{64'hdeadbeef}},0,1); // pure dwell ignores all targets
        random_target=position;random_target[63:0]=$signed(position[63:0])+1;
        complete_point(random_target,1,2*SCALE);
        @(negedge clk);rebase_req=1;tick;check(rejected,"enabled/session REBASE rejected");
        @(negedge clk);rebase_req=0;
        // At duration=1 tick, common guard and lane1 rate bound sharply limit N.
        setup(0,2);complete_point({64'd0,64'd0,64'd5,64'd5},3,1);
        setup(0,3);complete_point({64'd0,64'd0,64'd4,64'd4},3,1);
        setup(0,4);complete_point(1,1,0);
        setup(0,5);complete_point(1,1,64'hffffffffffffffff);
        setup({4{64'h8000000000000000}},6);
        complete_point({4{64'h7fffffffffffffff}},15,2);
        setup({4{64'h7fffffffffffffff}},7);
        complete_point({4{64'h8000000000000000}},15,2);
        setup({64'h8000000000000001,64'h7ffffffffffffffe,64'h8000000000000000,64'h7fffffffffffffff},8);
        complete_point({64'h8000000000000000,64'h7fffffffffffffff,64'h8000000000000001,64'h7ffffffffffffffe},15,2*SCALE);
        // Change the input payload during the 64-cycle preflight: the captured
        // counts, signs, mask and duration must remain a single atomic point.
        setup(0,9);before_points=points;
        submit({64'sd1,-64'sd2,64'sd4,64'sd5},15,2*SCALE);
        @(negedge clk);cmd_target={4{64'h7fffffffffffffff}};duration_tick=0;cmd_mask=0;
        wait_idle;check(points==before_points+1 && session_valid,"captured payload stable across preflight");
        // Selective disable cancels the group but only invalidates/releases its mask.
        before_stops=stops;@(negedge clk);disable_mask=4;disable_req=1;tick;
        @(negedge clk);disable_req=0;wait_idle;
        check(stops==before_stops+1 && position_valid==11 && (en^POL)==4,
              "partial disable preserves other lanes and cancels the group");
        @(negedge clk);open_req=1;open_session_id=10;tick;
        check(open_accepted,"new session after selective disable");
        @(negedge clk);open_req=0;cmd_session_id=10;
        guard_rejection(position,15); // disabled/invalid lane cannot participate
        @(negedge clk);rebase_req=1;rebase_mask=4;rebase_position=0;tick;
        check(rebase_accepted && position_valid==15,"only disabled lane may be rebased");
        @(negedge clk);rebase_req=0;enable_req=1;enable_mask=4;tick;
        @(negedge clk);enable_req=0;open_req=1;open_session_id=11;tick;
        check(open_accepted,"recovery still needs explicit new session");
        @(negedge clk);open_req=0;cmd_session_id=11;
        complete_point(0,15,4*SCALE);
        @(negedge clk);cmd_session_id=10;
        guard_rejection(1,1); // stale ID cannot execute in a new session
        disable_mask=15;
        // Largest legal duration exercises unsigned64 conversion, without
        // pretending to simulate centuries of dwell. Cancel immediately.
        setup(0,12);submit(0,0,64'd184467440737095516);
        check(oracle_ok && cmd_accepted,"largest legal duration accepted without truncation");
        @(negedge clk);stop_req=1;tick;@(negedge clk);stop_req=0;wait_idle;
        setup(0,13);complete_point(0,0,64'd184467440737095517);
        setup(0,14);submit({64'sd1,-64'sd2,64'sd4,64'sd5},15,2*SCALE);
        repeat(90)tick;before_edges=edges;before_stops=stops;
        @(negedge clk);fault=4;disable_req=1;disable_mask=1;tick;
        @(negedge clk);disable_req=0;wait_idle;repeat(30*SCALE)tick;
        check(stops==before_stops+1 && edges==before_edges && position_valid==14 &&
              (en^POL)==1,"persistent fault plus selective disable completes once");
        @(negedge clk);fault=0;clear_fault=1;tick;
        check(!session_valid && fault_latched==0 && (en^POL)==1,"clear does not recover disabled EN");
        @(negedge clk);clear_fault=0;disable_mask=15;
        for(j=0;j<100;j=j+1)begin
            setup(0,100+j);random_target=0;
            for(k=0;k<4;k=k+1)begin
                random_lane=$signed(($random & 32'h7fffffff)%31-15);
                random_target[k*64+:64]=random_lane;
            end
            random_mask=$random;random_duration=($random & 32'h7fffffff)%8+1;
            complete_point(random_target,random_mask,random_duration*SCALE);
        end
      end
        // Offsets include all 64 divide cycles, CHECK, common prelude, slots,
        // unequal-width pulse phases, tail and normal-completion idle.
        for(kind=0;kind<4;kind=kind+1)if(TEST_GROUP==kind+1)for(j=0;j<280*SCALE;j=j+1)begin
            safety_cases=safety_cases+1;
            setup(0,1000+kind*1000+j);
            submit({64'sd1,-64'sd2,64'sd4,64'sd5},15,2*SCALE);
            repeat(j)tick;before_edges=edges;before_stops=stops;
            @(negedge clk);
            case(kind)0:stop_req=1;1:underflow=1;2:fault=4'b0100;3:disable_req=1;endcase
            tick;check(!session_valid && edges==before_edges,"all axes cancel before a same-cycle edge");
            @(negedge clk);stop_req=0;underflow=0;disable_req=0;wait_idle;
            check(stops==before_stops+1,"group stopped exactly once");
            snapshot=position;repeat(30*SCALE)tick;
            check(position==snapshot && edges==before_edges,"late old motion never resumes");
            if(kind==3)check(position_valid==0 && en==(15^POL),"explicit all-axis disable invalidates/releases");
            else check(position_valid==15 && en==POL,"ordinary stop keeps EN and actual position");
            if(kind==2)begin
                @(negedge clk);clear_fault=1;tick;check(fault_latched!=0,"active source cannot clear");
                @(negedge clk);fault=0;tick;check(fault_latched==0 && !session_valid,"clear cannot reopen");
                @(negedge clk);clear_fault=0;
            end
            @(negedge clk);cmd_valid=1;tick;check(rejected,"cancelled-session command rejected");
            @(negedge clk);cmd_valid=0;
        end
        if(TEST_GROUP==5)for(j=0;j<280*SCALE;j=j+1)begin
            reset_cases=reset_cases+1;
            setup(0,10000+j);submit({64'sd1,-64'sd2,64'sd4,64'sd5},15,2*SCALE);repeat(j)tick;
            @(negedge clk);rst_n=0;#1;
            check(step==0 && en==(15^POL) && position_valid==0 && !session_valid,"asynchronous reset at every phase");
            tick;@(negedge clk);rst_n=1;repeat(30*SCALE)tick;
            check(position==0 && step==0 && !session_valid,"reset cannot auto-resume");
        end
        $display("PASS four checks=%0d points=%0d slots=%0d edges=%0d safety_offsets=%0d reset_offsets=%0d skew_cycles=0",
            checks,points,slots,edges,safety_cases,reset_cases);$finish;
    end
    initial begin #30000000;$display("FAIL four timeout");$fatal(1);end
endmodule
