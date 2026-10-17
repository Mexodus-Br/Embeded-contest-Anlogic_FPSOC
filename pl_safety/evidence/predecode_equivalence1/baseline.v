`timescale 1ns/1ps
`include "safety_defs.vh"
module baseline_regs(
 input wire clk,rst_n,
 input wire [32:0] s_awaddr,s_araddr,input wire [31:0] s_wdata,input wire [3:0] s_wstrb,
 input wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready,
 output wire s_awready,s_wready,s_arready,output reg s_bvalid,s_rvalid,
 output reg [1:0] s_bresp,s_rresp,output reg [31:0] s_rdata,
 input wire [255:0] config_hash,input wire config_ok,
 input wire [2047:0] live_snapshot,input wire [31:0] causes,
 input wire request_ok,clear_ok,home_done,home_cancelled,home_owner,pulse_safe,stopped,
 output wire home_request,clear_request,stop_request,irq
);
 localparam [32:0] BASE={1'b0,`SAF_BASE};
 reg ah,wh;reg [32:0] address;reg [31:0] data;reg [3:0] strobe;
 reg [31:0] opcode,arg,txn,last_id,last_opcode,last_arg;
 reg [31:0] ack_id,ack_error;reg ack_valid,ack_accepted,ack_complete,busy,cancel_pending;
 reg [31:0] pending,mask,snap_id;reg [2047:0] snapshot;reg snap_valid,ack_event;
 wire fire=ah && wh && !s_bvalid;
 wire hit=address[32:12]==BASE[32:12];
 wire full=address[1:0]==0 && strobe==15;
 wire [11:0] offset=address[11:0];
 wire same_payload=opcode==last_opcode && arg==last_arg;
 wire submit_valid=data==1 && txn!=0 && txn>=last_id &&
   (txn!=last_id || same_payload) && (!busy || txn==last_id);
 reg [1:0] response;
 always @*begin
  response=0;
  if(!hit)response=3;
  else if(!full)response=2;
  else case(offset)
   `SAF_REGISTERS_OPCODE,`SAF_REGISTERS_ARG,`SAF_REGISTERS_TXN:begin end
   `SAF_REGISTERS_STOP:if(data!=1)response=2;
   `SAF_REGISTERS_SUBMIT:if(!submit_valid)response=2;
   `SAF_REGISTERS_IRQ_PENDING,`SAF_REGISTERS_IRQ_MASK:if((data & ~32'hf)!=0)response=2;
   `SAF_REGISTERS_SNAP_REQ:if(data==0 || data<=snap_id)response=2;
   default:response=2;
  endcase
 end
 wire good=fire && response==0;
 wire submit=good && offset==`SAF_REGISTERS_SUBMIT && txn!=last_id;
 assign home_request=submit && opcode==`SAF_COMMANDS_HOME_START && arg==0;
 assign clear_request=submit && opcode==`SAF_COMMANDS_CLEAR_FAULT && arg==0;
 // Independent STOP does not depend on mailbox readiness or response mux.
 assign stop_request=fire && address==BASE+`SAF_REGISTERS_STOP && strobe==15 && data==1;
 assign s_awready=rst_n && !ah && !s_bvalid;
 assign s_wready=rst_n && !wh && !s_bvalid;
 assign s_arready=rst_n && !s_rvalid;
 assign irq=rst_n && |(pending & mask);
 wire [31:0] w1c=good && offset==`SAF_REGISTERS_IRQ_PENDING ? data:0;
 wire [31:0] events={(28'd0),stopped,ack_event,home_done,(|causes)};
 reg [31:0] read_data;reg read_known;
 integer word_index;
 always @*begin
  read_data=0;read_known=1;word_index=0;
  case(s_araddr[11:0])
   `SAF_REGISTERS_VERSION:read_data=`SAF_VERSION;
   `SAF_REGISTERS_PROFILE:read_data=`SAF_PROFILE;
   `SAF_REGISTERS_CAPS:read_data=`SAF_CAPS;
   `SAF_REGISTERS_FEATURES:read_data=`SAF_FEATURES;
   `SAF_REGISTERS_OPCODE:read_data=opcode;
   `SAF_REGISTERS_ARG:read_data=arg;
   `SAF_REGISTERS_TXN:read_data=txn;
   `SAF_REGISTERS_ACK_ID:read_data=ack_id;
   `SAF_REGISTERS_ACK_STATUS:read_data={27'd0,snap_valid,busy,ack_complete,ack_accepted,ack_valid};
   `SAF_REGISTERS_ACK_ERROR:read_data=ack_error;
   `SAF_REGISTERS_IRQ_PENDING:read_data=pending;
   `SAF_REGISTERS_IRQ_MASK:read_data=mask;
   `SAF_REGISTERS_SNAP_REQ:read_data=snap_id;
   `SAF_REGISTERS_CONFIG_VALID:read_data={31'd0,config_ok};
   default:begin
    if(s_araddr[11:0]>=`SAF_REGISTERS_CONFIG_ID_0 && s_araddr[11:0]<=`SAF_REGISTERS_CONFIG_ID_7)begin
     word_index=(s_araddr[11:0]-`SAF_REGISTERS_CONFIG_ID_0)>>2;read_data=config_hash[word_index*32+:32];
    end else if(s_araddr[11:0]>=`SAF_SNAPSHOT_BASE && s_araddr[11:0]<`SAF_SNAPSHOT_BASE+`SAF_SNAPSHOT_WORDS*4)begin
     word_index=(s_araddr[11:0]-`SAF_SNAPSHOT_BASE)>>2;read_data=snap_valid ? snapshot[word_index*32+:32]:0;
    end else read_known=0;
   end
  endcase
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   ah<=0;wh<=0;address<=0;data<=0;strobe<=0;s_bvalid<=0;s_bresp<=0;s_rvalid<=0;s_rresp<=0;s_rdata<=0;
   opcode<=0;arg<=0;txn<=0;last_id<=0;last_opcode<=0;last_arg<=0;
   ack_id<=0;ack_error<=0;ack_valid<=0;ack_accepted<=0;ack_complete<=0;busy<=0;cancel_pending<=0;
   pending<=0;mask<=0;snap_id<=0;snapshot<=0;snap_valid<=0;ack_event<=0;
  end else begin
   ack_event<=0;pending<=(pending & ~w1c)|events;
   if(s_awvalid && s_awready)begin ah<=1;address<=s_awaddr;end
   if(s_wvalid && s_wready)begin wh<=1;data<=s_wdata;strobe<=s_wstrb;end
   if(s_bvalid && s_bready)s_bvalid<=0;
   if(fire)begin
    ah<=0;wh<=0;s_bvalid<=1;s_bresp<=response;
    if(good)case(offset)
     `SAF_REGISTERS_OPCODE:opcode<=data;
     `SAF_REGISTERS_ARG:arg<=data;
     `SAF_REGISTERS_TXN:txn<=data;
     `SAF_REGISTERS_IRQ_MASK:mask<=data;
     `SAF_REGISTERS_SNAP_REQ:begin
      snapshot<=live_snapshot;snapshot[`SAF_SNAPSHOT_SNAP_ID*32+:32]<=data;snap_id<=data;snap_valid<=1;
     end
     default:begin end
    endcase
   end
   if(submit)begin
    last_id<=txn;last_opcode<=opcode;last_arg<=arg;ack_id<=txn;ack_valid<=1;ack_event<=1;
    ack_accepted<=(home_request && request_ok) || (clear_request && clear_ok);
    ack_error<=((home_request && request_ok) || (clear_request && clear_ok)) ? `SAF_ERRORS_OK:`SAF_ERRORS_REJECTED;
    ack_complete<=!(home_request && request_ok);busy<=home_request && request_ok;cancel_pending<=0;
   end
   if(busy && home_cancelled)cancel_pending<=1;
   if(busy && home_done)begin busy<=0;ack_complete<=1;ack_event<=1;end
   if(busy && cancel_pending && !home_owner && pulse_safe)begin
    busy<=0;ack_complete<=1;ack_error<=`SAF_ERRORS_CANCELLED;ack_event<=1;cancel_pending<=0;
   end
   if(s_rvalid && s_rready)s_rvalid<=0;
   if(s_arvalid && s_arready)begin
    s_rvalid<=1;s_rdata<=read_data;
    s_rresp<=s_araddr[32:12]!=BASE[32:12] ? 3 : (s_araddr[1:0]!=0 || !read_known ? 2:0);
   end
  end
 end
endmodule
