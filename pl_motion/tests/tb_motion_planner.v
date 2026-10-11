`timescale 1ns/1ps
module tb_motion_planner;
 localparam [255:0] RATES={64'd3000000,64'd7000000,64'd10000000,64'd100000000};
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cancel=0,req_valid=0,plan_ready=0;
 reg [255:0] base=0,target=0;reg [3:0] mask=15;
 reg [63:0] duration=2,sid=11;reg [31:0] seq=0;reg last=1;
 wire req_ready,valid,error;wire [1196:0] data;
 motion_planner #(.STEP_HIGH_CYCLES({4{64'd3}}),.STEP_LOW_CYCLES({4{64'd2}}),
  .DIR_SETUP_CYCLES({4{64'd4}}),.DIR_HOLD_CYCLES({4{64'd7}}),
  .EN_SETUP_CYCLES({4{64'd5}}),.MAX_STEP_HZ(RATES)) dut(
  .clk(clk),.rst_n(rst_n),.cancel(cancel),.req_valid(req_valid),.req_ready(req_ready),
  .base_position(base),.target_position(target),.axis_mask(mask),.duration_tick(duration),
  .request_session(sid),.request_sequence(seq),.request_end(last),.plan_valid(valid),
  .plan_ready(plan_ready),.plan_data(data),.error(error));
 wire [255:0] pb,pe,counts;wire [3:0] positive,moving,pm;
 wire [63:0] master,guard,cycles,quotient,remainder,ps;wire [31:0] pq;wire pl;
 assign {pb,pe,counts,positive,moving,master,guard,cycles,quotient,remainder,ps,pq,pl,pm}=data;
 localparam NONZERO_LATENCY=71,ZERO_LATENCY=6;
 integer checks=0,i,n;
 reg [1196:0] snapshot;
 integer seed=1701,a,k,cycle_number=0,captured_at;
 always @(posedge clk)cycle_number=cycle_number+1;
 reg [255:0] reference_counts,reference_target,reference_base,reference_endpoint;
 reg [63:0] reference_master,reference_cycles,reference_q,reference_r;
 reg [3:0] reference_mask,reference_positive,reference_moving;
 reg signed [64:0] reference_delta;
 reg [127:0] reference_product;
 reg expected_ok;
 task check;input condition;begin checks=checks+1;if(condition!==1'b1)$fatal(1,"planner check %0d",checks);end endtask
 task tick;begin @(posedge clk);#2;end endtask
 task request;begin @(negedge clk);req_valid=1;tick;@(negedge clk);req_valid=0;end endtask
 initial begin
  tick;@(negedge clk);rst_n=1;
  target={64'd0,-64'sd3,64'd5,64'd7};request;
  target=0;base={4{64'd99}};mask=0;duration=0;sid=999;seq=42;last=0;
  n=0;while(!valid && n<NONZERO_LATENCY+3)begin tick;n=n+1;end
  check(valid && n==NONZERO_LATENCY);check(pb==0 && pe=={64'd0,-64'sd3,64'd5,64'd7} && counts=={64'd0,64'd3,64'd5,64'd7});
  check(positive[2:0]==3 && moving==7 && master==7 && guard==13 && cycles==200);
  check(quotient==26 && remainder==5 && ps==11 && pq==0 && pl && pm==15);
  snapshot=data;target={4{64'hffffffffffffffff}};duration=0;base={4{64'd1}};
  repeat(9)begin tick;check(valid && data==snapshot && !req_ready);end
  @(negedge clk);plan_ready=1;tick;@(negedge clk);plan_ready=0;check(req_ready);
  base=0;target=0;mask=0;duration=1;sid=11;seq=0;last=1;request;repeat(ZERO_LATENCY)tick;check(valid && master==0 && cycles==100 && pb==pe);
  @(negedge clk);cancel=1;tick;@(negedge clk);cancel=0;#1;check(req_ready && !valid);
  mask=15;duration=2;
  for(i=0;i<NONZERO_LATENCY+5;i=i+1)begin
   target={64'd0,-64'sd3,64'd5,64'd7};request;repeat(i)tick;
   @(negedge clk);cancel=1;tick;check(!valid);@(negedge clk);cancel=0;
   repeat(NONZERO_LATENCY+5)tick;check(req_ready && !valid);
  end
  duration=0;request;repeat(ZERO_LATENCY)tick;check(error && !valid);
  duration=64'hffffffffffffffff;request;repeat(ZERO_LATENCY)tick;check(error && !valid);
  base={4{64'h8000000000000000}};target={4{64'h7fffffffffffffff}};duration=2;request;
  n=0;while(!error && n<NONZERO_LATENCY+3)begin tick;n=n+1;end check(error && !valid);
  // Independent arithmetic reference retains multiplication instead of the
  // new ceil(rate) implementation; mixed non-divisible rates exercise rounding.
  for(k=0;k<120;k=k+1)begin
   base=0;mask=$random(seed);duration=1+($unsigned($random(seed))%4);
   for(a=0;a<4;a=a+1)target[a*64+:64]=($random(seed)%12);
   sid=64'd800+k;seq=k;last=k%2;
   reference_base=base;reference_target=target;reference_endpoint=base;reference_mask=mask;
   reference_counts=0;reference_master=0;reference_moving=0;reference_positive=0;
   for(a=0;a<4;a=a+1)if(mask[a])begin
    reference_endpoint[a*64+:64]=target[a*64+:64];
    reference_delta=$signed({target[a*64+63],target[a*64+:64]})-$signed({base[a*64+63],base[a*64+:64]});
    reference_counts[a*64+:64]=reference_delta[64] ? -reference_delta : reference_delta;
    reference_moving[a]=reference_delta!=0;reference_positive[a]=reference_delta>0;
    if(reference_counts[a*64+:64]>reference_master)reference_master=reference_counts[a*64+:64];
   end
   reference_cycles=duration*100;reference_q=0;reference_r=0;expected_ok=1;
   if(reference_master!=0)begin
    reference_q=(reference_cycles-13)/reference_master;reference_r=(reference_cycles-13)%reference_master;
    for(a=0;a<4;a=a+1)if(reference_moving[a])begin
     reference_product={64'b0,reference_q}*{64'b0,RATES[a*64+:64]};
     if(reference_q<7 || reference_product<128'd100000000)expected_ok=0;
    end
   end
   request;target=0;base=0;duration=0;mask=0;sid=0;seq=0;last=0;
   n=0;while(!valid && !error && n<NONZERO_LATENCY+3)begin tick;n=n+1;end
   check(n==(reference_master==0 ? ZERO_LATENCY : NONZERO_LATENCY));
   check(expected_ok ? valid && !error : error && !valid);
   if(expected_ok)begin
    check(pb==reference_base && pe==reference_endpoint && counts==reference_counts);
    check(moving==reference_moving && positive==reference_positive && pm==reference_mask);
    check(master==reference_master && cycles==reference_cycles && quotient==reference_q && remainder==reference_r);
    check(ps==800+k && pq==k && pl==(k%2));
    @(negedge clk);plan_ready=1;tick;@(negedge clk);plan_ready=0;
   end
  end
  // Measure request initiation interval with immediate output consumption.
  base=0;target=1;mask=1;duration=1;sid=123;seq=100;last=0;request;captured_at=cycle_number;
  repeat(NONZERO_LATENCY)tick;check(valid && ps==123 && pq==100);
  @(negedge clk);plan_ready=1;tick;
  @(negedge clk);plan_ready=0;req_valid=1;seq=101;tick;
  check(cycle_number-captured_at==NONZERO_LATENCY+2);
  @(negedge clk);req_valid=0;repeat(NONZERO_LATENCY)tick;check(valid && pq==101);
  @(negedge clk);plan_ready=1;tick;
  @(negedge clk);plan_ready=0;req_valid=1;mask=0;seq=102;tick;captured_at=cycle_number;
  @(negedge clk);req_valid=0;repeat(ZERO_LATENCY)tick;check(valid && pq==102);
  @(negedge clk);plan_ready=1;tick;
  @(negedge clk);plan_ready=0;req_valid=1;seq=103;tick;check(cycle_number-captured_at==ZERO_LATENCY+2);
  @(negedge clk);req_valid=0;repeat(ZERO_LATENCY)tick;check(valid && pq==103);
  $display("PASS planner checks=%0d cancel_offsets=%0d nonzero_latency=%0d zero_latency=%0d nonzero_II=73 zero_II=8",checks,NONZERO_LATENCY+5,NONZERO_LATENCY,ZERO_LATENCY);$finish;
 end
endmodule
