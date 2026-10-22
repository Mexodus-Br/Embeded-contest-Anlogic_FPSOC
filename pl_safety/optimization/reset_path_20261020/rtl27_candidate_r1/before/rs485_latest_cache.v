// Atomic snapshot by version references; three slots avoid cross-port collisions
// even when a read, replacement snapshot and event coincide. Read latency: 1 clk.
module rs485_latest_cache #(parameter integer SLAVE_COUNT=3,parameter [79:0] SLAVE_ADDRS=80'he2e1e0)(
 input wire clk,rst_n,input wire [63:0] time_us,input wire [31:0] collector_generation,
 input wire event_valid,input wire [255:0] event_raw,input wire [31:0] event_generation,event_revision,
 input wire [159:0] active_period_us,input wire [4:0] active_mask,
 input wire snapshot_capture,input wire [8:0] snapshot_word,output reg [31:0] snapshot_data,
 output reg [31:0] parse_errors);
 `include "telem_defs.vh"
 localparam integer TASKS=SLAVE_COUNT*5, META_BITS=170;
 wire [5:0] task_index;wire formed,valid,known;wire [63:0] signed_value;wire [31:0] carry;wire [15:0] value;wire [7:0] enum_raw;
 rs485_light_parse #(.SLAVE_COUNT(SLAVE_COUNT),.SLAVE_ADDRS(SLAVE_ADDRS)) parser(event_raw,task_index,formed,valid,known,signed_value,carry,value,enum_raw);
 (* ram_style="block" *) reg [255:0] good_memory[0:TASKS*3-1];
 (* ram_style="block" *) reg [255:0] last_memory[0:TASKS*3-1];
 reg [1:0] good_pointer[0:TASKS-1],last_pointer[0:TASKS-1];
 reg good_written[0:TASKS-1],last_written[0:TASKS-1];
 reg [31:0] good_gen[0:TASKS-1],good_rev[0:TASKS-1],last_gen[0:TASKS-1],last_rev[0:TASKS-1],updates[0:TASKS-1];
 reg seen[0:TASKS-1],last_seen[0:TASKS-1],last_valid[0:TASKS-1],known_enum[0:TASKS-1];
 // Snapshot metadata is small enough for simultaneous capture. Raw records are
 // immutable while referenced. No acquisition pause or background copy exists.
 reg [`RT_ROWS*META_BITS-1:0] frozen;
 reg [63:0] frozen_time;reg [169:0] frozen_limits;reg [4:0] frozen_disabled;
 reg [31:0] generation;
 function [1:0] free_slot;input [1:0] live,held;
  begin
   case(live)
    0:if(held==1) free_slot=2;else free_slot=1;
    1:if(held==0) free_slot=2;else free_slot=0;
    default:if(held==0) free_slot=1;else free_slot=0;
   endcase
  end
 endfunction
 wire [META_BITS-1:0] event_frozen=frozen[task_index*META_BITS+:META_BITS];
 wire [1:0] next_good=free_slot(good_pointer[task_index],event_frozen[1:0]);
 wire [1:0] next_last=free_slot(last_pointer[task_index],event_frozen[3:2]);
 wire [7:0] event_base={1'b0,task_index,1'b0}+{2'b0,task_index};
 wire write_record=rst_n && generation==collector_generation && event_valid && event_generation==collector_generation && formed;
 wire [3:0] read_row=snapshot_word[8:5];
 wire [META_BITS-1:0] selected_meta=frozen[read_row*META_BITS+:META_BITS];
 wire [3:0] safe_read_row=read_row<TASKS?read_row:4'd0;
 wire [5:0] read_base={1'b0,safe_read_row,1'b0}+{2'b0,safe_read_row};
 reg [255:0] read_good,read_last;
 reg [META_BITS-1:0] read_meta;reg [8:0] read_word;
 reg [63:0] read_time,read_limit;reg read_disabled;
 // Each RAM has one independent write and one clocked read. The writer avoids
 // BOTH live and old snapshot slots, including the snapshot replacement edge.
 always @(posedge clk) begin
  if(write_record) begin
   last_memory[event_base+{6'd0,next_last}]<=event_raw;
   if(valid) good_memory[event_base+{6'd0,next_good}]<=event_raw;
  end
  read_good<=good_memory[read_base+{4'd0,selected_meta[1:0]}];
  read_last<=last_memory[read_base+{4'd0,selected_meta[3:2]}];
  read_meta<=selected_meta;read_word<=snapshot_word;read_time<=frozen_time;
  read_limit<={30'd0,frozen_limits[(read_row%5)*34+:34]};read_disabled<=frozen_disabled[read_row%5];
 end
 wire [3:0] row_index=read_word[8:5];wire [4:0] word_index=read_word[4:0];
 wire [255:0] raw=read_meta[4]?read_good:256'd0;
 wire [255:0] result_raw=read_meta[5]?read_last:256'd0;
 wire [3:0] row_flags=read_meta[169:166];
 wire [63:0] age=read_time-raw[111:48];
 reg [63:0] decoded;
 wire decoded_known=(row_index%5>=3) && (raw[7:0]==1 || raw[7:0]==2);
 always @* begin
  case(row_index%5)
   0:decoded={{32{raw[47]}},raw[47:16]};
   1:decoded={{32{raw[31]}},raw[31:0]};
   2:decoded={{48{raw[15]}},raw[15:0]};
   default:decoded={56'd0,raw[7:0]};
  endcase
  snapshot_data=0;
  if(read_word<`RT_ROWS*32 && row_index<TASKS) begin
   case(word_index)
    0:snapshot_data={26'd0,read_disabled,(!row_flags[0] || read_disabled || age>=read_limit),row_flags};
    1:snapshot_data={16'd0,SLAVE_ADDRS[(row_index/5)*8+:8],raw[239:232]};
    2,3,4,5,6:snapshot_data=read_meta[6+(word_index-2)*32+:32];
    7:snapshot_data=0;
    24:snapshot_data=decoded[31:0];25:snapshot_data=decoded[63:32];
    26:snapshot_data=raw[47:16];27:snapshot_data={7'd0,decoded_known,raw[7:0],raw[15:0]};
    28:snapshot_data=age[31:0];29:snapshot_data=age[63:32];
    30:snapshot_data=read_limit[31:0];31:snapshot_data=read_limit[63:32];
    default:if(word_index<16) snapshot_data=raw[(word_index-8)*32+:32];
            else snapshot_data=result_raw[(word_index-16)*32+:32];
   endcase
  end
 end
 integer i;reg [33:0] three_period;reg [3:0] flags;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin generation<=0;parse_errors<=0;
   for(i=0;i<TASKS;i=i+1) begin
    seen[i]<=0;last_seen[i]<=0;last_valid[i]<=0;known_enum[i]<=0;
    good_pointer[i]<=0;last_pointer[i]<=0;good_written[i]<=0;last_written[i]<=0;
    good_gen[i]<=0;good_rev[i]<=0;last_gen[i]<=0;last_rev[i]<=0;updates[i]<=0;
   end
  end else begin
   generation<=collector_generation;
   if(generation!=collector_generation) begin
    for(i=0;i<TASKS;i=i+1) begin seen[i]<=0;last_seen[i]<=0;last_valid[i]<=0;known_enum[i]<=0;updates[i]<=0;end
   end else if(event_valid && event_generation==collector_generation) begin
    if(!formed) begin if(parse_errors!=32'hffffffff) parse_errors<=parse_errors+1'b1;end
    else begin
     last_pointer[task_index]<=next_last;last_written[task_index]<=1;
     last_gen[task_index]<=event_generation;last_rev[task_index]<=event_revision;last_seen[task_index]<=1;last_valid[task_index]<=valid;
     if(valid) begin
      good_pointer[task_index]<=next_good;good_written[task_index]<=1;
      good_gen[task_index]<=event_generation;good_rev[task_index]<=event_revision;seen[task_index]<=1;known_enum[task_index]<=known;
      if(updates[task_index]!=32'hffffffff) updates[task_index]<=updates[task_index]+1'b1;
     end
    end
   end
   if(snapshot_capture) begin
    frozen_time<=time_us;
    for(i=0;i<5;i=i+1) begin
     three_period={2'd0,active_period_us[i*32+:32]}+{1'd0,active_period_us[i*32+:32],1'b0};
     frozen_limits[i*34+:34]<=three_period<`RT_STALE_FLOOR_US ? `RT_STALE_FLOOR_US:three_period;
     frozen_disabled[i]<=!active_mask[i] || active_period_us[i*32+:32]==0;
    end
    for(i=0;i<`RT_ROWS;i=i+1) frozen[i*META_BITS+:META_BITS]<=0;
    for(i=0;i<TASKS;i=i+1) begin
     flags={known_enum[i] && seen[i] && generation==collector_generation,last_valid[i] && last_seen[i] && generation==collector_generation,
            last_seen[i] && generation==collector_generation,seen[i] && generation==collector_generation};
     frozen[i*META_BITS+:META_BITS]<={flags,updates[i],last_rev[i],last_gen[i],good_rev[i],good_gen[i],last_written[i],good_written[i],last_pointer[i],good_pointer[i]};
    end
   end
  end
 end
 // synthesis translate_off
 always @(posedge clk) if(write_record) begin
  if(next_last==event_frozen[3:2] || (valid && next_good==event_frozen[1:0])) $fatal(1,"write to frozen raw slot");
  if(snapshot_capture && (next_last==last_pointer[task_index] || (valid && next_good==good_pointer[task_index]))) $fatal(1,"write to newly captured slot");
 end
 // synthesis translate_on
endmodule
