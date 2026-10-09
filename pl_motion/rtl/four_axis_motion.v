`timescale 1ns/1ps
// Atomic single-point four-axis scheduler. Lane 0 occupies bits [63:0].
// Requests are synchronous strobes; fault is a level. No FIFO/END/PAUSE here.
module four_axis_motion #(
    parameter [255:0] STEP_HIGH_CYCLES=0, STEP_LOW_CYCLES=0,
    parameter [255:0] DIR_SETUP_CYCLES=0, DIR_HOLD_CYCLES=0,
    parameter [255:0] EN_SETUP_CYCLES=0, EN_DISABLE_CYCLES=0,
    parameter [255:0] MAX_STEP_HZ=0,
    parameter [3:0] EN_ACTIVE_LEVEL=4'b1111
)(
    input wire clk, rst_n,
    input wire rebase_req, input wire [3:0] rebase_mask,
    input wire [255:0] rebase_position,
    input wire enable_req, input wire [3:0] enable_mask,
    input wire disable_req, input wire [3:0] disable_mask,
    input wire open_req, input wire [63:0] open_session_id,
    input wire cmd_valid, input wire [63:0] cmd_session_id,
    input wire [3:0] cmd_mask, input wire [255:0] cmd_target,
    input wire [63:0] duration_tick,
    input wire stop_req, underflow, input wire [3:0] fault,
    input wire clear_fault,
    output reg [3:0] step, dir, output wire [3:0] en,
    output wire [255:0] position, output reg [3:0] position_valid,
    output reg [63:0] session_id, output reg session_valid,
    output reg [3:0] fault_latched, output wire [3:0] config_valid,
    output wire cmd_ready, busy,
    output reg cmd_accepted, rebase_accepted, open_accepted, rejected,
    output reg point_start, done, stopped, cancelled,
    output reg [3:0] pulse_event, output reg slot_event,
    output reg [63:0] slot_id
);
    localparam IDLE=0, DIVIDE=1, CHECK=2, RUN=3, DRAIN=4;
    reg [2:0] state;
    reg [3:0] enabled, disabling, moving, positive;
    reg signed [63:0] pos[0:3];
    reg [63:0] count[0:3], accumulator[0:3];
    reg [63:0] high_left[0:3], edge_age[0:3], low_age[0:3];
    reg [63:0] dir_age[0:3], en_age[0:3], off_left[0:3];
    wire [63:0] h[0:3], l[0:3], s[0:3], q[0:3], e[0:3], off[0:3], rate[0:3];
    genvar g;
    generate for(g=0;g<4;g=g+1)begin: lanes
        assign h[g]=STEP_HIGH_CYCLES[g*64+:64];
        assign l[g]=STEP_LOW_CYCLES[g*64+:64];
        assign s[g]=DIR_SETUP_CYCLES[g*64+:64];
        assign q[g]=DIR_HOLD_CYCLES[g*64+:64];
        assign e[g]=EN_SETUP_CYCLES[g*64+:64];
        assign off[g]=EN_DISABLE_CYCLES[g*64+:64];
        assign rate[g]=MAX_STEP_HZ[g*64+:64];
        assign position[g*64+:64]=pos[g];
        assign en[g]=enabled[g] ? EN_ACTIVE_LEVEL[g] : !EN_ACTIVE_LEVEL[g];
        assign config_valid[g]=h[g]>0 && l[g]>0 && rate[g]>0 &&
            ({1'b0,h[g]}+{1'b0,l[g]})<=65'h0ffffffffffffffff &&
            ({2'b0,q[g]}+{2'b0,s[g]}+66'd2)<=66'h0ffffffffffffffff &&
            e[g]<=64'hfffffffffffffffd && l[g]<=64'hfffffffffffffffd;
    end endgenerate
    wire safety=stop_req || underflow || (|fault) || disable_req;
    assign busy=(state!=IDLE) || (|disabling);
    assign cmd_ready=state==IDLE && !(|disabling) && session_valid &&
                     !(|fault_latched) && !safety;
    function [63:0] age_next;
        input [63:0] age;
        begin age_next=(&age) ? age : age+64'd1; end
    endfunction
    // Event resets age=0. Before the next edge, age+1 is elapsed cycles.
    function reached;
        input [63:0] age, minimum;
        begin reached=(minimum==0) || age>=minimum-64'd1; end
    endfunction
    reg all_safe;
    integer a;
    always @* begin
        all_safe=1;
        for(a=0;a<4;a=a+1)
            if(step[a] || !reached(low_age[a],l[a]) ||
                         !reached(edge_age[a],q[a])) all_safe=0;
    end

    // Whole-group capture/preflight: exact signed65 subtraction, unsigned64 N.
    reg [63:0] proposed_count[0:3];
    reg [3:0] proposed_positive, proposed_moving;
    reg [63:0] proposed_master, proposed_guard;
    reg [127:0] cycles_wide;
    reg basic_ok;
    reg signed [63:0] target_lane;
    reg signed [64:0] diff;
    reg [64:0] magnitude;
    reg [65:0] guard_lane;
    integer b;
    always @* begin
        cycles_wide={64'b0,duration_tick}*128'd100;
        basic_ok=duration_tick!=0 && cycles_wide[127:64]==0 &&
                 cmd_session_id==session_id && all_safe &&
                 (cmd_mask & ~enabled)==0 && (cmd_mask & ~position_valid)==0 &&
                 (cmd_mask & ~config_valid)==0;
        proposed_master=0;proposed_guard=0;
        proposed_positive=dir;proposed_moving=0;
        target_lane=0;diff=0;magnitude=0;guard_lane=0;
        for(b=0;b<4;b=b+1)begin
            proposed_count[b]=0;
            if(cmd_mask[b])begin
                target_lane=$signed(cmd_target[b*64+:64]);
                diff=$signed({target_lane[63],target_lane})-$signed({pos[b][63],pos[b]});
                magnitude=diff[64] ? -diff : diff;
                proposed_count[b]=magnitude[63:0];
                if(magnitude!=0)begin
                    proposed_moving[b]=1;proposed_positive[b]=!diff[64];
                    if(magnitude[63:0]>proposed_master)proposed_master=magnitude[63:0];
                    guard_lane={2'b0,q[b]}+{2'b0,s[b]};
                    if({2'b0,e[b]}>guard_lane)guard_lane={2'b0,e[b]};
                    if({2'b0,l[b]}>guard_lane)guard_lane={2'b0,l[b]};
                    guard_lane=guard_lane+66'd2;
                    if(guard_lane[65:64]!=0)basic_ok=0;
                    if(guard_lane[63:0]>proposed_guard)proposed_guard=guard_lane[63:0];
                end
            end
        end
        if(proposed_master!=0 && cycles_wide[63:0]<=proposed_guard)basic_ok=0;
    end

    reg [63:0] cycles, guard_cycles, master, quotient, remainder;
    reg [63:0] dividend, div_quotient;
    reg [64:0] div_remainder;
    reg [6:0] div_left;
    wire [64:0] trial={div_remainder[63:0],dividend[63]};
    wire div_bit=trial>={1'b0,master};
    wire [64:0] rem_next=div_bit ? trial-{1'b0,master} : trial;
    wire [63:0] quo_next={div_quotient[62:0],div_bit};
    reg feasible;
    reg [127:0] rate_product;
    integer c;
    always @* begin
        feasible=quotient!=0;rate_product=0;
        for(c=0;c<4;c=c+1)if(moving[c])begin
            rate_product={64'b0,quotient}*{64'b0,rate[c]};
            if({1'b0,quotient}<({1'b0,h[c]}+{1'b0,l[c]}) ||
                quotient<q[c] || rate_product<128'd100000000)feasible=0;
        end
    end

    reg [63:0] elapsed, next_slot, slot_index, time_remainder;
    wire slot_due=state==RUN && master!=0 && slot_index<master &&
                  elapsed+64'd1==next_slot;
    reg [3:0] emit;
    reg emission_ok;
    reg [64:0] sum_lane;
    reg signed [64:0] next_pos;
    reg [127:0] spacing_rate;
    integer d;
    always @* begin
        emit=0;emission_ok=1;sum_lane=0;next_pos=0;spacing_rate=0;
        for(d=0;d<4;d=d+1)begin
            sum_lane={1'b0,accumulator[d]}+{1'b0,count[d]};
            if(moving[d] && sum_lane>={1'b0,master})begin
                emit[d]=1;
                next_pos=$signed({pos[d][63],pos[d]})+(positive[d] ? 65'sd1 : -65'sd1);
                spacing_rate=({64'b0,edge_age[d]}+128'd1)*{64'b0,rate[d]};
                if(step[d] || !enabled[d] || !position_valid[d] || dir[d]!=positive[d] ||
                   !reached(low_age[d],l[d]) || !reached(dir_age[d],s[d]) ||
                   !reached(en_age[d],e[d]) || spacing_rate<128'd100000000 ||
                   next_pos[64]!=next_pos[63])emission_ok=0;
            end
        end
    end
    reg [64:0] sum_time, sum_axis;
    integer i;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            state<=IDLE;enabled<=0;disabling<=0;step<=0;dir<=4'b1111;
            position_valid<=0;session_valid<=0;session_id<=0;fault_latched<=0;
            moving<=0;positive<=4'b1111;cycles<=0;guard_cycles<=0;master<=0;
            quotient<=0;remainder<=0;dividend<=0;div_quotient<=0;
            div_remainder<=0;div_left<=0;elapsed<=0;next_slot<=0;
            slot_index<=0;time_remainder<=0;slot_id<=0;
            cmd_accepted<=0;rebase_accepted<=0;open_accepted<=0;rejected<=0;
            point_start<=0;done<=0;stopped<=0;cancelled<=0;pulse_event<=0;slot_event<=0;
            for(i=0;i<4;i=i+1)begin
                pos[i]<=0;count[i]<=0;accumulator[i]<=0;high_left[i]<=0;
                edge_age[i]<=0;low_age[i]<=0;dir_age[i]<=0;en_age[i]<=0;off_left[i]<=0;
            end
        end else begin
            cmd_accepted<=0;rebase_accepted<=0;open_accepted<=0;rejected<=0;
            point_start<=0;done<=0;stopped<=0;cancelled<=0;pulse_event<=0;slot_event<=0;
            fault_latched<=fault_latched|fault;
            if(clear_fault && !busy && !safety)fault_latched<=0;
            for(i=0;i<4;i=i+1)begin
                edge_age[i]<=age_next(edge_age[i]);dir_age[i]<=age_next(dir_age[i]);
                if(!step[i])low_age[i]<=age_next(low_age[i]);
                if(enabled[i])en_age[i]<=age_next(en_age[i]);
                if(step[i])begin
                    if(high_left[i]==1)begin step[i]<=0;low_age[i]<=0;high_left[i]<=0;end
                    else high_left[i]<=high_left[i]-64'd1;
                end
                if(disabling[i] && state==IDLE && all_safe && !disable_req)begin
                    if(off_left[i]==0)begin enabled[i]<=0;disabling[i]<=0;end
                    else off_left[i]<=off_left[i]-64'd1;
                end
            end
            if(safety)begin
                session_valid<=0;
                if(session_valid || state==DIVIDE || state==CHECK || state==RUN)cancelled<=1;
                if(state!=DRAIN && (session_valid || state!=IDLE || stop_req ||
                                   underflow || disable_req))state<=DRAIN;
                if(disable_req)begin
                    position_valid<=position_valid & ~disable_mask;
                    disabling<=disabling|disable_mask;
                    for(i=0;i<4;i=i+1)if(disable_mask[i])off_left[i]<=off[i];
                end
                if(cmd_valid || open_req || rebase_req || enable_req)rejected<=1;
            end else begin
                if((rebase_req && (open_req || enable_req || cmd_valid)) ||
                   (open_req && (enable_req || cmd_valid)) || (enable_req && cmd_valid))
                    rejected<=1;
                else if(rebase_req)begin
                    if(!busy && !session_valid && !(|fault_latched) && rebase_mask!=0 &&
                       (rebase_mask & enabled)==0)begin
                        for(i=0;i<4;i=i+1)if(rebase_mask[i])pos[i]<=$signed(rebase_position[i*64+:64]);
                        position_valid<=position_valid|rebase_mask;rebase_accepted<=1;
                    end else rejected<=1;
                end else if(enable_req)begin
                    if(!busy && !(|fault_latched) && enable_mask!=0 &&
                       (enable_mask & ~position_valid)==0 && (enable_mask & ~config_valid)==0)begin
                        enabled<=enabled|enable_mask;
                        for(i=0;i<4;i=i+1)if(enable_mask[i] && !enabled[i])en_age[i]<=0;
                    end else rejected<=1;
                end else if(open_req)begin
                    if(!busy && !session_valid && !(|fault_latched) &&
                       open_session_id!=0 && open_session_id!=session_id)begin
                        session_id<=open_session_id;session_valid<=1;open_accepted<=1;
                    end else rejected<=1;
                end else if(cmd_valid)begin
                    if(cmd_ready)begin
                        if(!basic_ok)begin rejected<=1;cancelled<=1;session_valid<=0;state<=DRAIN;end
                        else begin
                            cycles<=cycles_wide[63:0];guard_cycles<=proposed_guard;
                            master<=proposed_master;moving<=proposed_moving;positive<=proposed_positive;
                            for(i=0;i<4;i=i+1)count[i]<=proposed_count[i];
                            if(proposed_master==0)begin
                                state<=RUN;elapsed<=0;slot_index<=0;
                                cmd_accepted<=1;point_start<=1;
                            end else begin
                                dividend<=cycles_wide[63:0]-proposed_guard;
                                div_remainder<=0;div_quotient<=0;div_left<=64;state<=DIVIDE;
                            end
                        end
                    end else rejected<=1;
                end
                case(state)
                    DIVIDE:begin
                        dividend<={dividend[62:0],1'b0};div_remainder<=rem_next;
                        div_quotient<=quo_next;div_left<=div_left-1'b1;
                        if(div_left==1)begin quotient<=quo_next;remainder<=rem_next[63:0];state<=CHECK;end
                    end
                    CHECK:begin
                        if(!feasible)begin rejected<=1;cancelled<=1;session_valid<=0;state<=DRAIN;end
                        else begin
                            state<=RUN;elapsed<=0;next_slot<=guard_cycles;
                            slot_index<=0;time_remainder<=0;cmd_accepted<=1;point_start<=1;
                            for(i=0;i<4;i=i+1)begin
                                accumulator[i]<=master-count[i];
                                if(moving[i] && dir[i]!=positive[i])begin dir[i]<=positive[i];dir_age[i]<=0;end
                            end
                        end
                    end
                    RUN:begin
                        elapsed<=elapsed+64'd1;
                        if(slot_due)begin
                            if(!emission_ok)begin
                                state<=DRAIN;session_valid<=0;fault_latched<=4'b1111;cancelled<=1;
                            end else begin
                                slot_event<=1;slot_id<=slot_index;slot_index<=slot_index+64'd1;
                                sum_time={1'b0,time_remainder}+{1'b0,remainder};
                                if(sum_time>={1'b0,master})begin
                                    time_remainder<=sum_time-{1'b0,master};next_slot<=next_slot+quotient+64'd1;
                                end else begin time_remainder<=sum_time[63:0];next_slot<=next_slot+quotient;end
                                for(i=0;i<4;i=i+1)if(moving[i])begin
                                    sum_axis={1'b0,accumulator[i]}+{1'b0,count[i]};
                                    accumulator[i]<=emit[i] ? sum_axis-{1'b0,master} : sum_axis[63:0];
                                    if(emit[i])begin
                                        step[i]<=1;pulse_event[i]<=1;edge_age[i]<=0;high_left[i]<=h[i];
                                        pos[i]<=pos[i]+(positive[i] ? 64'sd1 : -64'sd1);
                                    end
                                end
                            end
                        end
                        if(elapsed+64'd1==cycles)begin
                            if(all_safe && (master==0 || slot_index==master))begin state<=IDLE;done<=1;end
                            else begin state<=DRAIN;session_valid<=0;fault_latched<=4'b1111;cancelled<=1;end
                        end
                    end
                    default:begin end
                endcase
            end
            if(state==DRAIN && all_safe)begin state<=IDLE;stopped<=1;end
        end
    end
endmodule
