`timescale 1ns/1ps
`include "safety_defs.vh"
`include "generated/interface_defs.vh"
module tb_safety;
parameter MODE=0,OFFSET=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg [2:0] limit_n=7;reg estop_n=1;
reg [63:0] time_us=0;integer div=0,cycle=0;
always @(posedge clk)begin
 if(!rst_n)begin time_us<=0;div<=0;end
 else if(div>=((MODE==16 || MODE==17 || (MODE==18 && dut.state==`SAF_STATES_PULL)) ? 1:99))begin div<=0;time_us<=time_us+1;end else div<=div+1;
 cycle=cycle+1;if(cycle>30000)$fatal(1,"watchdog mode=%0d state=%0d causes=%h",MODE,dut.state,dut.causes);
end
reg [65:0] awaddr=0,araddr=0;reg [63:0] wdata=0;reg [7:0] wstrb=255;
reg [1:0] awvalid=0,wvalid=0,bready=0,arvalid=0,rready=0;
wire [1:0] awready,wready,bvalid,arready,rvalid;wire [3:0] bresp,rresp;wire [63:0] rdata;
wire [3:0] step,dir,en,valid,pulse;wire [255:0] position,pulses;wire busy,session,running,stopped;
reg [63:0] stream_data=0;reg stream_last=0,stream_valid=0;wire stream_ready;
safety_motion_service #(.CONFIG_PROFILE(MODE==8 ? 0:1),.FIFO_DEPTH(3),.PLAN_DEPTH(2),.START_MIN_POINTS(2),
 .STEP_HIGH_CYCLES({4{64'd3}}),.STEP_LOW_CYCLES({4{64'd2}}),.DIR_SETUP_CYCLES({4{64'd4}}),
 .DIR_HOLD_CYCLES({4{64'd7}}),.EN_SETUP_CYCLES({4{64'd5}}),.EN_DISABLE_CYCLES({4{64'd3}}),
 .MAX_STEP_HZ(MODE==19 ? {4{64'd1}} : {4{64'd10000000}})) dut(
 .clk(clk),.rst_n(rst_n),.dma_reset_released(1'b1),.dma_error(1'b0),.fault(4'd0),
 .s_awaddr(awaddr[0+:33]),.s_araddr(araddr[0+:33]),.s_wdata(wdata[0+:32]),.s_wstrb(wstrb[0+:4]),
 .s_awvalid(awvalid[0]),.s_wvalid(wvalid[0]),.s_bready(bready[0]),.s_arvalid(arvalid[0]),.s_rready(rready[0]),
 .s_awready(awready[0]),.s_wready(wready[0]),.s_bvalid(bvalid[0]),.s_arready(arready[0]),.s_rvalid(rvalid[0]),
 .s_bresp(bresp[0+:2]),.s_rresp(rresp[0+:2]),.s_rdata(rdata[0+:32]),
 .saf_awaddr(awaddr[33+:33]),.saf_araddr(araddr[33+:33]),.saf_wdata(wdata[32+:32]),.saf_wstrb(wstrb[4+:4]),
 .saf_awvalid(awvalid[1]),.saf_wvalid(wvalid[1]),.saf_bready(bready[1]),.saf_arvalid(arvalid[1]),.saf_rready(rready[1]),
 .saf_awready(awready[1]),.saf_wready(wready[1]),.saf_bvalid(bvalid[1]),.saf_arready(arready[1]),.saf_rvalid(rvalid[1]),
 .saf_bresp(bresp[2+:2]),.saf_rresp(rresp[2+:2]),.saf_rdata(rdata[32+:32]),
 .limit_n(limit_n),.estop_n(estop_n),.shared_time_us(time_us),.safety_irq(),
 .stream_data(stream_data),.stream_keep(8'hff),.stream_last(stream_last),.stream_valid(stream_valid),.stream_ready(stream_ready),
 .step(step),.dir(dir),.en(en),.position_valid(valid),.position(position),.pulses(pulses),.running(running),
 .paused(),.core_busy(busy),.session_valid(session),.session_id(),.fifo_level(),.prepared_level(),.buffered_points(),
 .point_start(),.point_done(),.stopped(stopped),.pulse_event(pulse),.slot_event(),.slot_id(),.irq());
integer checks=0,tid=0,mtid=0,stop_events=0;
 always @(negedge clk)if(rst_n && stopped)stop_events=stop_events+1;
task check;input ok;input [511:0] msg;begin
 checks=checks+1;if(ok!==1'b1)begin $display("FAIL mode=%0d offset=%0d cycle=%0d state=%0d causes=%h %0s",MODE,OFFSET,cycle,dut.state,dut.causes,msg);$fatal(1);end
end endtask
task wr;input integer bus;input [31:0] off,val;input [1:0] response;begin
 @(negedge clk);awaddr[bus*33+:33]=(bus==1 ? {1'b0,`SAF_BASE}:{1'b0,`PLI_MOTION_GP_MOTION_V1_BASE})+off;
 wdata[bus*32+:32]=val;awvalid[bus]=1;
 @(posedge clk);while(!awready[bus])@(posedge clk);@(negedge clk);awvalid[bus]=0;
 repeat(2)@(negedge clk);wvalid[bus]=1;
 @(posedge clk);while(!wready[bus])@(posedge clk);@(negedge clk);wvalid[bus]=0;
 while(!bvalid[bus])@(negedge clk);
 repeat(3)begin check(bvalid[bus] && bresp[bus*2+:2]==response,"write B ownership/backpressure");@(negedge clk);end
 bready[bus]=1;@(negedge clk);bready[bus]=0;
end endtask
task rd;input [32:0] address;input [1:0] response;output [31:0] value;begin
 @(negedge clk);araddr[33+:33]=address;arvalid[1]=1;
 @(posedge clk);while(!arready[1])@(posedge clk);@(negedge clk);arvalid[1]=0;
 while(!rvalid[1])@(negedge clk);value=rdata[32+:32];
 repeat(4)begin check(rvalid[1] && rresp[2+:2]==response && rdata[32+:32]===value,"read snapshot held under backpressure");@(negedge clk);end
 rready[1]=1;@(negedge clk);rready[1]=0;
end endtask
task command;input [31:0] op;begin
 tid=tid+1;wr(1,`SAF_REGISTERS_OPCODE,op,0);wr(1,`SAF_REGISTERS_ARG,0,0);
 wr(1,`SAF_REGISTERS_TXN,tid,0);wr(1,`SAF_REGISTERS_SUBMIT,1,0);
end endtask
task mcommand;input [31:0] op,arg;begin
 mtid=mtid+1;wr(0,`PLI_MOTION_GP_MOTION_V1_REG_OPCODE,op,0);wr(0,`PLI_MOTION_GP_MOTION_V1_REG_ARG,arg,0);
 wr(0,`PLI_MOTION_GP_MOTION_V1_REG_TXN,mtid,0);wr(0,`PLI_MOTION_GP_MOTION_V1_REG_SUBMIT,1,0);repeat(8)@(negedge clk);
end endtask
// Independent physical pin oracle: counts, signed position, pulse shape and age.
reg [3:0] old_step=0,old_dir=15,old_en=0;
reg [255:0] expected_pos=0,expected_pulses=0;
integer rise[0:3],fall[0:3],dir_change[0:3],enable_cycle[0:3];
integer phase_count[0:2];reg [3:0] old_state=0;integer search_age=0;
function integer rank;input integer axis;begin
 case(MODE)
  24:rank=axis;
  25:rank=axis==0 ? 0 : axis==1 ? 2:1;
  26:rank=axis==0 ? 1 : axis==1 ? 0:2;
  27:rank=axis==0 ? 2 : axis==1 ? 0:1;
  28:rank=axis==0 ? 1 : axis==1 ? 2:0;
  default:rank=2-axis;
 endcase
end endfunction
integer a;reg auto_contacts=1;
always @(negedge clk)begin
 if(!rst_n)begin
  old_step=0;old_dir=15;old_en=0;expected_pos=0;expected_pulses=0;old_state=0;
  for(a=0;a<4;a=a+1)begin rise[a]=-100;fall[a]=-100;dir_change[a]=-100;enable_cycle[a]=-100;end
  for(a=0;a<3;a=a+1)phase_count[a]=0;
 end else begin
  if(dut.state!=old_state)begin
   search_age=0;for(a=0;a<3;a=a+1)phase_count[a]=0;
  end
  if(dut.state==`SAF_STATES_SEARCH)search_age=search_age+1;
  // Reference load occurs exactly once, at the fully safe REF boundary.
  if(old_state==`SAF_STATES_REF && dut.state==`SAF_STATES_PULL)begin
   check(step[2:0]==0 && valid[2:0]==0,"reference captured stopped and still invalid");
   expected_pos[63:0]=100;expected_pos[127:64]=-64'sd200;expected_pos[191:128]=300;
  end
  for(a=0;a<4;a=a+1)begin
   if(en[a] && !old_en[a])enable_cycle[a]=cycle;
   if(dir[a]!=old_dir[a])begin check(cycle-rise[a]>=7,"DIR hold");dir_change[a]=cycle;end
   if(step[a] && !old_step[a])begin
    check(cycle-fall[a]>=2 && cycle-dir_change[a]>=4 && cycle-enable_cycle[a]>=5,"low/setup/EN timing");
    rise[a]=cycle;expected_pos[a*64+:64]=$signed(expected_pos[a*64+:64])+(dir[a] ? 64'sd1:-64'sd1);
    expected_pulses[a*64+:64]=expected_pulses[a*64+:64]+1;
    if(a<3)phase_count[a]=phase_count[a]+1;
   end
   if(!step[a] && old_step[a])begin check(cycle-rise[a]==3,"no truncated high pulse");fall[a]=cycle;end
   if(!en[a] && old_en[a])check(!step[a] && cycle-rise[a]>=7+3,"EN closes after safe hold and off delay");
  end
  check(position===expected_pos,"position equals true signed pin edges and private reference");
  check(pulses===expected_pulses,"pulse totals count HOME and ordinary motion once");
  if(dut.owner && dut.state!=`SAF_STATES_FINISH)check(valid[2:0]==0,"HOME invalid until atomic completion");
  if(auto_contacts)for(a=0;a<3;a=a+1)begin
   if(dut.state==`SAF_STATES_PRE && phase_count[a]>=2 && MODE!=7 && MODE!=17)limit_n[a]=1;
   if(dut.state==`SAF_STATES_SEARCH && (MODE==22 ? search_age>=40 : MODE>=24 ? search_age>=20+rank(a)*30 : phase_count[a]>=3+a*3) && !((MODE==4 || MODE==16) && a==2))limit_n[a]=0;
   if(dut.state==`SAF_STATES_PULL && phase_count[a]>=2 && MODE!=5)limit_n[a]=1;
   if(MODE==6 && dut.state==`SAF_STATES_PULL && dut.released_mask[a])limit_n[a]=0;
  end
  old_step=step;old_dir=dir;old_en=en;old_state=dut.state;
 end
end
reg [3:0] before_step;reg kill;reg [2:0] run_before;
always @(posedge clk)if(rst_n)begin
 before_step=step;kill=dut.ctrl_stop || dut.ctrl_disable;run_before=dut.run;
 #1;
 if(kill)check((step & ~before_step)==0,"detecting edge globally inhibits new STEP");
 if(dut.owner)check(((step[2:0] & ~before_step[2:0]) & ~run_before)==0,"HOME hit axis gets no new edges");
end
reg [575:0] rec;reg [31:0] crc;integer k,b;
function [31:0] crc_byte;input [31:0] c;input [7:0] v;integer j;reg [31:0] x;begin
 x=c^v;for(j=0;j<8;j=j+1)x=x[0] ? (x>>1)^32'hedb88320:x>>1;crc_byte=x;
end endfunction
task start_normal;begin
 wr(0,`PLI_MOTION_GP_MOTION_V1_REG_RECOVER_GEN,1,0);mcommand(`PLI_CMD_LINK_RECOVER,0);
 wr(0,`PLI_MOTION_GP_MOTION_V1_REG_SESSION_LO,1,0);mcommand(`PLI_CMD_OPEN_SESSION,0);
 check(session,"explicit new normal session after HOME");wr(0,`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,1,0);
 rec=0;rec[0+:32]=32'h32544f4d;rec[32+:16]=2;rec[48+:16]=72;rec[64+:64]=1;
 rec[160]=1;rec[176+:16]=7;rec[192+:64]=10;
 for(k=0;k<3;k=k+1)rec[256+k*64+:64]=$signed(position[k*64+:64])+20;
 crc=32'hffffffff;for(k=0;k<68;k=k+1)crc=crc_byte(crc,rec[k*8+:8]);rec[544+:32]=~crc;
 for(b=0;b<9;b=b+1)begin
  @(negedge clk);stream_data=rec[b*64+:64];stream_last=b==8;stream_valid=1;
  @(posedge clk);while(!stream_ready)@(posedge clk);@(negedge clk);stream_valid=0;
 end
 while(!dut.motion.start_ready)@(negedge clk);mcommand(`PLI_CMD_START,0);
 check(running,"HOME position used by unchanged continuous scheduler");
end endtask
integer t,pad_cycle,detect_cycle,drain_latency,en_latency;reg [31:0] value,saved;reg [255:0] lastpos;
initial begin
 if(MODE==1 || MODE==7 || MODE==10 || MODE==17)limit_n=2;
 repeat(6)@(negedge clk);rst_n=1;repeat(15)@(negedge clk);
 check(en==0 && valid==0 && !session,"boot disabled invalid no session");
 rd({1'b0,`SAF_BASE}+`SAF_REGISTERS_CONFIG_VALID,0,value);check(value==(MODE!=8 && MODE!=19),"production disabled, complete fixture configured");
 rd({1'b1,`SAF_BASE}+4,3,value);rd({1'b0,`SAF_BASE}+1,2,value);
 if(MODE==8 || MODE==19)begin
  command(`SAF_COMMANDS_HOME_START);repeat(200)@(negedge clk);
  check(!dut.registers.ack_accepted && en==0 && pulses==0,"unqualified production HOME rejected");
  mcommand(`PLI_CMD_REBASE,7);mcommand(`PLI_CMD_ENABLE,7);
  check(en==0 && valid==0 && pulses==0,"public maintenance cannot fake HOME");
 end else begin
  command(`SAF_COMMANDS_HOME_START);
  check(dut.registers.ack_accepted,"HOME accepted with unknown position");
  if(MODE==2 || MODE==3 || MODE==10 || MODE==11 || MODE==12 || MODE==20 || MODE==23)begin
   if(MODE==10)while(dut.state!=`SAF_STATES_PRE)@(negedge clk);
   else if(MODE==11 || MODE==12)while(dut.state!=`SAF_STATES_PULL)@(negedge clk);
   else while(dut.state!=`SAF_STATES_SEARCH)@(negedge clk);
   repeat(OFFSET)@(negedge clk);
   if(MODE==3 || MODE==12 || MODE==20 || MODE==23)begin
    #2;estop_n=0;pad_cycle=cycle;
    while(!dut.ctrl_stop)@(negedge clk);
    check(cycle-pad_cycle+1<=3,"pad to executor inhibit bounded by 3 cycles");
    detect_cycle=cycle;
    while(!dut.pulse_safe)@(negedge clk);drain_latency=cycle-detect_cycle;
    while(en[2:0]!=0)@(negedge clk);en_latency=cycle-detect_cycle;
    check(drain_latency<=9 && en_latency<=15,"separate pulse-safe and EN-off cycle budgets");
    $display("LATENCY mode=%0d offset=%0d pad_qualified=%0d executor_inhibit_bound=%0d qualified_drain=%0d qualified_en_off=%0d",MODE,OFFSET,detect_cycle-pad_cycle,detect_cycle-pad_cycle+1,drain_latency,en_latency);
    repeat(25)@(negedge clk);check(en[2:0]==0 && valid[2:0]==0,"ESTOP invalid and EN off");
    if(MODE==23)begin check(stop_events==1,"persistent ESTOP publishes one safe completion");end
    estop_n=1;repeat(10)@(negedge clk);check(dut.causes[3] && !dut.request_ok,"release alone never restores permission");
   end else begin wr(0,`PLI_MOTION_GP_MOTION_V1_REG_STOP,1,0);repeat(25)@(negedge clk);end
   check(valid[2:0]==0 && !dut.owner && !session,"abort invalidates HOME and cancels owner");
   if(MODE==20)begin
    lastpos=pulses;command(`SAF_COMMANDS_CLEAR_FAULT);repeat(10)@(negedge clk);
    check(en[2:0]==0 && valid[2:0]==0 && pulses==lastpos && !session,"manual clear keeps EN off and no autoreplay");
    command(`SAF_COMMANDS_HOME_START);while(dut.state!=`SAF_STATES_READY)@(negedge clk);
    check(valid[2:0]==7 && en[2:0]==7 && !session,"explicit reHOME alone restores validity with fresh EN setup");
   end
  end else if(MODE==4 || MODE==5 || MODE==6 || MODE==7 || MODE==16 || MODE==17 || MODE==18)begin
   while(dut.state!=`SAF_STATES_FAULT)@(negedge clk);
   check(dut.causes!=0 && valid[2:0]==0 && step==0,"bounded failure group stop invalid");
   if(MODE==4 || MODE==16)check((dut.causes & `SAF_CAUSES_SEARCH_FAIL)!=0,"missing switch search limit");
   if(MODE==5 || MODE==18)check((dut.causes & `SAF_CAUSES_PULL_FAIL)!=0,"fixed endpoint does not extend for stuck contact");
   if(MODE==6)check((dut.causes & `SAF_CAUSES_RECONTACT)!=0,"qualified release then recontact fails");
   if(MODE==7 || MODE==17)check((dut.causes & `SAF_CAUSES_PRE_FAIL)!=0,"bounded startup reverse failure");
  end else begin
   while(dut.state!=`SAF_STATES_READY)@(negedge clk);
   check(valid[2:0]==7 && position[63:0]==92 && $signed(position[127:64])==-191 && position[191:128]==290,"fixed pull distance and final absolute coordinate");
   check(dut.travel=={64'd10,64'd9,64'd8},"exact pull distance no extra retry");
   wr(1,`SAF_REGISTERS_SNAP_REQ,1,0);rd({1'b0,`SAF_BASE}+`SAF_SNAPSHOT_BASE+`SAF_SNAPSHOT_POSITION_0*4,0,saved);
   repeat(15)@(negedge clk);rd({1'b0,`SAF_BASE}+`SAF_SNAPSHOT_BASE+`SAF_SNAPSHOT_POSITION_0*4,0,value);check(value==saved,"frozen atomic snapshot");
   wr(1,`SAF_REGISTERS_SUBMIT,1,0);check(!dut.owner,"duplicate HOME id never replays motion");
   if(MODE==9)begin
    auto_contacts=0;#2;limit_n[1]=0;repeat(20)@(negedge clk);
    check(valid[2:0]==0 && dut.causes[1] && step==0,"ordinary limit invalidates whole group");
    command(`SAF_COMMANDS_CLEAR_FAULT);repeat(5)@(negedge clk);
    check(dut.causes==0 && dut.normal_inhibit && valid[2:0]==0,"closed-limit recovery clears only into NEED_HOME");
    auto_contacts=1;command(`SAF_COMMANDS_HOME_START);
    while(dut.state!=`SAF_STATES_READY)@(negedge clk);
    check(valid[2:0]==7,"closed-limit recovery completes bounded preclear and full HOME");
   end
   if(MODE==21)begin
    auto_contacts=0;#2;limit_n=0;estop_n=0;repeat(20)@(negedge clk);
    check(dut.causes[3:0]==15 && dut.first_cause==`SAF_CAUSES_ESTOP && valid[2:0]==0 && en[2:0]==0,"simultaneous sources retained, ESTOP first cause, invalid and disable win");
    saved=dut.first_time;command(`SAF_COMMANDS_CLEAR_FAULT);
    check(!dut.registers.ack_accepted && dut.first_time==saved,"active ESTOP rejects clear and preserves first event time");
   end
   if((MODE>=13 && MODE<=15) || MODE==30)begin
    auto_contacts=0;start_normal;
    repeat(OFFSET)@(negedge clk);
    if(MODE==13)begin #2;limit_n[0]=0;end
    else if(MODE==14)begin #2;estop_n=0;end
    else if(MODE==15)wr(0,`PLI_MOTION_GP_MOTION_V1_REG_STOP,1,0);
    else begin
     while(busy)@(negedge clk);repeat(5)@(negedge clk);
     check(position[63:0]==112 && $signed(position[127:64])==-171 && position[191:128]==310,"ordinary END exact absolute target from HOME position");
    end
    repeat(30)@(negedge clk);
    check(!session && !running && dut.motion.partial_empty && dut.motion.buffered_points==0,"normal cancellation clears session queues and partial record");
    check((MODE==15 || MODE==30) ? valid[2:0]==7 : valid[2:0]==0,"ordinary stop versus physical safety invalidation");
    if(MODE==14)check(en[2:0]==0,"ordinary run ESTOP eventually EN off");
    // Old bytes are not re-admitted after the transport owner is cancelled.
    @(negedge clk);stream_data=rec[0+:64];stream_valid=1;repeat(10)@(negedge clk);
    check(!stream_ready && !session,"late old session cannot auto-restart");stream_valid=0;
   end
   lastpos=position;wr(0,`PLI_MOTION_GP_MOTION_V1_REG_STOP,1,0);repeat(15)@(negedge clk);
   check((MODE==13 || MODE==14 || MODE==21 ? valid[2:0]==0 : valid[2:0]==7) && position==lastpos,"ordinary STOP preserves existing coordinate validity");
  end
 end
 $display("PASS safety mode=%0d offset=%0d checks=%0d cycles=%0d",MODE,OFFSET,checks,cycle);$finish;
end
endmodule
