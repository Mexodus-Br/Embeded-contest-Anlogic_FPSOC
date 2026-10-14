// Atomic compact snapshot. Derived words use only frozen inputs, never live state.
module rs485_latest_cache #(parameter integer SLAVE_COUNT=3,parameter [79:0] SLAVE_ADDRS=80'he2e1e0)(
 input wire clk,rst_n,input wire [63:0] time_us,input wire [31:0] collector_generation,
 input wire event_valid,input wire [255:0] event_raw,input wire [31:0] event_generation,event_revision,
 input wire [159:0] active_period_us,input wire [4:0] active_mask,
 input wire snapshot_capture,input wire [8:0] snapshot_word,output reg [31:0] snapshot_data,
 output reg [31:0] parse_errors);
 `include "telem_defs.vh"
 wire [5:0] task_index;wire formed,valid,known;wire [63:0] signed_value;wire [31:0] carry;wire [15:0] value;wire [7:0] enum_raw;
 rs485_light_parse #(.SLAVE_COUNT(SLAVE_COUNT),.SLAVE_ADDRS(SLAVE_ADDRS)) parser(event_raw,task_index,formed,valid,known,signed_value,carry,value,enum_raw);
 localparam integer TASKS=SLAVE_COUNT*5;
 localparam integer ROW_BITS=676;
 reg [255:0] good[0:TASKS-1],last[0:TASKS-1];
 reg [31:0] good_gen[0:TASKS-1],good_rev[0:TASKS-1],last_gen[0:TASKS-1],last_rev[0:TASKS-1],updates[0:TASKS-1];
 reg seen[0:TASKS-1],last_seen[0:TASKS-1],last_valid[0:TASKS-1],known_enum[0:TASKS-1];
 // Packed storage avoids the tool's unpacked full-row snapshot optimization bug.
 reg [`RT_ROWS*ROW_BITS-1:0] frozen;
 reg [63:0] frozen_time;reg [169:0] frozen_limits;reg [4:0] frozen_disabled;
 reg [31:0] generation;
 wire [3:0] row_index=snapshot_word[8:5];wire [4:0] word_index=snapshot_word[4:0];
 wire [ROW_BITS-1:0] row=frozen[row_index*ROW_BITS+:ROW_BITS];
 wire [255:0] raw=row[255:0];wire [3:0] row_flags=row[675:672];
 // 3*u32 needs exactly 34 bits; explicitly sized add/shift avoids 64-bit DSPs.
 wire [63:0] limit={30'd0,frozen_limits[(row_index%5)*34+:34]};
 wire disabled=frozen_disabled[row_index%5];
 wire [63:0] age=frozen_time-raw[111:48];
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
  if(snapshot_word<`RT_ROWS*32) begin
   if(row_index<TASKS) begin
    case(word_index)
     0:snapshot_data={26'd0,disabled,(!row_flags[0] || disabled || age>=limit),row_flags};
     1:snapshot_data={16'd0,SLAVE_ADDRS[(row_index/5)*8+:8],raw[239:232]};
     2,3,4,5,6:snapshot_data=row[512+(word_index-2)*32+:32];
     7:snapshot_data=0;
     24:snapshot_data=decoded[31:0];
     25:snapshot_data=decoded[63:32];
     26:snapshot_data=raw[47:16];
     27:snapshot_data={7'd0,decoded_known,raw[7:0],raw[15:0]};
     28:snapshot_data=age[31:0];29:snapshot_data=age[63:32];
     30:snapshot_data=limit[31:0];31:snapshot_data=limit[63:32];
     default:if(word_index<16) snapshot_data=row[(word_index-8)*32+:32];
             else snapshot_data=row[256+(word_index-16)*32+:32];
    endcase
   end
  end
 end
 integer i;reg [33:0] three_period;reg [3:0] flags;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin generation<=0;parse_errors<=0;
   for(i=0;i<TASKS;i=i+1) begin seen[i]<=0;last_seen[i]<=0;last_valid[i]<=0;known_enum[i]<=0;good[i]<=0;last[i]<=0;good_gen[i]<=0;good_rev[i]<=0;last_gen[i]<=0;last_rev[i]<=0;updates[i]<=0;end
  end else begin
   generation<=collector_generation;
   if(generation!=collector_generation) begin
    for(i=0;i<TASKS;i=i+1) begin seen[i]<=0;last_seen[i]<=0;last_valid[i]<=0;known_enum[i]<=0;updates[i]<=0;end
   end else if(event_valid && event_generation==collector_generation) begin
    if(!formed) begin if(parse_errors!=32'hffffffff) parse_errors<=parse_errors+1'b1;end
    else begin
     last[task_index]<=event_raw;last_gen[task_index]<=event_generation;last_rev[task_index]<=event_revision;last_seen[task_index]<=1;last_valid[task_index]<=valid;
     if(valid) begin
      good[task_index]<=event_raw;good_gen[task_index]<=event_generation;good_rev[task_index]<=event_revision;seen[task_index]<=1;known_enum[task_index]<=known;
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
    for(i=0;i<`RT_ROWS;i=i+1) frozen[i*ROW_BITS+:ROW_BITS]<=0;
    for(i=0;i<TASKS;i=i+1) begin
     flags={known_enum[i] && seen[i] && generation==collector_generation,
            last_valid[i] && last_seen[i] && generation==collector_generation,
            last_seen[i] && generation==collector_generation,seen[i] && generation==collector_generation};
     frozen[i*ROW_BITS+:ROW_BITS]<={flags,updates[i],last_rev[i],last_gen[i],good_rev[i],good_gen[i],last[i],good[i]};
    end
   end
  end
 end
endmodule
