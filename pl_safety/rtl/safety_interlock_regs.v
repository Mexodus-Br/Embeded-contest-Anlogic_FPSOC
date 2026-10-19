`timescale 1ns/1ps
`include "interlock_defs.vh"
// Extension of the existing safety AXI endpoint, using its captured AW/W fire.
// This module is not another AXI slave and owns no AXI response channel.
module safety_interlock_regs(
 input wire clk,rst_n,write_fire,input wire [11:0] write_offset,
 input wire [31:0] write_data,input wire [3:0] write_strobe,
 input wire [11:0] read_offset,
 output reg write_known,read_known,output reg [1:0] write_response,
 output reg [31:0] read_data,
 input wire config_ready,owner_open_ok,owner_close_ok,heartbeat_ok,
 input wire [63:0] owner_id,last_sequence,first_time,
 input wire [31:0] causes,first_cause,status,
 input wire [2:0] active_axes,input wire [31:0] active_feedback_us,active_watchdog_us,
 input wire [1023:0] live_snapshot,
 output reg config_apply,output wire config_pending,owner_open,owner_close,heartbeat_commit,
 output wire [2:0] committed_axes,
 output wire [31:0] committed_feedback_us,committed_watchdog_us,
 output reg [2:0] config_axes,
 output reg [31:0] config_feedback_us,config_watchdog_us,
 output reg [63:0] heartbeat_owner,heartbeat_sequence
);
 reg [31:0] config_txn,accepted_txn,applied_txn;
 reg [2:0] applied_axes,config_dirty;
 reg [31:0] applied_feedback,applied_watchdog;
 reg [3:0] heartbeat_dirty;
 reg [31:0] snapshot_id;reg [1023:0] snapshot;
 wire same_config=config_axes==applied_axes && config_feedback_us==applied_feedback &&
                  config_watchdog_us==applied_watchdog;
 wire config_payload_ok=config_axes!=0 &&
   config_feedback_us>=`SI_TIMEOUT_MIN_US && config_feedback_us<=`SI_TIMEOUT_MAX_US &&
   config_watchdog_us>=`SI_TIMEOUT_MIN_US && config_watchdog_us<=`SI_TIMEOUT_MAX_US;
 assign committed_axes=applied_axes;
 assign committed_feedback_us=applied_feedback;
 assign committed_watchdog_us=applied_watchdog;
 assign config_pending=accepted_txn!=applied_txn;
 wire config_submit_ok=write_data==1 && config_txn!=0 && config_txn>=accepted_txn &&
   config_payload_ok && (config_txn==accepted_txn ? same_config : config_ready && !config_pending && config_dirty==7);
 always @*begin
  write_known=1;write_response=0;
  if(write_strobe!=15)write_response=2;
  case(write_offset)
   `SI_REG_SHADOW_AXES:if(write_data==0 || write_data>7)write_response=2;
   `SI_REG_SHADOW_FEEDBACK_US,`SI_REG_SHADOW_WATCHDOG_US,`SI_REG_CONFIG_TXN,
   `SI_REG_HEARTBEAT_OWNER_LO,`SI_REG_HEARTBEAT_OWNER_HI,
   `SI_REG_HEARTBEAT_SEQ_LO,`SI_REG_HEARTBEAT_SEQ_HI:begin end
   `SI_REG_CONFIG_COMMIT:begin
    if(write_data!=1 || config_txn==0 || config_txn<accepted_txn || !config_payload_ok)write_response=2;
    else if(config_txn==accepted_txn)begin if(!same_config)write_response=2;end
    else if(!config_ready || config_pending || config_dirty!=7)write_response=2;
   end
   `SI_REG_OWNER_OPEN:if(write_data!=1 || !owner_open_ok)write_response=2;
   `SI_REG_OWNER_CLOSE:if(write_data!=1 || !owner_close_ok ||
     heartbeat_dirty[1:0]!=3 || heartbeat_owner!=owner_id)write_response=2;
   `SI_REG_HEARTBEAT_COMMIT:if(write_data!=1 || heartbeat_dirty!=15 || !heartbeat_ok)write_response=2;
   `SI_REG_SNAP_REQ:if(write_data==0 || write_data<=snapshot_id)write_response=2;
   default:begin write_known=0;write_response=2;end
  endcase
 end
 wire accepted=write_fire && write_known && write_response==0;
 // Side effects must not pass through the shared response mux. In particular
 // config_apply changes current-round qualification, which affects owner_open
 // legality; sharing the mux would create a structural combinational loop.
 wire full_commit=write_fire && write_strobe==15 && write_data==1;
 wire config_commit=full_commit && write_offset==`SI_REG_CONFIG_COMMIT &&
   config_submit_ok && config_txn!=accepted_txn;
 assign owner_open=full_commit && write_offset==`SI_REG_OWNER_OPEN && owner_open_ok;
 assign owner_close=full_commit && write_offset==`SI_REG_OWNER_CLOSE && owner_close_ok &&
   heartbeat_dirty[1:0]==3 && heartbeat_owner==owner_id;
 assign heartbeat_commit=full_commit && write_offset==`SI_REG_HEARTBEAT_COMMIT &&
   heartbeat_dirty==15 && heartbeat_ok;
 integer index;
 always @*begin
  read_known=1;read_data=0;index=0;
  case(read_offset)
   `SI_REG_SHADOW_AXES:read_data={29'd0,config_axes};
   `SI_REG_SHADOW_FEEDBACK_US:read_data=config_feedback_us;
   `SI_REG_SHADOW_WATCHDOG_US:read_data=config_watchdog_us;
   `SI_REG_CONFIG_TXN:read_data=config_txn;
   `SI_REG_CONFIG_APPLIED:read_data=applied_txn;
   `SI_REG_CONFIG_ACCEPTED:read_data=accepted_txn;
   `SI_REG_ACTIVE_AXES:read_data={29'd0,active_axes};
   `SI_REG_ACTIVE_FEEDBACK_US:read_data=active_feedback_us;
   `SI_REG_ACTIVE_WATCHDOG_US:read_data=active_watchdog_us;
   `SI_REG_OWNER_LO:read_data=owner_id[31:0];
   `SI_REG_OWNER_HI:read_data=owner_id[63:32];
   `SI_REG_HEARTBEAT_OWNER_LO:read_data=heartbeat_owner[31:0];
   `SI_REG_HEARTBEAT_OWNER_HI:read_data=heartbeat_owner[63:32];
   `SI_REG_HEARTBEAT_SEQ_LO:read_data=heartbeat_sequence[31:0];
   `SI_REG_HEARTBEAT_SEQ_HI:read_data=heartbeat_sequence[63:32];
   `SI_REG_STATUS:read_data=status;
   `SI_REG_CAUSES:read_data=causes;
   `SI_REG_FIRST_CAUSE:read_data=first_cause;
   `SI_REG_FIRST_TIME_LO:read_data=first_time[31:0];
   `SI_REG_FIRST_TIME_HI:read_data=first_time[63:32];
   `SI_REG_LAST_SEQ_LO:read_data=last_sequence[31:0];
   `SI_REG_LAST_SEQ_HI:read_data=last_sequence[63:32];
   `SI_REG_SNAP_REQ,`SI_REG_SNAP_ID:read_data=snapshot_id;
   default:begin
    if(read_offset>=`SI_SNAPSHOT_BASE && read_offset<`SI_SNAPSHOT_BASE+4*`SI_SNAPSHOT_WORDS)begin
     index=(read_offset-`SI_SNAPSHOT_BASE)>>2;read_data=snapshot[index*32+:32];
    end else read_known=0;
   end
  endcase
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   config_axes<=`SI_DEFAULT_AXIS_MASK;config_feedback_us<=`SI_TIMEOUT_DEFAULT_US;
   config_watchdog_us<=`SI_TIMEOUT_DEFAULT_US;config_txn<=0;accepted_txn<=0;applied_txn<=0;config_apply<=0;
   config_dirty<=0;applied_axes<=0;applied_feedback<=0;applied_watchdog<=0;
   heartbeat_owner<=0;heartbeat_sequence<=0;heartbeat_dirty<=0;snapshot_id<=0;snapshot<=0;
  end else begin
   // Capture the complete payload at acceptance, apply on the next edge.
   // This breaks idle/planner admission out of the detection/STEP cone.
   config_apply<=config_commit;
   if(config_apply)applied_txn<=accepted_txn;
   if(accepted)begin
   case(write_offset)
    `SI_REG_SHADOW_AXES:begin config_axes<=write_data[2:0];config_dirty[0]<=1;end
    `SI_REG_SHADOW_FEEDBACK_US:begin config_feedback_us<=write_data;config_dirty[1]<=1;end
    `SI_REG_SHADOW_WATCHDOG_US:begin config_watchdog_us<=write_data;config_dirty[2]<=1;end
    `SI_REG_CONFIG_TXN:config_txn<=write_data;
    `SI_REG_HEARTBEAT_OWNER_LO:begin heartbeat_owner[31:0]<=write_data;heartbeat_dirty[0]<=1;end
    `SI_REG_HEARTBEAT_OWNER_HI:begin heartbeat_owner[63:32]<=write_data;heartbeat_dirty[1]<=1;end
    `SI_REG_HEARTBEAT_SEQ_LO:begin heartbeat_sequence[31:0]<=write_data;heartbeat_dirty[2]<=1;end
    `SI_REG_HEARTBEAT_SEQ_HI:begin heartbeat_sequence[63:32]<=write_data;heartbeat_dirty[3]<=1;end
    `SI_REG_OWNER_CLOSE,`SI_REG_HEARTBEAT_COMMIT:heartbeat_dirty<=0;
    `SI_REG_OWNER_OPEN:heartbeat_dirty<=0;
    `SI_REG_CONFIG_COMMIT:if(config_commit)begin
     accepted_txn<=config_txn;applied_axes<=config_axes;applied_feedback<=config_feedback_us;
     applied_watchdog<=config_watchdog_us;config_dirty<=0;
    end
    `SI_REG_SNAP_REQ:begin snapshot<=live_snapshot;snapshot_id<=write_data;end
    default:begin end
   endcase
   end
  end
 end
endmodule
