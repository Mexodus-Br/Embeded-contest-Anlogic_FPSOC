// Whitelisted single logical request engine; owns DE, retries and bus guards.
// UART/FIFO layout is shared with v1. No motion or arbitrary command inputs.
module rs485_transaction #(
 `include "parameters.vh"
 ,parameter INTERLOCK_PREDECODE=0,parameter [79:0] PROTECTION_ADDRS=0
 ,parameter integer NORMAL_CYCLES=QUIET_CYCLES,ERROR_CYCLES=QUIET_CYCLES
)(input wire clk,rst_n,input wire [63:0] time_us,input wire rx,
 input wire request_valid,output wire request_ready,input wire [7:0] request_address,
 input wire [2:0] request_query,input wire [31:0] request_sequence,
 output wire tx,output reg de,output reg active,done,
 output reg [7:0] result,output reg bus_blocked,
 output reg push,output reg [255:0] push_data,
 output reg [31:0] accepted,errors,ignored_rx,output reg [5:0] protection_decoded,input wire [63:0] next_round_reference,output reg [1:0] protection_time_valid);
 `include "rs485_defs.vh"
 localparam integer BIT_CYCLES=(CLK_HZ+BAUD/2)/BAUD;
 localparam [3:0] IDLE=0,QUIET=1,PRE=2,SEND=3,HOLD=4,TURN=5,RECEIVE=6,EMIT=7;
 reg [3:0] state;
 reg [31:0] timer,deadline,interbyte,poll_timer,quiet_timer;
 reg [7:0] address,command,attempt,status,sum,tx_data;
 reg [3:0] length,rx_count;
 reg [1:0] tx_index;
 reg [47:0] payload;
 reg [63:0] request_time,event_time;
 reg [31:0] request_seq;
 reg retry_pending,tx_start;
 // Capture the fixed-format decode on the SAME EMIT edge as push_data.
 // No FIFO/PS/DMA dependency and no additional detection pipeline stage.
 wire protection_known=command==query_code(3'd4) && status==`RS_STATUS_VALID &&
  length==query_length(3'd4) && payload[47:8]==0 && (payload[7:0]==1 || payload[7:0]==2);
 wire [2:0] protection_axes={address==PROTECTION_ADDRS[16+:8],
  address==PROTECTION_ADDRS[8+:8],address==PROTECTION_ADDRS[0+:8]} & {3{protection_known}};
 wire tx_busy,tx_done,rv,rf,line_idle;
 wire [7:0] rd;
 wire rx_enable=(state==IDLE)||(state==QUIET)||(state==RECEIVE);
 assign request_ready=state==IDLE && line_idle && !rv && !rf && poll_timer==0;
 uart_tx #(.BIT_CYCLES(BIT_CYCLES)) u_tx(clk,rst_n,tx_start,tx_data,tx,tx_busy,tx_done);
 uart_rx #(.BIT_CYCLES(BIT_CYCLES)) u_rx(clk,rst_n,rx_enable,rx,line_idle,rd,rv,rf);
 task fail;input [7:0] code;
  begin status<=code;event_time<=time_us;payload<=0;state<=EMIT;end
 endtask
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=QUIET;de<=0;active<=0;done<=0;result<=0;bus_blocked<=0;push<=0;push_data<=0;protection_decoded<=0;
   timer<=0;deadline<=ERROR_CYCLES+TIMEOUT_CYCLES;interbyte<=0;poll_timer<=0;quiet_timer<=ERROR_CYCLES;
   address<=0;command<=0;attempt<=0;status<=0;sum<=0;tx_data<=0;length<=0;rx_count<=0;tx_index<=0;
   payload<=0;request_time<=0;event_time<=0;request_seq<=0;retry_pending<=0;tx_start<=0;
   accepted<=0;errors<=0;ignored_rx<=0;
  end else begin
   done<=0;bus_blocked<=0;push<=0;tx_start<=0;
   if(poll_timer!=0) poll_timer<=poll_timer-1'b1;
   if(rx_enable && state!=RECEIVE && (rv||rf) && ignored_rx!=32'hffffffff) ignored_rx<=ignored_rx+1'b1;
   case(state)
    IDLE: begin
     if(!line_idle || rv || rf) begin state<=QUIET;quiet_timer<=ERROR_CYCLES;deadline<=ERROR_CYCLES+TIMEOUT_CYCLES;end
     else if(request_valid && request_ready) begin
      address<=request_address;command<=query_code(request_query);length<=query_length(request_query);
      request_seq<=request_sequence;request_time<=time_us;attempt<=0;active<=1;
      de<=1;timer<=PRE_CYCLES-1;state<=PRE;poll_timer<=POLL_CYCLES;
     end
    end
    QUIET: begin
     if(!line_idle || rv || rf) quiet_timer<=(status==0 && active && !retry_pending)?NORMAL_CYCLES:ERROR_CYCLES;
     else if(quiet_timer!=0) quiet_timer<=quiet_timer-1'b1;
     if(deadline!=0) deadline<=deadline-1'b1;
     if(quiet_timer==0 && line_idle && !rv && !rf && poll_timer==0) begin
      if(retry_pending) begin retry_pending<=0;de<=1;timer<=PRE_CYCLES-1;state<=PRE;poll_timer<=POLL_CYCLES;end
      else begin state<=IDLE;if(active) begin active<=0;done<=1;result<=status;end end
     end else if(deadline==0 && quiet_timer!=0) begin
      bus_blocked<=1;
      if(retry_pending) begin retry_pending<=0;fail(`RS_STATUS_BUS_BUSY);end
      else begin
       if(active) begin active<=0;done<=1;result<=status;end
       quiet_timer<=ERROR_CYCLES;deadline<=ERROR_CYCLES+TIMEOUT_CYCLES;
       // Stay receive-only on occupied bus; no phantom requests/node failures.
      end
     end
    end
    PRE: if(timer!=0) timer<=timer-1'b1;
     else begin tx_index<=0;tx_data<=address;tx_start<=1;state<=SEND;end
    SEND: if(tx_done) begin
     if(tx_index==2) begin state<=HOLD;timer<=POST_CYCLES-1;end
     else begin tx_index<=tx_index+1'b1;tx_data<=(tx_index==0)?command:address+command;tx_start<=1;end
    end
    HOLD: if(timer!=0) timer<=timer-1'b1;
     else begin de<=0;state<=TURN;timer<=TURN_CYCLES-1;deadline<=TIMEOUT_CYCLES;end
    TURN: begin
     if(deadline!=0) deadline<=deadline-1'b1;
     if(timer!=0) timer<=timer-1'b1;
     else begin state<=RECEIVE;rx_count<=0;sum<=0;payload<=0;interbyte<=INTERBYTE_CYCLES;end
    end
    RECEIVE: begin
     if(deadline!=0) deadline<=deadline-1'b1;
     if(interbyte!=0) interbyte<=interbyte-1'b1;
     if(rf) fail(`RS_STATUS_FRAMING);
     else if(rv) begin
      interbyte<=INTERBYTE_CYCLES;
      if(rx_count==0) begin
       if(rd!=address) fail(`RS_STATUS_ADDRESS);else begin sum<=rd;rx_count<=1;end
      end else if(rx_count==length+1) begin
       if(rd!=sum) fail(`RS_STATUS_CHECKSUM);else begin status<=`RS_STATUS_VALID;event_time<=time_us;state<=EMIT;end
      end else begin payload<={payload[39:0],rd};sum<=sum+rd;rx_count<=rx_count+1'b1;end
     end else if(deadline==0) fail(rx_count==0?`RS_STATUS_TIMEOUT:`RS_STATUS_TRUNCATED);
     else if(rx_count!=0 && interbyte==0) fail(`RS_STATUS_TRUNCATED);
    end
    EMIT: begin
     protection_decoded<=INTERLOCK_PREDECODE ?
       {protection_axes & {3{payload[7:0]==1}},protection_axes}:6'd0;
     push<=1;push_data<={8'd`RS_VERSION,address,command,status,attempt,(status==0?{4'd0,length}:8'd0),request_seq,request_time,event_time,payload};
     if(status==0) begin if(accepted!=32'hffffffff) accepted<=accepted+1'b1;end
     else if(errors!=32'hffffffff) errors<=errors+1'b1;
     if(status!=0 && status!=`RS_STATUS_BUS_BUSY && attempt<RETRIES) begin attempt<=attempt+1'b1;retry_pending<=1;end
     else retry_pending<=0;
     state<=QUIET;
     quiet_timer<=status==0?NORMAL_CYCLES:ERROR_CYCLES;
     deadline<=TIMEOUT_CYCLES+(status==0?NORMAL_CYCLES:ERROR_CYCLES);
    end
    default: begin state<=QUIET;de<=0;quiet_timer<=ERROR_CYCLES;deadline<=ERROR_CYCLES+TIMEOUT_CYCLES;end
   endcase
  end
 end

// Capture the SAME existing raw-record edge, with the round value that the
// monitor will hold after this edge. No extra push/detection stage. The two
// private bits need no reset: push already invalidates them asynchronously.
wire [63:0] request_round_age=request_time-next_round_reference;
wire [63:0] event_round_age=event_time-next_round_reference;
always @(posedge clk)if(state==EMIT)
 protection_time_valid<=INTERLOCK_PREDECODE ? {!event_round_age[63],!request_round_age[63]}:2'd0;
endmodule
