// GP writes + real MM2S/HP BFM. All motion observations use explicit DUT ports.
localparam [32:0] MB={1'b0,`PLI_MOTION_GP_MOTION_V1_BASE};
integer txn=0,gen=0,phase=0,starts=0,dones=0,started_cycle=0,edges;
integer count_lane[0:3],rise_cycle[0:3],fall_cycle[0:3];
reg [3:0] prev_step=0,prev_dir=15,prev_en=0;
integer m,trace;reg [7:0] fixture[0:71];reg [31:0] snap[0:63];
integer snap_id=0;
always @(posedge clk_100m)if(cycle%5000000==0 && cycle!=0)begin
 $display("PROGRESS scope phase=%0d cycle=%0d",phase,cycle);$fflush(trace);$dumpflush;
end
// Observe every output transition after port propagation settles. Avoid a
// redundant four-lane polling loop on each of 100 million clock cycles.
always @(motion_step or motion_dir or motion_en or motion_point_start or motion_point_done or motion_slot_event or motion_slot_id)begin
 #1;
 if(control_rst_n)begin
  if(motion_point_start)begin starts=starts+1;started_cycle=cycle;
   $display("POINT_START phase=%0d cycle=%0d",phase,cycle);end
  if(motion_point_done)begin dones=dones+1;
   check(cycle-started_cycle==50000000,"exact 500000 ticks duration");
   $display("POINT_DONE phase=%0d cycle=%0d duration_cycles=%0d",phase,cycle,cycle-started_cycle);end
  check(motion_step[3]==0 && motion_en[3]==0,"M4 disabled and no pulses");
  for(m=0;m<4;m=m+1)begin
   if(motion_step[m] && !prev_step[m])begin
    check(motion_slot_event,"pulse belongs to common slot");
    check(cycle-started_cycle==1002+(motion_slot_id*49998998)/124,"common slot exact integer lattice");
    if(count_lane[m]!=0)check(cycle-fall_cycle[m]>=500,"minimum STEP low 5us");
    check(motion_en[m] && motion_dir[m]==(phase==2 ? (m==2) : (m!=2)),"direction and enabled");
    rise_cycle[m]=cycle;count_lane[m]=count_lane[m]+1;
    $fwrite(trace,"%0d,%0d,%0d,%0d,step,1,%0d\n",phase,cycle,cycle-started_cycle,m,motion_slot_id);
   end
   if(!motion_step[m] && prev_step[m])begin
    check(cycle-rise_cycle[m]==500,"exact STEP high 5us including STOP drain");fall_cycle[m]=cycle;
    $fwrite(trace,"%0d,%0d,%0d,%0d,step,0,%0d\n",phase,cycle,cycle-started_cycle,m,motion_slot_id);
   end
   if(motion_dir[m]!=prev_dir[m])$fwrite(trace,"%0d,%0d,%0d,%0d,dir,%0d,%0d\n",phase,cycle,cycle-started_cycle,m,motion_dir[m],motion_slot_id);
   if(motion_en[m]!=prev_en[m])$fwrite(trace,"%0d,%0d,%0d,%0d,en,%0d,%0d\n",phase,cycle,cycle-started_cycle,m,motion_en[m],motion_slot_id);
  end
 end
 prev_step=motion_step;prev_dir=motion_dir;prev_en=motion_en;
end
task command;input [31:0] op,av;begin
 txn=txn+1;
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_OPCODE,op,15,0,1);
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_ARG,av,15,0,2);
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_TXN,txn,15,0,0);
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_SUBMIT,1,15,0,1);
 polls=0;status_value=0;
 while(status_value!=txn && polls<1000)begin read_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_ACK_ID,0,status_value);polls=polls+1;end
 check(status_value==txn,"command ACK identity");
 read_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_ACK_ERROR,0,status_value);check(status_value==0,"command accepted");
 polls=0;status_value=0;
 while(status_value[2:0]!=7 && polls<1000)begin read_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_ACK_STATUS,0,status_value);polls=polls+1;end
 check(status_value[2:0]==7,"command completed");
end endtask
task recover;begin
 gen=gen+1;write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_RECOVER_GEN,gen,15,0,0);
 command(`PLI_CMD_LINK_RECOVER,0);command(`PLI_CMD_CLEAR_FAULT,0);
end endtask
task capture;begin
 snap_id=snap_id+1;write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_SNAP_REQ,snap_id,15,0,0);
 for(n=0;n<64;n=n+1)read_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_SNAP_0+n*4,0,snap[n]);
 $display("SNAP phase=%0d accepted=%0d active=%0d done=%0d ends=%0d error=%x pos=%0d,%0d,%0d pulse=%0d,%0d,%0d",
 phase,snap[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_ACCEPT_SEQ],snap[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_ACTIVE_SEQ],snap[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_DONE_SEQ],snap[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_END_COUNT],snap[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_ERROR],
 $signed({snap[17],snap[16]}),$signed({snap[21],snap[20]}),$signed({snap[25],snap[24]}),{snap[19],snap[18]},{snap[23],snap[22]},{snap[27],snap[26]});
