`timescale 1ns/1ps
module tb_cache_diff;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,event_valid=0,snapshot_capture=0;
 reg [63:0] time_us=0;reg [31:0] collector_generation=0,event_generation=0,event_revision=0;
 reg [255:0] event_raw=0;reg [159:0] active_period_us={5{32'd50000}};reg [4:0] active_mask=31;
 reg [8:0] snapshot_word=0;wire [31:0] actual,expected,errors,ref_errors;
 rs485_latest_cache dut(clk,rst_n,time_us,collector_generation,event_valid,event_raw,event_generation,event_revision,active_period_us,active_mask,snapshot_capture,snapshot_word,actual,errors);
 rs485_latest_cache_baseline reference_cache(clk,rst_n,time_us,collector_generation,event_valid,event_raw,event_generation,event_revision,active_period_us,active_mask,snapshot_capture,snapshot_word,expected,ref_errors);
 integer checks=0,seed=20261015,r,n,q,k;reg [7:0] code,len,status;reg [47:0] payload;
 task step;begin @(posedge clk);#1;if(errors!==ref_errors) $fatal(1,"parse count");checks=checks+1;@(negedge clk);end endtask
 task compare_all;
  integer w;begin
   // Addresses continue changing while all source inputs can change independently.
   for(w=0;w<512;w=w+1) begin snapshot_word=w;#1;
    if(actual!==expected) $fatal(1,"cache difference word=%0d got=%h expected=%h",w,actual,expected);
    checks=checks+1;
   end
  end
 endtask
 task capture;begin snapshot_capture=1;step;snapshot_capture=0;compare_all;end endtask
 task make_event;input integer node,query,variant;begin
  case(query) 0:begin code='h30;len=6;end 1:begin code='h33;len=4;end
   2:begin code='h39;len=2;end 3:begin code='h3a;len=1;end default:begin code='h3e;len=1;end endcase
  status=0;
  case(variant%8)
   0:payload=0;1:payload=48'h800000008000;2:payload=48'h7fffffffffff;
   3:payload=48'hffffffffffff;4:payload=1;5:payload=2;6:payload='h80;
   default:begin status=3;len=0;payload=0;end
  endcase
  if(variant%8==1 && query==1) payload=48'h000080000000;
  if(variant%8==2 && query==1) payload=48'h00007fffffff;
  if(variant%8==2 && query==2) payload=48'h000000007fff;
  if(len<6) payload=payload & (48'hffffffffffff >> ((6-len)*8));
  event_raw={8'd1,8'he0+node[7:0],code,status,8'd1,len,event_revision,time_us-64'd10,time_us,payload};
  event_generation=collector_generation;event_valid=1;
 end endtask
 initial begin
  if($value$plusargs("seed=%d",seed)) begin end
  repeat(3) step;rst_n=1;step;capture; // initialized diagnostics including unseen rows
  for(k=0;k<8;k=k+1) begin
   for(n=0;n<3;n=n+1) for(q=0;q<5;q=q+1) begin make_event(n,q,k);step;event_valid=0;end
   capture;
  end
  // Same-edge event/capture observes previous values; config and generation races.
  active_period_us={5{32'd1000}};time_us=100;make_event(0,0,1);step;event_valid=0;
  time_us=100+64'd99999;capture;time_us=time_us+1;capture; // floor-1 / floor
  active_period_us={5{32'd100000}};time_us=100+64'd299999;capture;time_us=time_us+1;capture; // 3*period-1 / limit
  make_event(0,0,3);capture;event_valid=0;
  time_us=64'hfffffffffffffff0;make_event(2,2,1);step;event_valid=0;time_us=24;capture;
  active_period_us={5{32'hffffffff}};active_mask=0;capture;
  collector_generation=1;make_event(0,3,4);capture;event_valid=0;step;capture;
  for(k=0;k<100;k=k+1) begin
   r=$random(seed);time_us={r,$random(seed)};event_revision=k;
   active_mask=$random(seed);active_period_us={$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
   for(n=0;n<12;n=n+1) begin r=$random(seed)&32'h7fffffff;make_event(r%3,(r/3)%5,r%8);
    if(n==2) event_raw[255:248]=3; // malformed version
    if(n==3) event_generation=collector_generation+1;
    if(n==4) event_raw[215:208]=7;
    step;event_valid=0;
   end
   capture;
   // Snapshot cannot follow post-capture time/config/gen or continuous events.
   collector_generation=collector_generation+1;time_us=~time_us;active_mask=~active_mask;
   active_period_us=0;make_event(1,4,5);step;step;event_valid=0;compare_all;
  end
  // Saturation is the same on the update boundary.
  dut.updates[0]=32'hfffffffe;reference_cache.updates[0]=32'hfffffffe;
  make_event(0,0,1);step;step;step;event_valid=0;capture;
  dut.parse_errors=32'hfffffffe;reference_cache.parse_errors=32'hfffffffe;
  make_event(0,0,1);event_raw[255:248]=3;step;step;event_valid=0;capture;
  rst_n=0;snapshot_capture=1;step;compare_all;rst_n=1;step;snapshot_capture=0;compare_all;capture;
  $display("PASS cache differential checks=%0d all512words signed/enum/failure/atomic/gen/config/wrap/saturation",checks);$finish;
 end
 initial begin #10000000;$fatal(1,"diff watchdog");end
endmodule
