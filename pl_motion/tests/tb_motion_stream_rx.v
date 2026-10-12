`timescale 1ns/1ps
module tb_motion_stream_rx;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,abort=0,link_ready=1,arm=0;reg [31:0] arm_count=0;
wire arm_ready,packet_busy,partial_empty,s_ready,point_valid,error,packet_closed;
reg [63:0] s_data=0;reg [7:0] s_keep=255;reg s_last=0,s_valid=0,allow_points=0;
wire [63:0] point_session,duration_tick;wire [31:0] point_sequence,packet_count;wire point_end;
wire [3:0] point_mask;wire [255:0] point_target;
integer cycles=0,checks=0,outputs=0,errors=0,expected_seq=0,input_beats=0;
wire point_ready=allow_points && cycles%3!=0;
motion_stream_rx dut(.clk(clk),.rst_n(rst_n),.abort(abort),.link_ready(link_ready),.arm(arm),.arm_count(arm_count),
 .arm_ready(arm_ready),.packet_busy(packet_busy),.partial_empty(partial_empty),.s_data(s_data),.s_keep(s_keep),.s_last(s_last),.s_valid(s_valid),.s_ready(s_ready),
 .point_valid(point_valid),.point_ready(point_ready),.point_session(point_session),.duration_tick(duration_tick),.point_sequence(point_sequence),.point_end(point_end),.point_mask(point_mask),.point_target(point_target),
 .error(error),.packet_closed(packet_closed),.packet_count(packet_count));
task check;input good;input [511:0] msg;begin checks=checks+1;if(!good)begin $display("FAIL rx %0s cycle=%0d",msg,cycles);$fatal(1);end end endtask
reg blocked=0;reg [420:0] held_record;
always @(posedge clk)begin
 cycles=cycles+1;if(cycles>100000)$fatal(1,"rx watchdog");
 if(rst_n)begin
  if(blocked && !abort && link_ready)check(point_valid && {point_target,duration_tick,point_session,point_sequence,point_end,point_mask}==held_record,"valid/payload held without ready");
  blocked<=point_valid && !point_ready && !abort;
  held_record<={point_target,duration_tick,point_session,point_sequence,point_end,point_mask};
  if(s_valid && s_ready)input_beats=input_beats+1;
  if(error)errors=errors+1;
  if(point_valid && point_ready)begin
   check(input_beats>=9*(outputs+1),"no partial record output");
   check(point_session==64'h12345678 && point_sequence==expected_seq && duration_tick==100,"complete metadata");
   check(point_mask==15 && point_end==(expected_seq==2) && point_target[0+:64]==expected_seq+1 && point_target[64+:64]==-64'sd1*(expected_seq+1) && point_target[128+:64]==5*(expected_seq+1) && point_target[192+:64]==-64'sd7*(expected_seq+1),"distinct four-axis signed targets/END");
   outputs=outputs+1;expected_seq=expected_seq+1;
  end
 end else blocked<=0;
end
reg [575:0] record_data;integer i,j,offset,before_errors;
function [31:0] crc_byte;input [31:0] c;input [7:0] b;integer k;reg [31:0] x;begin x=c^b;for(k=0;k<8;k=k+1)x=x[0] ? (x>>1)^32'hedb88320:x>>1;crc_byte=x;end endfunction
task make_record;input integer seq;reg [31:0] c;begin
 record_data=0;record_data[0+:32]=32'h32544f4d;record_data[32+:16]=2;record_data[48+:16]=72;record_data[64+:64]=64'h12345678;
 record_data[128+:32]=seq;record_data[160]=seq==2;record_data[176+:16]=15;record_data[192+:64]=100;
 record_data[256+:64]=seq+1;record_data[320+:64]=-64'sd1*(seq+1);record_data[384+:64]=5*(seq+1);record_data[448+:64]=-64'sd7*(seq+1);
 c=32'hffffffff;for(i=0;i<68;i=i+1)c=crc_byte(c,record_data[i*8+:8]);record_data[544+:32]=~c;
end endtask
task begin_packet;input integer count;begin
 @(negedge clk);check(arm_ready,"arm resource ready");arm_count=count;arm=1;@(negedge clk);arm=0;
end endtask
task beat;input integer index;input last;begin
 @(negedge clk);s_data=record_data[index*64+:64];s_last=last;s_valid=1;
 @(posedge clk);while(!s_ready)@(posedge clk);@(negedge clk);s_valid=0;
end endtask
initial begin
 repeat(3)@(negedge clk);rst_n=1;begin_packet(3);
 fork
  begin for(j=0;j<3;j=j+1)begin make_record(j);for(i=0;i<9;i=i+1)beat(i,j==2 && i==8);end end
  begin repeat(180)@(negedge clk);check(point_valid && outputs==0,"full record held while consumer blocked");allow_points=1;end
 join
 while(packet_busy)@(negedge clk);check(outputs==3 && packet_count==1,"three records one packet");
 // Each of the 72 bytes is corrupted separately. None may produce valid.
 allow_points=0;
 for(offset=0;offset<72;offset=offset+1)begin
  begin_packet(1);make_record(0);record_data[offset*8]=~record_data[offset*8];before_errors=errors;
  for(i=0;i<9;i=i+1)beat(i,i==8);
  repeat(20)@(negedge clk);check(errors==before_errors+1 && outputs==3 && partial_empty && !point_valid,"all byte corruption rejected atomically");
 end
 // Abandon a producer that truncates after any beat without TLAST; abort
 // establishes the new packet boundary, rather than searching for magic.
 for(offset=0;offset<9;offset=offset+1)begin
  begin_packet(1);make_record(0);for(i=0;i<offset;i=i+1)beat(i,0);
  @(negedge clk);abort=1;@(negedge clk);abort=0;
  check(partial_empty && !point_valid && outputs==3,"abort clears every partial-record phase");
 end
 $display("PASS motion_stream_rx checks=%0d corruptions=%0d records=%0d",checks,errors,outputs);$finish;
end
endmodule
