reg stall_hp1=0,hp1_active=0,hp1_pending=0;integer hp1_left=0,hp1_delay=0,hp1_writes=0;reg [32:0] hp1_address;reg [5:0] hp1_id;
assign hp1_arready=control_rst_n;assign hp1_rdata=0;assign hp1_rid=0;assign hp1_rlast=0;assign hp1_rvalid=0;assign hp1_rresp=0;
assign hp1_awready=control_rst_n && !hp1_active && !hp1_pending && !hp1_bvalid && !stall_hp1;
assign hp1_wready=control_rst_n && hp1_active && !stall_hp1 && cycle%3!=0;assign hp1_bresp=0;
integer h;
always @(posedge clk_100m) begin
 if(!control_rst_n) begin hp1_active<=0;hp1_pending<=0;hp1_bvalid<=0;end
 else begin
  check(!hp1_arvalid,"independent S2MM no HP1 read");
  if(hp1_awvalid && hp1_awready) begin check(hp1_awsize==3 && hp1_awlen<16 && hp1_awaddr>=196608 && hp1_awaddr<262144,"HP1 write geometry");hp1_active<=1;hp1_left<=hp1_awlen+1;hp1_address<=hp1_awaddr;hp1_id<=hp1_awid;end
  if(hp1_wvalid && hp1_wready) begin
   check(hp1_wlast==(hp1_left==1),"HP1 WLAST");hp1_writes=hp1_writes+1;
   for(h=0;h<8;h=h+1) if(hp1_wstrb[h]) memory[hp1_address+h]<=hp1_wdata[h*8+:8];
   hp1_address<=hp1_address+8;hp1_left<=hp1_left-1;
   if(hp1_left==1) begin hp1_active<=0;hp1_pending<=1;hp1_delay<=5;end
  end
  if(hp1_pending && !hp1_bvalid) begin if(hp1_delay>0) hp1_delay<=hp1_delay-1;else begin hp1_bvalid<=1;hp1_bid<=hp1_id;end end
  if(hp1_bvalid && hp1_bready) begin hp1_bvalid<=0;hp1_pending<=0;end
 end
end
always @(negedge clk_100m) if(control_rst_n) begin
 check(motion_step===ref_motion_step && motion_dir===ref_motion_dir && motion_en===ref_motion_en,"STEP/DIR/EN differential against unchanged motion controller");
 check(hp_arvalid===ref_hp_arvalid && hp_rready===ref_hp_rready,"HP0 controller unaffected");
end
