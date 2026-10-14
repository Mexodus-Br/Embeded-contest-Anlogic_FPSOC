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
 reg [255:0] good[0:TASKS-1],last[0:TASKS-1];reg [31:0] good_gen[0:TASKS-1],good_rev[0:TASKS-1],last_gen[0:TASKS-1],last_rev[0:TASKS-1],updates[0:TASKS-1];
 reg seen[0:TASKS-1],last_seen[0:TASKS-1],last_valid[0:TASKS-1],known_enum[0:TASKS-1];
 reg [63:0] parsed[0:TASKS-1];reg [31:0] packed_value[0:TASKS-1];
 reg [`RT_ROWS*1024-1:0] snapshot;reg [31:0] generation;
 integer i,j;reg [63:0] age,limit;reg disabled;reg [31:0] flags;
 always @* snapshot_data=snapshot_word<`RT_ROWS*32?snapshot[(snapshot_word)*32+:32]:0;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin generation<=0;parse_errors<=0;
   for(i=0;i<TASKS;i=i+1) begin seen[i]<=0;last_seen[i]<=0;last_valid[i]<=0;known_enum[i]<=0;good[i]<=0;last[i]<=0;good_gen[i]<=0;good_rev[i]<=0;last_gen[i]<=0;last_rev[i]<=0;updates[i]<=0;parsed[i]<=0;packed_value[i]<=0;end
  end else begin
   generation<=collector_generation;
   if(generation!=collector_generation) begin
    for(i=0;i<TASKS;i=i+1) begin seen[i]<=0;last_seen[i]<=0;last_valid[i]<=0;known_enum[i]<=0;updates[i]<=0;end
   end else if(event_valid && event_generation==collector_generation) begin
    if(!formed) begin if(parse_errors!=32'hffffffff) parse_errors<=parse_errors+1'b1;end
    else begin
     last[task_index]<=event_raw;last_gen[task_index]<=event_generation;last_rev[task_index]<=event_revision;last_seen[task_index]<=1;last_valid[task_index]<=valid;
     if(valid) begin
      good[task_index]<=event_raw;good_gen[task_index]<=event_generation;good_rev[task_index]<=event_revision;seen[task_index]<=1;known_enum[task_index]<=known;parsed[task_index]<=signed_value;
      packed_value[task_index]<={7'd0,known,enum_raw,value};
      if(updates[task_index]!=32'hffffffff) updates[task_index]<=updates[task_index]+1'b1;
     end
    end
   end
   if(snapshot_capture) begin
    for(i=0;i<`RT_ROWS*32;i=i+1) snapshot[(i)*32+:32]<=0;
    for(i=0;i<TASKS;i=i+1) begin
     age=time_us-good[i][111:48];limit={32'd0,active_period_us[(i%5)*32+:32]}*`RT_STALE_PERIODS;
     if(limit<`RT_STALE_FLOOR_US) limit=`RT_STALE_FLOOR_US;
     disabled=!active_mask[i%5] || active_period_us[(i%5)*32+:32]==0;
     flags=((seen[i] && generation==collector_generation)?`RT_FLAG_VALID_SEEN:0)|((last_seen[i] && generation==collector_generation)?`RT_FLAG_RESULT_SEEN:0)|
       ((last_valid[i] && last_seen[i] && generation==collector_generation)?`RT_FLAG_RESULT_VALID:0)|((known_enum[i] && seen[i] && generation==collector_generation)?`RT_FLAG_ENUM_KNOWN:0)|
       ((!seen[i] || generation!=collector_generation || disabled || age>=limit)?`RT_FLAG_STALE:0)|(disabled?`RT_FLAG_DISABLED:0);
     snapshot[(i*32+`RT_ROW_FLAGS/4)*32+:32]<=flags;snapshot[(i*32+`RT_ROW_ADDRESS_QUERY/4)*32+:32]<={16'd0,SLAVE_ADDRS[(i/5)*8+:8],good[i][239:232]};
     snapshot[(i*32+`RT_ROW_VALID_GENERATION/4)*32+:32]<=good_gen[i];snapshot[(i*32+`RT_ROW_VALID_REVISION/4)*32+:32]<=good_rev[i];
     snapshot[(i*32+`RT_ROW_RESULT_GENERATION/4)*32+:32]<=last_gen[i];snapshot[(i*32+`RT_ROW_RESULT_REVISION/4)*32+:32]<=last_rev[i];snapshot[(i*32+`RT_ROW_UPDATES/4)*32+:32]<=updates[i];
     for(j=0;j<8;j=j+1) begin snapshot[(i*32+`RT_ROW_VALID_RAW/4+j)*32+:32]<=good[i][j*32+:32];snapshot[(i*32+`RT_ROW_RESULT_RAW/4+j)*32+:32]<=last[i][j*32+:32];end
     snapshot[(i*32+`RT_ROW_SIGNED/4)*32+:32]<=parsed[i][31:0];snapshot[(i*32+`RT_ROW_SIGNED/4+1)*32+:32]<=parsed[i][63:32];
     snapshot[(i*32+`RT_ROW_CARRY/4)*32+:32]<=good[i][47:16];snapshot[(i*32+`RT_ROW_VALUE_ENUM/4)*32+:32]<=packed_value[i];
     snapshot[(i*32+`RT_ROW_AGE/4)*32+:32]<=age[31:0];snapshot[(i*32+`RT_ROW_AGE/4+1)*32+:32]<=age[63:32];snapshot[(i*32+`RT_ROW_STALE_LIMIT/4)*32+:32]<=limit[31:0];snapshot[(i*32+`RT_ROW_STALE_LIMIT/4+1)*32+:32]<=limit[63:32];
    end
   end
  end
 end
endmodule
