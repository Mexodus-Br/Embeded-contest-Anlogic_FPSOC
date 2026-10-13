`timescale 1ns/1ps
module tb_multirate_profile;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,enable=0,rx=1,cv=0;
 reg [63:0] time_us=64'd900000;
 integer div=0,cycles=0;
 always @(posedge clk) begin cycles=cycles+1;if(div==99) begin div=0;time_us<=time_us+1;end else div=div+1;end
 reg [159:0] periods={32'd200000,32'd200000,32'd20000,32'd100000,32'd20000};
 wire tx,de,rv,busy,cr,ca,ce;
 wire [7:0] cerr;
 wire [255:0] data;
 wire [31:0] load,revision,seq,drop,ok,err,ignored,level,be,ss,st,sv,sm,sl,nb;
 wire [159:0] active;wire [4:0] am;wire [9:0] offline;
 wire [7:0] nf;wire [63:0] nc;
 wire legacy_ready,legacy_rejected;wire [7:0] legacy_error;
 rs485_multirate legacy_budget(.clk(clk),.rst_n(rst_n),.enable(1'b0),.time_us(time_us),.rx(1'b1),
 .cfg_valid(cv),.cfg_ready(legacy_ready),.cfg_period_us(periods),.cfg_mask(5'd31),
 .cfg_rejected(legacy_rejected),.cfg_error(legacy_error),.record_ready(1'b1),.debug_task(6'd0),.debug_node(4'd0));
 reg saw_legacy_reject=0;
 always @(posedge clk) if(legacy_rejected) begin
  if(legacy_error!=2) $fatal(1,"legacy guard rejection reason");saw_legacy_reject=1;
 end
 rs485_multirate #(.NORMAL_CYCLES(100000),.POLL_CYCLES(100000)) dut(
 .clk(clk),.rst_n(rst_n),.enable(enable),.time_us(time_us),.rx(rx),.tx(tx),.de(de),.busy(busy),
 .cfg_valid(cv),.cfg_ready(cr),.cfg_period_us(periods),.cfg_mask(5'd31),.cfg_applied(ca),.cfg_rejected(ce),.cfg_error(cerr),
 .cfg_revision(revision),.cfg_apply_sequence(seq),.active_period_us(active),.active_mask(am),.config_load_ppm(load),
 .record_ready(1'b1),.record_valid(rv),.record_data(data),.fifo_level(level),.dropped(drop),.accepted(ok),.errors(err),.ignored_rx(ignored),
 .bus_busy_events(be),.node_offline(offline),.debug_task(6'd0),.debug_node(4'd0),.stat_scheduled(ss),.stat_sent(st),.stat_valid(sv),.stat_missed(sm),.stat_max_lateness_us(sl),
 .node_failure_streak(nf),.node_cooldown_until_us(nc),.node_backoff_entries(nb));
 integer counts[0:14],records=0,i,j,rise,stop;
 reg [63:0] first_time=0;
 always @(posedge de) begin rise=cycles;if(first_time==0) first_time=time_us;end
 task ticks;input integer n;begin repeat(n) @(negedge clk);end endtask
 task read_byte;output [7:0] b;integer j;
  begin ticks(1302);for(j=0;j<8;j=j+1) begin b[j]=tx;ticks(868);end if(tx!==1) $fatal(1,"stop");ticks(434);end
 endtask
 task send_byte;input [7:0] b;integer j;
  begin if(de) $fatal(1,"half-duplex overlap");rx=0;ticks(868);
   for(j=0;j<8;j=j+1) begin rx=b[j];ticks(868);end rx=1;ticks(868);end
 endtask
 function integer data_len;input [7:0] q;
  begin case(q) 8'h30:data_len=6;8'h33:data_len=4;8'h39:data_len=2;8'h3a,8'h3e:data_len=1;default:data_len=0;endcase end
 endfunction
 reg [7:0] a,c,k,check,b;integer len,ix;
 initial forever begin
  @(negedge tx);if(cycles-rise<1000) $fatal(1,"DE pre");
  read_byte(a);@(negedge tx);read_byte(c);@(negedge tx);read_byte(k);stop=cycles;
  if(a<8'he0 || a>8'he2 || data_len(c)==0 || k!=((a+c)&255)) $fatal(1,"request whitelist/checksum");
  @(negedge de);if(cycles-stop<1000) $fatal(1,"DE true stop hold");
  ticks(2000);check=a;send_byte(a);len=data_len(c);
  for(ix=0;ix<len;ix=ix+1) begin b=ix+1;send_byte(b);check=check+b;end send_byte(check);
 end
 always @(posedge clk) if(rv) begin
  if(data[231:224]!=0 || data[215:208]!=data_len(data[239:232]) || data[175:112]>data[111:48] || data[111:48]>time_us) $fatal(1,"valid profile record");
  case(data[239:232]) 8'h30:j=0;8'h33:j=1;8'h39:j=2;8'h3a:j=3;8'h3e:j=4;default:$fatal(1,"query");endcase
  counts[(data[247:240]-8'he0)*5+j]=counts[(data[247:240]-8'he0)*5+j]+1;records=records+1;
 end
 initial begin
  for(i=0;i<15;i=i+1) counts[i]=0;
  ticks(10);rst_n=1;wait(cr && legacy_ready);ticks(1);cv=1;ticks(1);cv=0;wait(ca || ce);
  if(ce || load>750000 || load<710000) $fatal(1,"real profile admission load=%0d",load);
  enable=1;wait(first_time!=0);wait(time_us-first_time>=100000);enable=0;wait(!busy);ticks(10);
  for(i=0;i<15;i=i+1) begin
   case(i%5) 0,2:if(counts[i]<4 || counts[i]>7) $fatal(1,"50Hz profile");
    1:if(counts[i]<1 || counts[i]>3) $fatal(1,"10Hz profile");
    3,4:if(counts[i]<1 || counts[i]>2) $fatal(1,"5Hz profile");endcase
   $display("PROFILE task=%0d valid=%0d over 100ms plus drain",i,counts[i]);
  end
  if(err || drop || offline || be || !saw_legacy_reject) $fatal(1,"profile errors or legacy overload not rejected");
  $display("PROFILE admission ppm=%0d records=%0d task0 missed=%0d max_lateness_us=%0d",load,records,sm,sl);
  $display("PASS multirate profile 100MHz/115200, 50/10/50/5/5Hz, DE full stop");$finish;
 end
 initial begin #160000000;$fatal(1,"profile watchdog");end
endmodule
