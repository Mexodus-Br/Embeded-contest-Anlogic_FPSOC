`timescale 1ns/1ps
// Behavioral slave deliberately decodes line timing, not the DUT RX implementation.
module tb_rs485;
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
 rs485_master #(.BAUD(5000000),.POLL_CYCLES(900),.TIMEOUT_CYCLES(5000),
  .INTERBYTE_CYCLES(600),.PRE_CYCLES(40),.POST_CYCLES(40),.TURN_CYCLES(40),.QUIET_CYCLES(800),.FIFO_DEPTH(8))
 dut(clk,rst_n,enable,mask,time_us,rx,tx,de,ready,valid,data,level,dropped,accepted,errors,ignored,busy);
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
  if(data[175:112]>data[111:48] || data[111:48]>time_us) $fatal(1,"timestamps");
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
  begin if(len==1) value_byte=(cmd==8'h3e)?2:1;else value_byte=(j==0)?8'hff:(addr+cmd+j);end
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
 task reset_case;input integer m;input [4:0] qm;
  begin enable=0;rst_n=0;gen=gen+1;slave_line=1;echo=0;ticks(2500);
   rec_count=0;requests=0;mode=m;first_fault=0;mask=qm;ready=1;
   rst_n=1;enable=1;ticks(1);end
 endtask
 task wait_records;input integer n;integer limit;
  begin limit=0;while(rec_count<n && limit<200000) begin ticks(1);limit=limit+1;end
   if(rec_count<n) $fatal(1,"records timeout mode=%0d have=%0d want=%0d state=%0d",mode,rec_count,n,dut.state);
  end
 endtask
 task expect_status;input integer i,s;
  begin if(records[i][231:224]!=s) $fatal(1,"status case=%0d rec=%0d got=%0d want=%0d",mode,i,records[i][231:224],s);end
 endtask
 integer i,j,n,seed,seed_arg,s,base;reg [47:0] expected;reg [255:0] held;
 initial begin
  seed=20261013;if($value$plusargs("seed=%d",seed_arg)) seed=seed_arg;
  $display("SEED %0d",seed);
  if($test$plusargs("wave")) begin $dumpfile("rs485.vcd");$dumpvars(0,tb_rs485);end
  reset_case(0,31);wait_records(15);enable=0;
  for(i=0;i<15;i=i+1) begin
   expect_status(i,0);if(records[i][247:240]!=(8'he0+i/5)) $fatal(1,"address order");
   if(records[i][239:232]!=seen_cmd[i] || records[i][207:176]!=i || records[i][223:216]!=0) $fatal(1,"association");
   n=data_len(seen_cmd[i]);expected=0;
   for(j=0;j<n;j=j+1) expected={expected[39:0],value_byte(j,n,seen_addr[i],seen_cmd[i])};
   if(records[i][47:0]!=expected || records[i][215:208]!=n) $fatal(1,"data/length/endian");
  end
  $display("PASS multi-address all five queries, checksum and endian");
  // Enumerate ALL nonzero masks; avoids accidentally allowing a write opcode.
  for(s=1;s<32;s=s+1) begin
   reset_case(0,s);n=0;for(j=0;j<5;j=j+1) if(s&(1<<j)) n=n+1;
   wait_records(n*3);enable=0;
   for(i=0;i<n*3;i=i+1) begin
    if(records[i][247:240]!=(8'he0+i/n)) $fatal(1,"mask slave schedule");
    case(records[i][239:232]) 8'h30:j=0;8'h33:j=1;8'h39:j=2;8'h3a:j=3;8'h3e:j=4;default:j=5;endcase
    if(!(s&(1<<j))) $fatal(1,"disabled query sent");
   end
  end
  reset_case(0,0);ticks(20000);if(requests!=0) $fatal(1,"zero mask did not pause");
  mask=1;wait(de);mask=16;wait_records(2);enable=0;
  if(records[0][239:232]!=8'h30 || records[1][239:232]!=8'h3e) $fatal(1,"mask in-flight mutation");
  $display("PASS all 31 masks, zero pause, in-flight query stable");
  for(s=1;s<=7;s=s+1) begin
   reset_case(s,8);first_fault=1;
   if(s==6) begin wait_records(2);expect_status(0,0);expect_status(1,0);if(ignored==0) $fatal(1,"duplicate not counted");end
   else begin
    wait_records(2);
    case(s) 1:j=1;2:j=2;3:j=3;4:j=5;5:j=3;7:j=4;default:j=0;endcase
    expect_status(0,j);expect_status(1,0);
    if(records[0][207:176]!=records[1][207:176] || records[1][223:216]!=1 || records[0][175:112]!=records[1][175:112]) $fatal(1,"retry association");
    if(s==5 && ignored==0) $fatal(1,"late frame not counted");
   end
   enable=0;$display("PASS fault mode %0d",s);
  end
  reset_case(3,8);wait_records(6);enable=0;
  if(requests!=6 || records[4][247:240]!=8'he2) $fatal(1,"dead slave blocked polling");
  reset_case(8,8);wait_records(4);enable=0;
  expect_status(0,0);expect_status(1,3);expect_status(2,3);expect_status(3,0);
  if(records[3][247:240]!=8'he2) $fatal(1,"one failed node starved healthy node");
  reset_case(7,1);first_fault=1;wait_records(2);enable=0;
  expect_status(0,4);expect_status(1,0);
  // A short false start during active receive must be discarded by UART.
  reset_case(0,8);wait(dut.state==6);slave_line=0;ticks(4);slave_line=1;
  wait_records(1);enable=0;expect_status(0,0);
  reset_case(0,31);echo=1;wait_records(15);enable=0;
  if(errors!=0) $fatal(1,"echo poisoned RX");
  $display("PASS bounded dead-slave progress and TX echo");
  reset_case(0,8);ready=0;wait(level==8);held=data;ticks(30000);
  if(dropped==0 || level!=8 || data!==held) $fatal(1,"FIFO overwrite/block/drop");
  enable=0;ready=1;wait_records(8);
  for(i=0;i<8;i=i+1) if(records[i][207:176]!=i) $fatal(1,"FIFO ordering");
  $display("PASS FIFO full whole-record drop and drain");
  // Reset interrupts PRE, SEND, HOLD, TURN, RECEIVE, EMIT and QUIET.
  for(s=1;s<=7;s=s+1) begin
   reset_case(0,8);wait(dut.state==s);@(negedge clk);rst_n=0;enable=0;gen=gen+1;
   ticks(2500);if(de || valid || accepted || errors || dropped) $fatal(1,"reset retained transaction");
  end
  reset_case(0,8);slave_line=0;wait_records(3);enable=0;
  for(i=0;i<3;i=i+1) expect_status(i,6);
  slave_line=1;
  reset_case(0,0);slave_line=0;ticks(20000);
  if(accepted || errors || requests || level) $fatal(1,"zero mask busy-bus pause");
  slave_line=1;
  $display("PASS reset interruption and continuously noisy bus bounded skip");
  for(s=0;s<20;s=s+1) begin
   j=($random(seed)&32'h7fffffff)%5+1;if(j==5) j=7;
   reset_case(j,8);first_fault=1;wait_records(2);expect_status(1,0);enable=0;
  end
  if(step_edges<1000) $fatal(1,"STP coverage");
  $display("PASS seeded fault regression and independent continuous STP edges=%0d",step_edges);
  $display("PASS rs485");$finish;
 end
 initial begin #200000000;$fatal(1,"global watchdog");end
endmodule
