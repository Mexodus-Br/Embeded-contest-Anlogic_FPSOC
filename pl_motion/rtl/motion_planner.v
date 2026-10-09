`timescale 1ns/1ps
module motion_planner #(
    parameter [255:0] STEP_HIGH_CYCLES=0, STEP_LOW_CYCLES=0,
    parameter [255:0] DIR_SETUP_CYCLES=0, DIR_HOLD_CYCLES=0,
    parameter [255:0] EN_SETUP_CYCLES=0, EN_DISABLE_CYCLES=0,
    parameter [255:0] MAX_STEP_HZ=0,
    parameter [3:0] EN_ACTIVE_LEVEL=4'b1111
)(
 input wire clk,rst_n,cancel,
 input wire req_valid,output wire req_ready,output wire busy,
 input wire [255:0] base_position,target_position,
 input wire [3:0] axis_mask,
 input wire [63:0] duration_tick,request_session,
 input wire [31:0] request_sequence,input wire request_end,
 output wire plan_valid,input wire plan_ready,
 output wire [1196:0] plan_data,output reg error
);
localparam IDLE=0,DIVIDE=1,CHECK=2,HOLD=3;
reg [1:0] state;
wire [63:0] h[0:3],l[0:3],s[0:3],q[0:3],e[0:3],rate[0:3];
wire [3:0] config_valid;
    genvar g;
    generate for(g=0;g<4;g=g+1)begin: lanes
        assign h[g]=STEP_HIGH_CYCLES[g*64+:64];
        assign l[g]=STEP_LOW_CYCLES[g*64+:64];
        assign s[g]=DIR_SETUP_CYCLES[g*64+:64];
        assign q[g]=DIR_HOLD_CYCLES[g*64+:64];
        assign e[g]=EN_SETUP_CYCLES[g*64+:64];
        assign rate[g]=MAX_STEP_HZ[g*64+:64];
        assign config_valid[g]=h[g]>0 && l[g]>0 && rate[g]>0 &&
            ({1'b0,h[g]}+{1'b0,l[g]})<=65'h0ffffffffffffffff &&
            ({2'b0,q[g]}+{2'b0,s[g]}+66'd2)<=66'h0ffffffffffffffff &&
            e[g]<=64'hfffffffffffffffd && l[g]<=64'hfffffffffffffffd;
    end endgenerate
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
                 (axis_mask & ~config_valid)==0;
        proposed_master=0;proposed_guard=0;
        proposed_positive=0;proposed_moving=0;
        target_lane=0;diff=0;magnitude=0;guard_lane=0;
        for(b=0;b<4;b=b+1)begin
            proposed_count[b]=0;
            if(axis_mask[b])begin
                target_lane=$signed(target_position[b*64+:64]);
                diff=$signed({target_lane[63],target_lane})-$signed({base_position[b*64+63],base_position[b*64+:64]});
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

reg [255:0] counts,base_saved,endpoint;
reg [3:0] moving,positive,mask_saved;
reg [63:0] sid;
reg [31:0] seq;
reg last;
assign req_ready=state==IDLE && !cancel;
assign busy=state!=IDLE;
assign plan_valid=state==HOLD && !cancel;
assign plan_data={base_saved,endpoint,counts,positive,moving,master,guard_cycles,cycles,quotient,remainder,sid,seq,last,mask_saved};
integer i;
always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin
  state<=IDLE;error<=0;cycles<=0;guard_cycles<=0;master<=0;quotient<=0;remainder<=0;
  dividend<=0;div_quotient<=0;div_remainder<=0;div_left<=0;
  counts<=0;base_saved<=0;endpoint<=0;moving<=0;positive<=0;mask_saved<=0;sid<=0;seq<=0;last<=0;
 end else begin
  error<=0;
  if(cancel)state<=IDLE;
  else case(state)
   IDLE:if(req_valid)begin
    if(!basic_ok)error<=1;
    else begin
     base_saved<=base_position;endpoint<=base_position;
     for(i=0;i<4;i=i+1)begin
      counts[i*64+:64]<=proposed_count[i];
      if(axis_mask[i])endpoint[i*64+:64]<=target_position[i*64+:64];
     end
     moving<=proposed_moving;positive<=proposed_positive;mask_saved<=axis_mask;
     sid<=request_session;seq<=request_sequence;last<=request_end;
     cycles<=cycles_wide[63:0];guard_cycles<=proposed_guard;master<=proposed_master;
     if(proposed_master==0)begin quotient<=0;remainder<=0;state<=HOLD;end
     else begin dividend<=cycles_wide[63:0]-proposed_guard;div_remainder<=0;div_quotient<=0;div_left<=64;state<=DIVIDE;end
    end
   end
   DIVIDE:begin
    dividend<={dividend[62:0],1'b0};div_remainder<=rem_next;div_quotient<=quo_next;div_left<=div_left-1'b1;
    if(div_left==1)begin quotient<=quo_next;remainder<=rem_next[63:0];state<=CHECK;end
   end
   CHECK:if(feasible)state<=HOLD;else begin error<=1;state<=IDLE;end
   HOLD:if(plan_ready)state<=IDLE;
  endcase
 end
end
endmodule
