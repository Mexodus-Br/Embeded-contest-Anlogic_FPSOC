task send_bytes;input integer size,send_last;integer x,z;
 begin
  for(x=0;x<size;x=x+8) begin
   @(negedge clk_100m);for(z=0;z<8;z=z+1) stream_data[z*8+:8]=(x+z)^8'h5a;
   stream_keep=255;stream_last=send_last && x+8==size;stream_valid=1;
   @(posedge clk_100m);while(!stream_ready && stream_rst_n) @(posedge clk_100m);
   @(negedge clk_100m);stream_valid=0;
  end
 end
endtask
task reset_rx;
 begin
  stream_valid=0;write_reg(BASE+48,4,15,0,0);polls=0;status_value=4;
  while(status_value[2] && polls<1000) begin read_reg(BASE+48,0,status_value);polls=polls+1;end
  check(!status_value[2],"independent reset complete");repeat(30) @(negedge clk_100m);
 end
endtask
task receive_case;input integer btt,size,last_flag,exact;integer x;reg [31:0] sr,actual;
 begin
  for(x=0;x<2048;x=x+1) memory[69632+x]=8'hcc;
  write_reg(BASE+48,32'h5001,15,0,0);write_reg(BASE+72,69632,15,0,0);write_reg(BASE+88,btt,15,0,0);
  send_bytes(size,last_flag);polls=0;sr=0;
  while(!(sr[12] || (sr&32'h770)!=0) && polls<200) begin read_reg(BASE+52,0,sr);polls=polls+1;end
  read_reg(BASE+88,0,actual);
  $display("PROBE BTT=%0d sent=%0d TLAST=%0d status=%h actual=%0d writes=%0d",btt,size,last_flag,sr,actual,write_beats);
  if(exact) begin
   check(sr[12] && (sr&32'h770)==0,"exact S2MM IOC");check(actual==size,"actual S2MM length");
   for(x=0;x<size;x=x+1) check(memory[69632+x]===((x^8'h5a)&255),"DDR bytes");
   check(memory[69632+size]==8'hcc,"DDR end guard");
  end
  reset_rx;
 end
endtask
initial begin
 clk_100m=0;arst_n=0;s_awaddr=0;s_araddr=0;s_awvalid=0;s_wvalid=0;s_bready=0;s_arvalid=0;s_rready=0;s_wdata=0;s_wstrb=0;
 hp_rdata=0;hp_rid=0;hp_rlast=0;hp_rvalid=0;hp_bid=0;hp_bvalid=0;stream_data=0;stream_keep=0;stream_last=0;stream_valid=0;
 reset_design;repeat(100) @(negedge clk_100m);check(stream_rst_n,"S2MM-only primary release");
 read_reg(BASE,2,status_value);write_reg(BASE+40,64,15,2,0);
 receive_case(64,64,1,1);receive_case(1024,1024,1,1);receive_case(1024,64,1,1);
 receive_case(64,128,1,0);receive_case(128,64,0,0);
 receive_case(192,192,1,1);
 check(read_beats==0,"S2MM-only no HP reads");check(hp_idle,"all HP write responses drained");
 $display("PASS telemetry_real_s2mm checks=%0d DDR writes=%0d no HP reads",checks,write_beats);$finish;
end
