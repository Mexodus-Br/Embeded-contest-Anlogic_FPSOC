`timescale 1ns/1ps
// Behavioral slave deliberately decodes line timing, not the DUT RX implementation.
module tb_multirate;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,enable=0,ready=1,slave_line=1,echo=0;
 reg [4:0] mask=31;
 reg [63:0] time_us=64'd100000;
 integer time_div=0;
 always @(posedge clk) if(time_div==99) begin time_div<=0;time_us<=time_us+1;end else time_div<=time_div+1;
 wire tx,de,valid,busy;
 wire rx=(echo && de)?tx:slave_line;
 wire [255:0] data;
 wire [31:0] dropped,accepted,errors,ignored,level;
 reg cfg_valid=0;reg [159:0] periods=0;
 wire cfg_ready,applied,rejected;wire [7:0] cfg_error;
 wire [31:0] revision,apply_sequence,load;
 wire [159:0] active_periods;wire [4:0] active_mask;
 wire [31:0] bus_events,scheduled,sent,good,missed,max_late,backoffs;
 wire [9:0] offline;reg [5:0] dt=0;reg [3:0] dn=0;
 wire [7:0] streak;wire [63:0] cooldown;
 rs485_multirate #(.BAUD(5000000),.POLL_CYCLES(900),.TIMEOUT_CYCLES(5000),
  .INTERBYTE_CYCLES(600),.PRE_CYCLES(40),.POST_CYCLES(40),.TURN_CYCLES(40),.QUIET_CYCLES(800),.FIFO_DEPTH(8))
 dut(.clk(clk),.rst_n(rst_n),.enable(enable),.time_us(time_us),.rx(rx),.tx(tx),.de(de),.busy(busy),
 .cfg_valid(cfg_valid),.cfg_ready(cfg_ready),.cfg_period_us(periods),.cfg_mask(mask),.cfg_applied(applied),.cfg_rejected(rejected),
 .cfg_error(cfg_error),.cfg_revision(revision),.cfg_apply_sequence(apply_sequence),.active_period_us(active_periods),.active_mask(active_mask),.config_load_ppm(load),
 .record_ready(ready),.record_valid(valid),.record_data(data),.fifo_level(level),.dropped(dropped),.accepted(accepted),.errors(errors),.ignored_rx(ignored),
 .bus_busy_events(bus_events),.node_offline(offline),.debug_task(dt),.debug_node(dn),.stat_scheduled(scheduled),.stat_sent(sent),.stat_valid(good),.stat_missed(missed),.stat_max_lateness_us(max_late),
 .node_failure_streak(streak),.node_cooldown_until_us(cooldown),.node_backoff_entries(backoffs));
 always @(posedge clk) if(rst_n && applied && busy) $fatal(1,"configuration applied in transaction");
 reg protected=0;
 integer cycles=0;
 always @(posedge clk) cycles<=cycles+1;
 // Independent continuous STP model plus untouched reference, even during reset.
 reg step=0,step_ref=0;integer phase=0,ref_phase=0,step_edges=0;
 always @(posedge clk) begin
  if(phase==16) begin phase<=0;step<=~step;step_edges<=step_edges+1;end else phase<=phase+1;
  if(ref_phase==16) begin ref_phase<=0;step_ref<=~step_ref;end else ref_phase<=ref_phase+1;
  if(step!==step_ref || phase!==ref_phase) $fatal(1,"serial influenced independent STP");
 end
 integer rec_count=0,requests=0,mode=0,first_fault=0;
 reg [255:0] records[0:2047];
 reg [7:0] seen_addr[0:2047],seen_cmd[0:2047];
 integer request_cycle[0:2047];
 always @(posedge clk) if(rst_n && valid && ready) begin
  records[rec_count]=data;rec_count=rec_count+1;
  if(data[255:248]!=1) $fatal(1,"record version");
  if($signed(data[111:48]-data[175:112])<0 || $signed(time_us-data[111:48])<0) $fatal(1,"timestamps");
  if(data[231:224]!=0 && data[47:0]!=0) $fatal(1,"partial error payload published");
 end
 integer de_rise,last_stop,release_cycle;
 always @(posedge de) de_rise=cycles;
 always @(negedge de) if(rst_n && requests!=0) begin
  if(cycles-last_stop<40) $fatal(1,"DE released before full stop plus hold");
  if(tx!==1) $fatal(1,"DE released with TX low");
  release_cycle=cycles;
 end
 task ticks;input integer n;begin repeat(n) @(negedge clk);end endtask
 task read_byte;
  output [7:0] b;integer j;
  begin
   // Caller is positioned at start edge. Center of data bit 0 = 1.5 bits.
   ticks(30);for(j=0;j<8;j=j+1) begin b[j]=tx;ticks(20);end
   if(rst_n && tx!==1) $fatal(1,"master stop framing");
   ticks(10);last_stop=cycles;
  end
 endtask
 task send_byte;
  input [7:0] b;input bad_stop;integer j;
  begin
   if(de) $fatal(1,"slave transmit while master DE active");
   slave_line=0;ticks(20);
   for(j=0;j<8;j=j+1) begin slave_line=b[j];ticks(20);end
   slave_line=!bad_stop;ticks(20);slave_line=1;
  end
 endtask
 function integer data_len;input [7:0] cmd;
  begin case(cmd) 8'h30:data_len=6;8'h33:data_len=4;8'h39:data_len=2;8'h3a,8'h3e:data_len=1;default:data_len=0;endcase end
 endfunction
 function [7:0] value_byte;input integer j,len;input [7:0] addr,cmd;
  begin if(len==1) value_byte=(cmd==8'h3e)?(protected?1:2):1;else value_byte=(j==0)?8'hff:(addr+cmd+j);end
 endfunction
 task response;
  input [7:0] addr,cmd;input integer kind;
  integer j,len;reg [7:0] check,b;
  begin
   len=data_len(cmd);check=(kind==4)?8'he9:addr;
   send_byte(check,kind==2);
   if(kind!=7 && kind!=2) begin
    for(j=0;j<len;j=j+1) begin b=value_byte(j,len,addr,cmd);send_byte(b,0);check=check+b;end
    send_byte((kind==1)?check+1'b1:check,0);
   end
  end
 endtask
 reg [7:0] a,c,k;integer chosen,gen=0,local_gen,req_id;
 initial forever begin
  @(negedge tx);
  if(rst_n && de) begin
   local_gen=gen;read_byte(a);
   @(negedge tx);read_byte(c);
   @(negedge tx);read_byte(k);
   if(rst_n && local_gen==gen) begin
    if(data_len(c)==0 || a<8'he0 || a>8'he2 || k!=((a+c)&255)) $fatal(1,"illegal/writing request %h %h %h",a,c,k);
    if(cycles-de_rise<40+600) $fatal(1,"DE pre interval");
    req_id=requests;seen_addr[requests]=a;seen_cmd[requests]=c;request_cycle[requests]=cycles;requests=requests+1;
    chosen=mode;if(first_fault && requests>1) chosen=0;
    if(chosen==8) chosen=(a==8'he1)?3:0;
    @(negedge de);ticks(80);
    if(chosen==5) ticks(5000);
    if(chosen!=3 && rst_n && local_gen==gen) begin
     response(a,c,chosen);
     if(chosen==6) begin ticks(80);response(a,c,0);end
    end
   end
  end
 end
 task apply_config;
  input [31:0] p0,p1,p2,p3,p4;input [4:0] m;input integer expected_error;
  integer limit;reg [31:0] old_revision;reg [159:0] old_active;
  begin
   limit=0;while(!cfg_ready && limit<100000) begin ticks(1);limit=limit+1;end
   if(!cfg_ready) $fatal(1,"cfg ready timeout");
   @(negedge clk);old_revision=revision;old_active=active_periods;
   periods={p4,p3,p2,p1,p0};mask=m;cfg_valid=1;ticks(1);cfg_valid=0;
   limit=0;while(!applied && !rejected && limit<100000) begin ticks(1);limit=limit+1;end
   if(!applied && !rejected) $fatal(1,"cfg apply timeout state=%0d mode=%0d mask=%h pending=%0d revision=%0d old=%0d active=%h error=%0d",dut.state,mode,m,dut.pending,revision,old_revision,active_mask,cfg_error);
   if(cfg_error!=expected_error) $fatal(1,"cfg error got=%0d want=%0d",cfg_error,expected_error);
   if(expected_error==0) begin
    if(!applied || revision!=old_revision+1 || active_periods!=periods || active_mask!=m) $fatal(1,"atomic config");
   end else if(!rejected || revision!=old_revision || active_periods!=old_active) $fatal(1,"rejected config changed active state");
   ticks(1);
  end
 endtask
 task reset_case;input integer m;input [4:0] qm;
  begin enable=0;rst_n=0;cfg_valid=0;gen=gen+1;slave_line=1;echo=0;protected=0;ticks(2500);
   rec_count=0;requests=0;mode=m;first_fault=0;mask=qm;ready=1;
   rst_n=1;ticks(400);apply_config(5000,5000,5000,5000,5000,qm,0);enable=1;
  end
 endtask
 task wait_records;input integer n;integer limit;
  begin limit=0;while(rec_count<n && limit<2000000) begin ticks(1);limit=limit+1;end
   if(rec_count<n) $fatal(1,"record timeout mode=%0d count=%0d want=%0d state=%0d",mode,rec_count,n,dut.state);
  end
 endtask
 task expect_status;input integer i,s;
  begin if(records[i][231:224]!=s) $fatal(1,"fault=%0d rec=%0d status=%0d want=%0d",mode,i,records[i][231:224],s);end
 endtask
 integer i,j,kq,n,s,seed=20261013,seed_arg,counts[0:14],expected,limit,prev_requests;
 reg [63:0] cool,stamp;reg [31:0] old_rev;reg [255:0] held;
 initial begin
  if($value$plusargs("seed=%d",seed_arg)) seed=seed_arg;
  $display("SEED %0d",seed);
  reset_case(0,31);enable=0;
  apply_config(3000,11000,7000,13000,17000,31,0);enable=1;ticks(6000000);enable=0;wait(!busy);ticks(10);
  for(i=0;i<15;i=i+1) counts[i]=0;
  for(i=0;i<requests;i=i+1) begin
   case(seen_cmd[i]) 8'h30:j=0;8'h33:j=1;8'h39:j=2;8'h3a:j=3;8'h3e:j=4;default:$fatal(1,"write command");endcase
   n=(seen_addr[i]-8'he0)*5+j;counts[n]=counts[n]+1;
  end
  for(i=0;i<15;i=i+1) begin
   case(i%5) 0:expected=20;1:expected=5;2:expected=8;3:expected=4;4:expected=3;endcase
   if(counts[i]<expected || counts[i]>expected+2) $fatal(1,"mixed frequency task=%0d count=%0d",i,counts[i]);
   $display("RATE task=%0d samples=%0d over 60ms",i,counts[i]);
  end
  if(errors || offline) $fatal(1,"healthy mixed polling");
  $display("PASS mixed periods and healthy per-node frequency");
  reset_case(0,31);wait_records(15);enable=0;wait(!busy);
  for(i=0;i<15;i=i+1) if(seen_addr[i]!=(8'he0+i/5)) $fatal(1,"tie fairness");
  for(s=1;s<32;s=s+1) begin
   reset_case(0,s);n=0;for(j=0;j<5;j=j+1) if(s&(1<<j)) n=n+1;
   wait_records(3*n);enable=0;wait(!busy);
   for(i=0;i<3*n;i=i+1) begin
    case(seen_cmd[i]) 8'h30:j=0;8'h33:j=1;8'h39:j=2;8'h3a:j=3;8'h3e:j=4;default:j=5;endcase
    if(!(s&(1<<j))) $fatal(1,"disabled query");
   end
  end
  reset_case(0,0);ticks(20000);if(requests || rec_count) $fatal(1,"zero mask");
  enable=0;apply_config(0,5000,0,0,0,31,0);enable=1;wait_records(3);enable=0;wait(!busy);
  for(i=0;i<3;i=i+1) if(seen_cmd[i]!=8'h33) $fatal(1,"period zero disable");
  apply_config(999,5000,5000,5000,5000,31,1);
  apply_config(32'h80000000,5000,5000,5000,5000,31,1);
  apply_config(1000,1000,1000,1000,1000,31,2);
  $display("PASS masks, zero periods, fairness, range and budget rejection");
  reset_case(1,1);first_fault=1;wait(de);ticks(1);old_rev=revision;
  periods={5{32'd6000}};mask=16;cfg_valid=1;ticks(1);cfg_valid=0;
  ticks(200);if(revision!=old_rev || active_mask!=1 || cfg_ready) $fatal(1,"pending configuration");
  wait(applied);if(busy || active_mask!=16 || apply_sequence!=1) $fatal(1,"cfg boundary retry");
  wait_records(3);enable=0;wait(!busy);
  expect_status(0,1);expect_status(1,0);
  if(records[0][207:176]!=records[1][207:176] || records[1][223:216]!=1 || records[0][175:112]!=records[1][175:112] || records[2][239:232]!=8'h3e) $fatal(1,"in-flight config altered retry");
  $display("PASS atomic in-flight commit, bounded retry association and revision boundary");
  for(s=1;s<=7;s=s+1) begin
   reset_case(s,8);first_fault=1;wait_records(2);enable=0;wait(!busy);
   case(s) 1:j=1;2:j=2;3:j=3;4:j=5;5:j=3;6:j=0;7:j=4;endcase
   expect_status(0,j);expect_status(1,0);
   if(s!=6 && records[0][207:176]!=records[1][207:176]) $fatal(1,"fault retry");
   if(offline || dut.failures[0]!=0) $fatal(1,"retry success marked offline");
  end
  reset_case(0,31);echo=1;wait_records(15);enable=0;wait(!busy);if(errors) $fatal(1,"echo");
  reset_case(0,16);protected=1;wait_records(6);enable=0;wait(!busy);
  if(offline || errors || records[0][7:0]!=1) $fatal(1,"protection is business data");
  $display("PASS checksum, UART, timeout, wrong/late/duplicate/truncated frames, echo and protection");
  reset_case(8,8);enable=0;apply_config(1000,1000,1000,1000,1000,8,0);enable=1;
  wait(offline[1]);dn=1;ticks(2);cool=cooldown;
  if(streak!=3 || backoffs!=1 || cool-time_us>500000 || cool-time_us<499990) $fatal(1,"backoff threshold/deadline");
  prev_requests=0;for(i=0;i<requests;i=i+1) if(seen_addr[i]==8'he1) prev_requests=prev_requests+1;
  ticks(250000);n=0;for(i=0;i<requests;i=i+1) if(seen_addr[i]==8'he1) n=n+1;
  if(n!=prev_requests || accepted<8) $fatal(1,"offline polling or healthy node starvation");
  // Advance the injected system clock to the real 500ms expiry without wall wait.
  @(negedge clk);time_us=cool;
  // Failed probe renews cooldown exactly once.
  wait(backoffs==2);ticks(1);if(!offline[1] || streak!=4 || cooldown<=cool) $fatal(1,"failed probe renewal");
  mode=0;@(negedge clk);time_us=cooldown;wait(!offline[1]);ticks(2);if(streak!=0) $fatal(1,"probe recovery");
  enable=0;wait(!busy);
  for(i=0;i<requests;i=i+1) if(seen_cmd[i]!=8'h3a) $fatal(1,"probe used disabled query");
  $display("PASS three logical failures, cooldown, healthy progress, failed/successful enabled-query probe");
  reset_case(0,8);ready=0;wait(level==8);held=data;ticks(1200000);
  if(dropped==0 || data!==held || offline || errors) $fatal(1,"FIFO backpressure/offline confusion");
  enable=0;wait(!busy);ready=1;wait_records(8);
  $display("PASS whole-record FIFO overflow continues polling without node failure");
  reset_case(0,1);wait_records(3);enable=0;wait(!busy);ticks(1000);
  time_us=time_us+500000;enable=1;wait_records(6);enable=0;wait(!busy);dt=0;ticks(2);
  if(missed<90 || scheduled<sent+missed || max_late<490000) $fatal(1,"coalescing statistics");
  for(i=3;i<6;i=i+1) if(records[i][207:176]!=i) $fatal(1,"catch-up created extra sequence");
  $display("PASS large lateness coalesces releases, preserves phase and reports skipped samples");
  // Same system epoch modulo wrap; source time is injected only by the bench.
  reset_case(0,0);enable=0;time_us=64'hfffffffffffff800;
  apply_config(1000,1000,1000,1000,1000,8,0);enable=1;ticks(300000);enable=0;wait(!busy);
  if(time_us[63] || rec_count<6 || errors) $fatal(1,"64-bit time wrap");
  $display("PASS modular unified-time wrap");
  reset_case(0,0);slave_line=0;ticks(30000);
  if(offline || requests || errors || bus_events==0) $fatal(1,"BUS_BUSY node attribution");slave_line=1;
  for(s=2;s<=7;s=s+1) begin
   reset_case(0,8);wait(dut.engine.state==s);@(negedge clk);rst_n=0;enable=0;cfg_valid=0;gen=gen+1;
   ticks(2500);if(de || valid || offline || dropped || revision) $fatal(1,"reset transaction");
  end
  for(s=0;s<8;s=s+1) begin j=($random(seed)&32'h7fffffff)%5+1;if(j==5) j=7;
   reset_case(j,8);first_fault=1;wait_records(2);enable=0;wait(!busy);expect_status(1,0);end
  if(step_edges<1000) $fatal(1,"STP activity");
  $display("PASS seeded faults and independent STP edges=%0d",step_edges);
  $display("PASS multirate");$finish;
 end
 initial begin #250000000;$fatal(1,"multirate watchdog state=%0d records=%0d",dut.state,rec_count);end
endmodule

