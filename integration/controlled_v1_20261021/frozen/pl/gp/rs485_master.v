// Isolated read-only SERVO42C collector. No motion/control command interface.
module rs485_master #(
 `include "parameters.vh"
)(
 input wire clk,rst_n,enable,input wire [4:0] query_mask,
 input wire [63:0] time_us,input wire rx,
 output wire tx,output reg de,
 input wire record_ready,output wire record_valid,output wire [255:0] record_data,
 output wire [31:0] fifo_level,dropped,
 output reg [31:0] accepted,errors,ignored_rx,
 output wire busy
);
 `include "rs485_defs.vh"
 localparam integer BIT_CYCLES=(CLK_HZ+BAUD/2)/BAUD;
 localparam [3:0] IDLE=0,QUIET=1,PRE=2,SEND=3,HOLD=4,TURN=5,RECEIVE=6,EMIT=7;
 reg [3:0] state;
 reg [3:0] slave_index;
 reg [2:0] query_index;
 reg [7:0] address,command,attempt,status;
 reg [3:0] length,rx_count;
 reg [1:0] tx_index;
 reg [7:0] sum,tx_data;
 reg [47:0] payload;
 reg [63:0] request_time,event_time;
 reg [31:0] request_seq,next_request_seq,timer,deadline,interbyte,poll_timer,quiet_timer;
 reg retry_pending,tx_start,tx_wait,push;
 reg [255:0] push_data;
 // synthesis translate_off
 integer check_index;
 initial begin
  if(CLK_HZ<=0 || BAUD<=0 || BIT_CYCLES<8 || SLAVE_COUNT<1 || SLAVE_COUNT>10 ||
     RETRIES<0 || RETRIES>255 || FIFO_DEPTH<2 || POLL_CYCLES<1 ||
     TIMEOUT_CYCLES<=TURN_CYCLES || INTERBYTE_CYCLES<1 || PRE_CYCLES<1 ||
     POST_CYCLES<1 || TURN_CYCLES<1 || QUIET_CYCLES<10*BIT_CYCLES ||
     TIMEOUT_CYCLES>32'h7fffffff-QUIET_CYCLES) $fatal(1,"invalid RS485 parameters");
  for(check_index=0;check_index<SLAVE_COUNT;check_index=check_index+1)
   if(SLAVE_ADDRS[check_index*8 +:8]<8'he0 || SLAVE_ADDRS[check_index*8 +:8]>8'he9)
    $fatal(1,"invalid slave address");
 end
 // synthesis translate_on
 wire tx_busy,tx_done,rx_valid,rx_framing,line_idle;
 wire [7:0] rx_data;
 // Quiet decoder catches and counts duplicates; TX/turn decoder is held clear.
 wire rx_enable=(state==RECEIVE)||(state==QUIET)||(state==IDLE);
 assign busy=(state!=IDLE)&&(state!=QUIET);
 uart_tx #(.BIT_CYCLES(BIT_CYCLES)) u_tx(clk,rst_n,tx_start,tx_data,tx,tx_busy,tx_done);
 uart_rx #(.BIT_CYCLES(BIT_CYCLES)) u_rx(clk,rst_n,rx_enable,rx,line_idle,rx_data,rx_valid,rx_framing);
 record_fifo #(.DEPTH(FIFO_DEPTH)) u_fifo(clk,rst_n,push,push_data,record_ready,record_valid,record_data,dropped,fifo_level);

 task fail;
  input [7:0] code;
  begin status<=code;event_time<=time_us;payload<=0;state<=EMIT;end
 endtask
 task advance_slot;
  begin
   if(query_index==4) begin query_index<=0;slave_index<=(slave_index==SLAVE_COUNT-1)?0:slave_index+1'b1;end
   else query_index<=query_index+1'b1;
  end
 endtask
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=QUIET;slave_index<=0;query_index<=0;address<=0;command<=0;length<=0;
   attempt<=0;status<=0;rx_count<=0;tx_index<=0;sum<=0;payload<=0;
   request_time<=0;event_time<=0;request_seq<=0;next_request_seq<=0;
   timer<=0;deadline<=TIMEOUT_CYCLES+QUIET_CYCLES;interbyte<=0;poll_timer<=0;quiet_timer<=QUIET_CYCLES;
   retry_pending<=0;tx_start<=0;tx_wait<=0;tx_data<=0;push<=0;push_data<=0;
   de<=0;accepted<=0;errors<=0;ignored_rx<=0;
  end else begin
   tx_start<=0;push<=0;
   if(poll_timer!=0) poll_timer<=poll_timer-1'b1;
   if(rx_enable && state!=RECEIVE && (rx_valid||rx_framing) && ignored_rx!=32'hffffffff)
    ignored_rx<=ignored_rx+1'b1;
   case(state)
    IDLE: begin
     if(!line_idle || rx_valid || rx_framing) begin state<=QUIET;quiet_timer<=QUIET_CYCLES;deadline<=TIMEOUT_CYCLES+QUIET_CYCLES;end
     else if(enable && query_mask!=0) begin
      if(!query_mask[query_index]) advance_slot;
      else if(poll_timer==0) begin
       address<=SLAVE_ADDRS[slave_index*8 +:8];command<=query_code(query_index);length<=query_length(query_index);
       attempt<=0;request_seq<=next_request_seq;next_request_seq<=next_request_seq+1'b1;
       request_time<=time_us;de<=1;timer<=PRE_CYCLES-1;state<=PRE;poll_timer<=POLL_CYCLES;
      end
     end
    end
    QUIET: begin
     if(!line_idle || rx_valid || rx_framing) quiet_timer<=QUIET_CYCLES;
     else if(quiet_timer!=0) quiet_timer<=quiet_timer-1'b1;
     if(deadline!=0) deadline<=deadline-1'b1;
     if(quiet_timer==0 && line_idle && !rx_valid && !rx_framing && poll_timer==0) begin
      if(retry_pending) begin de<=1;timer<=PRE_CYCLES-1;state<=PRE;poll_timer<=POLL_CYCLES;retry_pending<=0;end
      else state<=IDLE;
     end else if(deadline==0 && quiet_timer!=0) begin
      // No request sent on a continuously occupied bus; bounded skip event.
      if(retry_pending) begin retry_pending<=0;fail(`RS_STATUS_BUS_BUSY);end
      else if(enable && query_mask!=0) begin
       if(!query_mask[query_index]) advance_slot;
       else begin
        address<=SLAVE_ADDRS[slave_index*8 +:8];command<=query_code(query_index);length<=query_length(query_index);
        request_seq<=next_request_seq;next_request_seq<=next_request_seq+1'b1;request_time<=time_us;
        attempt<=0;fail(`RS_STATUS_BUS_BUSY);
       end
      end
     end
    end
    PRE: if(timer!=0) timer<=timer-1'b1;
         else begin tx_index<=0;tx_data<=address;tx_start<=1;tx_wait<=1;state<=SEND;end
    SEND: if(tx_done && tx_wait) begin
      if(tx_index==2) begin state<=HOLD;timer<=POST_CYCLES-1;tx_wait<=0;end
      else begin tx_index<=tx_index+1'b1;tx_data<=(tx_index==0)?command:(address+command);tx_start<=1;end
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
     if(rx_framing) fail(`RS_STATUS_FRAMING);
     else if(rx_valid) begin
      interbyte<=INTERBYTE_CYCLES;
      if(rx_count==0) begin
       if(rx_data!=address) fail(`RS_STATUS_ADDRESS);
       else begin sum<=rx_data;rx_count<=1;end
      end else if(rx_count==length+1) begin
       if(rx_data!=sum) fail(`RS_STATUS_CHECKSUM);
       else begin status<=`RS_STATUS_VALID;event_time<=time_us;state<=EMIT;end
      end else begin payload<={payload[39:0],rx_data};sum<=sum+rx_data;rx_count<=rx_count+1'b1;end
     end else if(deadline==0) fail((rx_count==0)?`RS_STATUS_TIMEOUT:`RS_STATUS_TRUNCATED);
     else if(rx_count!=0 && interbyte==0) fail(`RS_STATUS_TRUNCATED);
    end
    EMIT: begin
     push_data<={8'd`RS_VERSION,address,command,status,attempt,(status==`RS_STATUS_VALID?{4'd0,length}:8'd0),request_seq,request_time,event_time,payload};push<=1;
     if(status==0) begin if(accepted!=32'hffffffff) accepted<=accepted+1'b1;end
     else if(errors!=32'hffffffff) errors<=errors+1'b1;
     if(status!=0 && status!=`RS_STATUS_BUS_BUSY && attempt<RETRIES) begin attempt<=attempt+1'b1;retry_pending<=1;end
     else begin retry_pending<=0;advance_slot;end
     state<=QUIET;quiet_timer<=QUIET_CYCLES;deadline<=TIMEOUT_CYCLES+QUIET_CYCLES;
    end
    default: begin state<=QUIET;de<=0;quiet_timer<=QUIET_CYCLES;deadline<=TIMEOUT_CYCLES+QUIET_CYCLES;end
   endcase
  end
 end
 // Parameter guards above are simulation-only; deployment must validate profile.
endmodule