end endtask
task packet;input integer sid;begin
 if(sid==1)$readmemh("outbound.hex",fixture);
 else if(sid==2)$readmemh("return.hex",fixture);else $readmemh("stop.hex",fixture);
 for(n=0;n<72;n=n+1)memory[4096+n]=fixture[n];
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_SESSION_LO,sid,15,0,0);command(`PLI_CMD_OPEN_SESSION,0);
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,1,15,0,0);
 write_reg(BASE+4,32'h7000,15,0,0);write_reg(BASE,32'h5001,15,0,0);write_reg(BASE+24,4096,15,0,0);
 write_reg(BASE+40,72,15,0,0);polls=0;status_value=0;
 while(!status_value[12] && polls<1000)begin read_reg(BASE+4,0,status_value);polls=polls+1;end
 check(status_value[12] && (status_value&32'h770)==0,"MM2S IOC no error");
 polls=0;status_value=0;
 while(status_value!=sid && polls<1000)begin read_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_PACKET_COUNT,0,status_value);polls=polls+1;end
 check(status_value==sid,"packet_closed independent of IOC");
 read_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_ACCEPT_COUNT,0,status_value);check(status_value==sid,"record_accepted");
 read_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_BUFFERED,0,status_value);check(status_value==1,"short END prebuffer below START32");
 repeat(600)@(negedge clk_100m);
 check(motion_step==0,"no STEP before explicit START");
 for(n=0;n<4;n=n+1)count_lane[n]=0;
 phase=sid;command(`PLI_CMD_START,0);
end endtask
initial begin
 trace=$fopen("observed_edges.csv","w");$fwrite(trace,"phase,cycle,relative_cycle,axis,signal,value,slot_id\n");
 $dumpfile("scope_outputs.vcd");$dumpvars(0,motion_step,motion_dir,motion_en,motion_point_start,motion_point_done,motion_slot_event,motion_slot_id);
 clk_100m=0;arst_n=0;gp_awid=0;gp_arid=0;gp_awlen=0;gp_arlen=0;gp_awsize=2;gp_arsize=2;gp_awburst=1;gp_arburst=1;gp_awlock=0;gp_arlock=0;gp_awcache=0;gp_arcache=0;gp_awprot=0;gp_arprot=0;gp_wlast=1;
 gp_awaddr=0;gp_awvalid=0;gp_wdata=0;gp_wstrb=0;gp_wvalid=0;gp_bready=0;gp_araddr=0;gp_arvalid=0;gp_rready=0;
 hp_rdata=0;hp_rvalid=0;hp_rlast=0;hp_rid=0;hp_bvalid=0;hp_bid=0;
 for(n=0;n<4;n=n+1)begin count_lane[n]=0;rise_cycle[n]=0;fall_cycle[n]=0;end
 reset_design;check(motion_step==0 && motion_dir==15 && motion_en==0,"reset STEP0 DIRpositive ENinactive");
 repeat(600)@(negedge clk_100m);check(motion_step==0 && motion_en==0,"unenabled no automatic output");
 recover;write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_MAINT,1,15,0,0);
 for(n=0;n<3;n=n+1)begin
  write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_REBASE_0+n*8,-1090,15,0,0);
  write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_REBASE_1+n*8,32'hffffffff,15,0,0);
 end
 command(`PLI_CMD_REBASE,7);command(`PLI_CMD_ENABLE,7);check(motion_en==7,"explicit three-axis ENABLE only");
 packet(1);wait(dones>=1);repeat(5)@(negedge clk_100m);
 check(count_lane[0]==1 && count_lane[1]==124 && count_lane[2]==123,"outbound counts 1 124 123");
 capture;check($signed({snap[17],snap[16]})==-1089 && $signed({snap[21],snap[20]})==-966 && $signed({snap[25],snap[24]})==-1213,"outbound target position");
 check(snap[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_END_COUNT]==1 && motion_en==7,"END retains EN, normal closure");
 recover;packet(2);wait(dones>=2);repeat(5)@(negedge clk_100m);
 check(count_lane[0]==1 && count_lane[1]==124 && count_lane[2]==123,"return counts 1 124 123");
 capture;check($signed({snap[17],snap[16]})==-1090 && $signed({snap[21],snap[20]})==-1090 && $signed({snap[25],snap[24]})==-1090,"return to reference start");
 recover;packet(3);while(motion_step==0)@(negedge clk_100m);repeat(50)@(negedge clk_100m);
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_STOP,1,15,0,0);
 polls=0;status_value=0;
 while(!(status_value&`PLI_MOTION_GP_MOTION_V1_STATUS_BITS_STOP_COMPLETE_MASK) && polls<1000)begin read_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_STATUS,0,status_value);polls=polls+1;end
 check((status_value&`PLI_MOTION_GP_MOTION_V1_STATUS_BITS_STOP_COMPLETE_MASK)!=0,"GP pulse-safe STOP completed");
 check(motion_step==0 && motion_en==7 && dones==2,"STOP no END/done, retains EN");
 check(count_lane[0]==1 && count_lane[1]==1 && count_lane[2]==1,"STOP suppresses later slots");
 capture;check(snap[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_BUFFERED]==0 && snap[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_END_COUNT]==2,"STOP clears queue not END");
 command(`PLI_CMD_DISABLE,7);repeat(550)@(negedge clk_100m);check(motion_en==0 && motion_step==0,"explicit DISABLE delayed ENinactive");
 check(read_beats==27 && write_beats==0,"three real 72B MM2S transfers and no S2MM RX");
 $fclose(trace);$display("PASS scope_gpio checks=%0d starts=%0d dones=%0d read_beats=%0d",checks,starts,dones,read_beats);$finish;
end
