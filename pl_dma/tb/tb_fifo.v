`timescale 1ns/1ps
module tb_fifo;
parameter DEPTH=16;
reg clk=0,rst_n=0;always #5 clk=~clk;
reg [63:0] s_data;reg [7:0] s_keep;reg s_last,s_valid=0,m_ready=0;
reg [3:0] s_user;reg [4:0] s_id,s_dest;
wire [63:0] m_data;wire [7:0] m_keep;wire m_last,m_valid,s_ready;
wire [3:0] m_user;wire [4:0] m_id,m_dest;wire [31:0] occupancy;
axis_loop_fifo #(.DEPTH(DEPTH)) dut(clk,rst_n,s_data,s_keep,s_last,s_valid,s_ready,s_user,s_id,s_dest,m_data,m_keep,m_last,m_valid,m_ready,m_user,m_id,m_dest,occupancy);
reg [86:0] expected[0:8191],old_payload;integer front=0,back=0,checks=0,serial=0,i,mode;
reg blocked=0,input_blocked=0,input_accepted=0;reg [86:0] old_input;
reg [31:0] random_state=32'hc001beef;
task check;input c;begin checks=checks+1;if(!c) $fatal(1,"FIFO depth=%0d front=%0d back=%0d serial=%0d",DEPTH,front,back,serial);end endtask
always @(posedge clk) begin
 if(!rst_n) begin front=0;back=0;blocked=0;input_blocked=0;input_accepted=0;end
 else begin
  check(occupancy==back-front);check(m_valid==(back!=front));check(s_ready==(back-front<DEPTH));
  if(blocked) check(m_valid && {m_dest,m_id,m_user,m_last,m_keep,m_data}===old_payload);
  if(input_blocked) check(s_valid && {s_dest,s_id,s_user,s_last,s_keep,s_data}===old_input);
  if(m_valid && m_ready) begin check({m_dest,m_id,m_user,m_last,m_keep,m_data}===expected[front]);front=front+1;end
  if(s_valid && s_ready) begin expected[back]={s_dest,s_id,s_user,s_last,s_keep,s_data};back=back+1;serial=serial+1;end
  blocked=m_valid && !m_ready;old_payload={m_dest,m_id,m_user,m_last,m_keep,m_data};
  input_blocked=s_valid && !s_ready;input_accepted=s_valid && s_ready;
  old_input={s_dest,s_id,s_user,s_last,s_keep,s_data};
 end
end
task drive;input integer phase;
 begin
  @(negedge clk);random_state={random_state[30:0],random_state[31]^random_state[21]^random_state[1]^random_state[0]};
  if(!s_valid || input_accepted) begin
   s_valid=phase==0 ? 1 : phase==1 ? 0 : random_state[0];
   s_data={32'hd00d0000|serial,32'h12340000^serial};s_keep=random_state[15:8];s_last=serial%7==6;
   s_user=serial;s_id=serial/2;s_dest=serial/3;
  end
  m_ready=phase==0 ? 0 : phase==1 ? 1 : random_state[3];
 end
endtask
initial begin
 s_data=0;s_keep=0;s_last=0;s_user=0;s_id=0;s_dest=0;
 repeat(3) @(negedge clk);rst_n=1;
 for(mode=0;mode<4;mode=mode+1) begin
  for(i=0;i<DEPTH+8;i=i+1) drive(0);
  @(negedge clk);check(occupancy==DEPTH && !s_ready);
  for(i=0;i<DEPTH+8;i=i+1) drive(1);
  for(i=0;i<1000;i=i+1) drive(2);
  @(negedge clk);rst_n=0;s_valid=0;m_ready=0;
  #1;check(!m_valid && !s_ready);repeat(3) @(negedge clk);rst_n=1;
 end
 for(i=0;i<DEPTH+8;i=i+1) drive(1);
 @(negedge clk);s_valid=0;check(front==back && occupancy==0);
 $display("PASS fifo depth=%0d checks=%0d accepted=%0d",DEPTH,checks,serial);$finish;
end
endmodule
