`timescale 1ns/1ps
module tb_telemetry;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,dma_ready=0,dma_quiescent=1;reg [63:0] time_us=0;
 // Accelerated externally supplied time for wrap/age/flush tests, no RTL epoch.
 always @(posedge clk) time_us<=time_us+1;
 reg event_valid=0;reg [255:0] event_raw=0;reg [31:0] generation=0,revision=2;
 reg [159:0] periods={5{32'd50000}};reg [4:0] mask=31;
 `include "telemetry_bfm.vh"
 wire diag_valid;wire [255:0] diag_data;wire [31:0] diag_level,diag_drop;
 record_fifo #(.DEPTH(8)) diagnostic(clk,rst_n && generation==0,event_valid,event_raw,1'b0,diag_valid,diag_data,diag_drop,diag_level);
 wire irq;wire [63:0] m_data;wire [7:0] m_keep;wire m_last,m_valid;reg m_ready=0;
 rs485_telem_top dut(.clk(clk),.rst_n(rst_n),.dma_ready(dma_ready),.dma_quiescent(dma_quiescent),.time_us(time_us),.event_valid(event_valid),.event_raw(event_raw),.collector_generation(generation),.event_revision(revision),.active_period_us(periods),.active_mask(mask),
 .s_awaddr(s_awaddr),.s_araddr(s_araddr),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_awvalid(s_awvalid),.s_wvalid(s_wvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_rready(s_rready),.s_awready(s_awready),.s_wready(s_wready),.s_bvalid(s_bvalid),.s_arready(s_arready),.s_rvalid(s_rvalid),.s_bresp(s_bresp),.s_rresp(s_rresp),.s_rdata(s_rdata),.irq(irq),.m_data(m_data),.m_keep(m_keep),.m_last(m_last),.m_valid(m_valid),.m_ready(m_ready));
 task emit;input [7:0] addr,q,status,len;input [47:0] payload;input [31:0] seq;
  begin ticks(1);event_raw={8'd1,addr,q,status,8'd1,len,seq,time_us-64'd10,time_us,payload};event_valid=1;ticks(1);event_valid=0;end
 endtask
 task snap;input [31:0] id;begin wr(`RT_REG_SNAP_REQ_ID,id,15,0);wr(`RT_REG_SNAP_SUBMIT,1,15,0);end endtask
 task recover_to;input [31:0] gen;
  begin wr(`RT_REG_RECOVER_GEN,gen,15,0);wr(`RT_REG_RECOVER,1,15,0);wr(`RT_REG_ENABLE,1,15,0);end
 endtask
 task arm_packet;input [31:0] id,gen,bytes;
  begin wr(`RT_REG_ARM_ID,id,15,0);wr(`RT_REG_ARM_GEN,gen,15,0);wr(`RT_REG_ARM_BYTES,bytes,15,0);wr(`RT_REG_ARM,1,15,0);end
 endtask
 task acknowledge;input [31:0] id,gen;
  begin wr(`RT_REG_COMPLETE_ID,id,15,0);wr(`RT_REG_COMPLETE_GEN,gen,15,0);wr(`RT_REG_COMPLETE_RESULT,0,15,0);wr(`RT_REG_COMPLETE,1,15,0);end
 endtask
 reg [511:0] frame;reg [63:0] held;reg held_last,blocked=0;integer beats=0,frames=0,packets=0;integer vectors;initial vectors=$fopen("frames.hex","w");
 reg [31:0] crc;integer j;reg [7:0] b;
 always @(posedge clk) if(rst_n && dma_ready) begin
  if(blocked && (!m_valid || m_data!==held || m_last!==held_last || m_keep!=255)) $fatal(1,"AXIS stalled stability");
  blocked=m_valid&&!m_ready;held=m_data;held_last=m_last;
  if(m_valid && m_ready) begin
   frame[beats*64+:64]=m_data;if(m_keep!=255) $fatal(1,"KEEP");
   if(beats==7) begin
    crc=32'hffffffff;
    for(j=0;j<60;j=j+1) begin b=frame[j*8+:8];crc=crc^b;repeat(8) crc=crc[0]?(crc>>1)^32'hedb88320:crc>>1;end
    if(frame[511:480]!=(crc^32'hffffffff) || frame[31:0]!=`RT_RECORD_MAGIC || frame[63:48]!=64 || frame[47:32]!=1) $fatal(1,"CRC/record format");
    if(frame[159:128]!=dut.transport.transport_generation) $fatal(1,"transport tag");
    $fdisplay(vectors,"%0128h",frame);frames=frames+1;beats=0;
   end else begin if(m_last) $fatal(1,"half record TLAST");beats=beats+1;end
   if(m_last) packets=packets+1;
  end
 end else blocked=0;
 integer n,q;reg [7:0] query,len;reg [47:0] payload;reg [31:0] v,id;
 reg step=0,ref_step=0;always @(posedge clk) begin step<=~step;ref_step<=~ref_step;end
 always @(negedge clk) if(step!==ref_step) $fatal(1,"STEP isolation");
 initial begin
  ticks(5);rst_n=1;ticks(3);dma_ready=1;ticks(3);recover_to(1);
  // All 15 slots, signed boundaries and raw unknown enum.
  for(n=0;n<3;n=n+1) for(q=0;q<5;q=q+1) begin
   case(q) 0:begin query=8'h30;len=6;payload=48'hffffffff8000;end
    1:begin query=8'h33;len=4;payload=48'h000080000000;end
    2:begin query=8'h39;len=2;payload=48'h000000008000;end
    3:begin query=8'h3a;len=1;payload=2;end
    4:begin query=8'h3e;len=1;payload=8'h80;end endcase
   emit(8'he0+n,query,0,len,payload,n*5+q);
  end
  snap(1);eq(`RT_ROW_BASE+`RT_ROW_CARRY,32'hffffffff);eq(`RT_ROW_BASE+`RT_ROW_VALUE_ENUM,32'h00008000);
  eq(`RT_ROW_BASE+`RT_ROW_STRIDE+`RT_ROW_SIGNED,32'h80000000);eq(`RT_ROW_BASE+`RT_ROW_STRIDE+`RT_ROW_SIGNED+4,32'hffffffff);
  eq(`RT_ROW_BASE+2*`RT_ROW_STRIDE+`RT_ROW_SIGNED,32'hffff8000);eq(`RT_ROW_BASE+3*`RT_ROW_STRIDE+`RT_ROW_FLAGS,15);
  eq(`RT_ROW_BASE+4*`RT_ROW_STRIDE+`RT_ROW_FLAGS,7);eq(`RT_ROW_BASE+`RT_ROW_VALID_REVISION,2);
  revision=9;emit(8'he0,8'h30,3,0,0,99);snap(2);eq(`RT_ROW_BASE+`RT_ROW_FLAGS,3);eq(`RT_ROW_BASE+`RT_ROW_CARRY,32'hffffffff);eq(`RT_ROW_BASE+`RT_ROW_VALID_REVISION,2);eq(`RT_ROW_BASE+`RT_ROW_RESULT_REVISION,9);
  // Freeze full batch, no RX credit: never assert VALID; overflow cannot stop cache.
  wait(dut.transport.state==1);rd(`RT_REG_PACKET_ID,0,id);eq(`RT_REG_PACKET_COUNT,16);
  for(n=0;n<260;n=n+1) emit(8'he1,8'h39,0,2,n,n);
  if(m_valid) $fatal(1,"sent without buffer credit");eq(`RT_REG_FIFO_LEVEL,256);eq(`RT_REG_FULL_DROP,20);
  if(diag_level!=8 || diag_drop!=268) $fatal(1,"independent diagnostic FIFO drops");
  snap(3);eq(`RT_ROW_BASE+7*`RT_ROW_STRIDE+`RT_ROW_SIGNED,259);

  wr(`RT_REG_IRQ_MASK,`RT_IRQ_PACKET_READY,15,0);wr(`RT_REG_IRQ_PENDING,31,15,0);
  rd(`RT_REG_IRQ_PENDING,0,v);if(!(v&`RT_IRQ_PACKET_READY) || !irq) $fatal(1,"persistent READY W1C set-wins");
  wr(`RT_REG_IRQ_MASK,0,15,0);if(irq) $fatal(1,"masked IRQ");
  wr(`RT_REG_IRQ_PENDING,31,15,0);rd(`RT_REG_IRQ_PENDING,0,v);if(!(v&1)) $fatal(1,"masked READY lost");
  wr(`RT_REG_IRQ_MASK,1,15,0);if(!irq) $fatal(1,"unmask pending source");wr(`RT_REG_IRQ_MASK,0,15,0);
  arm_packet(id,1,1024);wait(m_valid);ticks(30);if(!m_valid) $fatal(1,"held VALID");
  m_ready=1;wait(dut.transport.state==5);ticks(1);if(frames!=16 || packets!=1) $fatal(1,"batch");acknowledge(id,1);acknowledge(id,1);
  wr(`RT_REG_CANCEL,1,15,0);eq(`RT_REG_FIFO_LEVEL,0);recover_to(2);
  // A single record flushes without waiting for a full batch; exact short BTT.
  time_us=64'hfffffffffffffff0;emit(8'he0,8'h33,0,4,32'h7fffffff,100);time_us=64'd10020;
  wait(dut.transport.state==1);rd(`RT_REG_PACKET_ID,0,id);eq(`RT_REG_PACKET_BYTES,64);arm_packet(id,2,64);wait(dut.transport.state==5);acknowledge(id,2);
  snap(4);eq(`RT_ROW_BASE+`RT_ROW_STRIDE+`RT_ROW_SIGNED,32'h7fffffff);
  time_us=time_us+200000;snap(5);rd(`RT_ROW_BASE+`RT_ROW_STRIDE+`RT_ROW_FLAGS,0,v);if(!(v&`RT_FLAG_STALE)) $fatal(1,"stale age");
  mask=0;snap(6);rd(`RT_ROW_BASE+`RT_ROW_STRIDE+`RT_ROW_FLAGS,0,v);if(!(v&`RT_FLAG_DISABLED)) $fatal(1,"disabled");mask=31;
  // Cancel held VALID cannot retract or change payload; only primary reset fences.
  emit(8'he0,8'h3a,0,1,1,101);time_us=time_us+10010;wait(dut.transport.state==1);rd(`RT_REG_PACKET_ID,0,id);m_ready=0;arm_packet(id,2,64);wait(m_valid);wr(`RT_REG_CANCEL,1,15,0);ticks(20);if(!m_valid) $fatal(1,"cancel retracted VALID");
  dma_ready=0;ticks(3);dma_ready=1;beats=0;ticks(3);eq(`RT_REG_FIFO_LEVEL,0);wr(`RT_REG_ARM,1,15,2);
  dma_quiescent=0;wr(`RT_REG_RECOVER_GEN,3,15,0);wr(`RT_REG_RECOVER,1,15,2);dma_quiescent=1;recover_to(3);
  snap(7);rd(`RT_ROW_BASE+`RT_ROW_STRIDE+`RT_ROW_FLAGS,0,v);if(!(v&1)) $fatal(1,"DMA reset cleared cache");
  generation=1;ticks(3);snap(8);rd(`RT_ROW_BASE+`RT_ROW_STRIDE+`RT_ROW_FLAGS,0,v);if(v&3) $fatal(1,"collector reset cache valid");
  // Unknown address/query/malformed length never overwrites valid rows.
  emit(8'hf0,8'h39,0,2,5,0);emit(8'he0,8'h36,0,2,5,0);emit(8'he0,8'h30,0,5,5,0);eq(`RT_REG_PARSE_ERRORS,3);
  wr(`RT_REG_IRQ_MASK,31,15,0);wr(`RT_REG_IRQ_PENDING,31,15,0);
  rd_abs(33'h180800000,3,3,v);wr(`RT_REG_VERSION,1,15,2);wr(`RT_REG_ARM,1,1,2);

  wr(`RT_REG_IRQ_MASK,`RT_IRQ_FAULT,15,0);wr(`RT_REG_IRQ_PENDING,31,15,0);eq(`RT_REG_IRQ_PENDING,0);
  fork
   wr(`RT_REG_IRQ_PENDING,`RT_IRQ_FAULT,15,0);
   begin wait(dut.regs.wf && dut.regs.wa[11:0]==`RT_REG_IRQ_PENDING);dma_ready=0;end
  join
  ticks(3);eq(`RT_REG_IRQ_PENDING,`RT_IRQ_FAULT);if(!irq) $fatal(1,"edge fault lost to W1C");
  wr(`RT_REG_IRQ_PENDING,`RT_IRQ_FAULT,15,0);if(irq) $fatal(1,"fault source cleared");
  wr(`RT_REG_IRQ_MASK,0,15,0);dma_ready=1;ticks(3);dma_ready=0;ticks(3);
  eq(`RT_REG_IRQ_PENDING,`RT_IRQ_FAULT);if(irq) $fatal(1,"masked edge fault");
  wr(`RT_REG_IRQ_MASK,`RT_IRQ_FAULT,15,0);if(!irq) $fatal(1,"edge rearm");
  wr(`RT_REG_IRQ_PENDING,`RT_IRQ_FAULT,15,0);if(irq) $fatal(1,"edge W1C");
  $display("PASS telemetry IRQ unit checks=%0d frames=%0d packets=%0d parser/cache/drop/CRC/credit/cancel/wrap",checks,frames,packets);$finish;
 end
 initial begin #5000000;$fatal(1,"telemetry unit watchdog");end
endmodule
