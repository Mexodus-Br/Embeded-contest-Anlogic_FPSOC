`timescale 1ns/1ps
`include "generated/interface_defs.vh"
// gp_control_probe_v1 only. rst_n is already synchronously released in clk.
module rs485_probe_time_regs(
    input wire clk, rst_n,
    input wire [32:0] s_awaddr, input wire s_awvalid, output wire s_awready,
    input wire [31:0] s_wdata, input wire [3:0] s_wstrb,
    input wire s_wvalid, output wire s_wready,
    output reg [1:0] s_bresp, output reg s_bvalid, input wire s_bready,
    input wire [32:0] s_araddr, input wire s_arvalid, output wire s_arready,
    output reg [31:0] s_rdata, output reg [1:0] s_rresp,
    output reg s_rvalid, input wire s_rready,
    input wire [255:0] actual_position, actual_pulses,
    input wire [3:0] actual_valid, input wire [31:0] actual_state,
    input wire [63:0] actual_session,
    input wire [31:0] actual_accepted_seq, actual_done_seq,
    output wire [63:0] shared_time_us,
    output wire irq
);
    localparam [32:0] BASE={1'b0,`PLI_GP_GP_CONTROL_PROBE_V1_BASE};
    localparam [31:0] IRQ_BITS=`PLI_GP_GP_CONTROL_PROBE_V1_IRQ_PENDING_MASK;
    localparam [1:0] OKAY=0, SLVERR=2, DECERR=3;
    reg aw_held, w_held, aw_hit;
    reg [11:0] aw_offset;
    reg [31:0] write_data;
    reg [3:0] write_strobe;
    reg [31:0] scratch, opcode, argument, txn_shadow;
    reg [31:0] irq_pending, irq_mask;
    reg test_level;
    reg [31:0] last_id, last_opcode, last_argument;
    reg [31:0] ack_id, ack_error;
    reg ack_valid, ack_accepted, busy;
    reg [1:0] phase;
    reg [31:0] captured_id, captured_opcode, captured_argument, result_error;
    reg duplicate;
    reg [6:0] tick_div;
    reg [63:0] timestamp;
    assign shared_time_us=timestamp;
    reg [255:0] snap_position, snap_pulses;
    reg [63:0] snap_time, snap_session;
    reg [31:0] snap_id, snap_state, snap_accepted_seq, snap_done_seq;
    reg [3:0] snap_position_valid;
    reg snap_valid;
    assign s_awready=rst_n && !aw_held && !s_bvalid;
    assign s_wready=rst_n && !w_held && !s_bvalid;
    assign s_arready=rst_n && !s_rvalid;
    assign irq=rst_n && |(irq_pending & irq_mask);
    wire write_fire=aw_held && w_held && !s_bvalid;
    wire [31:0] byte_mask={{8{write_strobe[3]}},{8{write_strobe[2]}},
                              {8{write_strobe[1]}},{8{write_strobe[0]}}};
    function [31:0] merged;
        input [31:0] old_value;
        begin merged=(old_value & ~byte_mask) | (write_data & byte_mask); end
    endfunction
    // Decode uses full 33bit window; low offset alone can never select a register.
    function hit;
        input [32:0] address;
        begin hit=(address[32:12]==BASE[32:12]); end
    endfunction
    reg [1:0] write_response;
    always @* begin
        write_response=OKAY;
        if (!aw_hit) write_response=DECERR;
        else if (aw_offset[1:0]!=0) write_response=SLVERR;
        else if (write_strobe!=0) begin
            case (aw_offset)
                `PLI_REG_TEST_RW, `PLI_REG_CMD_OPCODE, `PLI_REG_CMD_ARG,
                `PLI_REG_TXN_ID: write_response=OKAY;
                `PLI_REG_IRQ_MASK:
                    if (|(write_data & byte_mask & ~IRQ_BITS)) write_response=SLVERR;
                `PLI_REG_IRQ_PENDING:
                    if (write_strobe!=15 || |(write_data & ~IRQ_BITS)) write_response=SLVERR;
                `PLI_REG_TEST_IRQ_LEVEL:
                    if (write_strobe!=15 || |(write_data & ~32'd1)) write_response=SLVERR;
                `PLI_REG_CMD_SUBMIT:
                    if (write_strobe!=15 || write_data!=1 || busy || txn_shadow==0 ||
                        txn_shadow<last_id || (txn_shadow==last_id &&
                        (opcode!=last_opcode || argument!=last_argument))) write_response=SLVERR;
                default: write_response=SLVERR;
            endcase
        end
    end
    wire write_ok=write_fire && write_response==OKAY && write_strobe!=0;
    wire [31:0] irq_clear=(write_ok && aw_offset==`PLI_REG_IRQ_PENDING) ? write_data : 0;
    wire ack_event=busy && phase==3;
    // Pre-edge active source and publish event win over concurrent W1C.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin irq_pending<=0; irq_mask<=0; test_level<=0; end
        else begin
            irq_pending <= (irq_pending & ~irq_clear) |
                           (ack_event ? `PLI_REG_IRQ_PENDING_ACK_MASK : 32'd0) |
                           (test_level ? `PLI_REG_IRQ_PENDING_TEST_MASK : 32'd0);
            if (write_ok && aw_offset==`PLI_REG_IRQ_MASK) irq_mask<=merged(irq_mask);
            if (write_ok && aw_offset==`PLI_REG_TEST_IRQ_LEVEL) test_level<=write_data[0];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            aw_held<=0; w_held<=0; aw_hit<=0; aw_offset<=0;
            write_data<=0; write_strobe<=0; s_bvalid<=0; s_bresp<=OKAY;
            scratch<=0; opcode<=0; argument<=0; txn_shadow<=0;
        end else begin
            if (s_awvalid && s_awready) begin
                aw_held<=1; aw_hit<=hit(s_awaddr); aw_offset<=s_awaddr[11:0];
            end
            if (s_wvalid && s_wready) begin
                w_held<=1; write_data<=s_wdata; write_strobe<=s_wstrb;
            end
            if (s_bvalid && s_bready) s_bvalid<=0;
            if (write_fire) begin
                aw_held<=0; w_held<=0; s_bvalid<=1; s_bresp<=write_response;
                if (write_ok) case (aw_offset)
                    `PLI_REG_TEST_RW: scratch<=merged(scratch);
                    `PLI_REG_CMD_OPCODE: opcode<=merged(opcode);
                    `PLI_REG_CMD_ARG: argument<=merged(argument);
                    `PLI_REG_TXN_ID: txn_shadow<=merged(txn_shadow);
                endcase
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin tick_div<=0; timestamp<=0; end
        else if (tick_div==99) begin tick_div<=0; timestamp<=timestamp+64'd1; end
        else tick_div<=tick_div+1'b1;
    end
    // Three cycles after SUBMIT capture: validate, sample, publish.
    // All payload fields are immutable during busy; duplicates reuse cache.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy<=0; phase<=0; duplicate<=0; captured_id<=0; captured_opcode<=0;
            captured_argument<=0; result_error<=0; last_id<=0; last_opcode<=0;
            last_argument<=0; ack_id<=0; ack_error<=0; ack_valid<=0; ack_accepted<=0;
            snap_position<=0; snap_pulses<=0; snap_time<=0; snap_session<=0;
            snap_id<=0; snap_state<=0; snap_accepted_seq<=`PLI_GP_GP_CONTROL_PROBE_V1_SNAP_ACCEPTED_SEQ_RESET;
            snap_done_seq<=`PLI_GP_GP_CONTROL_PROBE_V1_SNAP_DONE_SEQ_RESET;
            snap_position_valid<=0; snap_valid<=0;
        end else begin
            if (write_ok && aw_offset==`PLI_REG_CMD_SUBMIT) begin
                busy<=1; phase<=1; ack_valid<=0;
                captured_id<=txn_shadow; captured_opcode<=opcode; captured_argument<=argument;
                duplicate<=(txn_shadow==last_id);
            end
            if (busy) case (phase)
                1: begin
                    phase<=2;
                    if (duplicate) result_error<=ack_error;
                    else if (captured_argument!=0 ||
                        (captured_opcode!=`PLI_CMD_NOP && captured_opcode!=`PLI_CMD_SNAPSHOT))
                        result_error<=`PLI_ERR_BAD_COMMAND;
                    else result_error<=`PLI_ERR_OK;
                end
                2: begin
                    phase<=3;
                    if (!duplicate && result_error==`PLI_ERR_OK && captured_opcode==`PLI_CMD_SNAPSHOT) begin
                        snap_position<=actual_position; snap_pulses<=actual_pulses;
                        snap_position_valid<=actual_valid; snap_state<=actual_state;
                        snap_session<=actual_session; snap_accepted_seq<=actual_accepted_seq;
                        snap_done_seq<=actual_done_seq; snap_time<=timestamp;
                        snap_id<=captured_id; snap_valid<=1;
                    end
                end
                3: begin
                    busy<=0; phase<=0; ack_valid<=1; ack_accepted<=(result_error==`PLI_ERR_OK);
                    ack_id<=captured_id; ack_error<=result_error;
                    if (!duplicate) begin
                        last_id<=captured_id; last_opcode<=captured_opcode; last_argument<=captured_argument;
                    end
                end
            endcase
        end
    end
    reg [31:0] read_value;
    reg read_known;
    integer axis_index;
    always @* begin
        read_value=0; read_known=1; axis_index=0;
        case (s_araddr[11:0])
            `PLI_REG_VERSION: read_value=`PLI_GP_GP_CONTROL_PROBE_V1_EXPECTED_VERSION;
            `PLI_REG_CAPS: read_value=`PLI_GP_GP_CONTROL_PROBE_V1_EXPECTED_CAPS;
            `PLI_REG_FEATURES: read_value=`PLI_GP_GP_CONTROL_PROBE_V1_EXPECTED_FEATURES;
            `PLI_REG_STATE: read_value=`PLI_STATE_NOT_READY;
            `PLI_REG_TICK_HZ: read_value=`PLI_GP_GP_CONTROL_PROBE_V1_EXPECTED_TICK_HZ;
            `PLI_REG_TEST_RW: read_value=scratch;
            `PLI_REG_CMD_OPCODE: read_value=opcode;
            `PLI_REG_CMD_ARG: read_value=argument;
            `PLI_REG_TXN_ID: read_value=txn_shadow;
            `PLI_REG_CMD_STATUS: read_value={28'd0,ack_valid,ack_accepted,ack_valid,busy};
            `PLI_REG_ACK_ID: read_value=ack_id;
            `PLI_REG_ACK_ERROR: read_value=ack_error;
            `PLI_REG_LAST_TXN_ID: read_value=last_id;
            `PLI_REG_POSITION_VALID: read_value={28'd0,actual_valid};
            `PLI_REG_IRQ_PENDING: read_value=irq_pending;
            `PLI_REG_IRQ_MASK: read_value=irq_mask;
            `PLI_REG_TEST_IRQ_LEVEL: read_value={31'd0,test_level};
            `PLI_REG_SNAP_ID: read_value=snap_id;
            `PLI_REG_SNAP_VALID: read_value={31'd0,snap_valid};
            `PLI_REG_SNAP_TIME_LO: read_value=snap_time[31:0];
            `PLI_REG_SNAP_TIME_HI: read_value=snap_time[63:32];
            `PLI_REG_SNAP_STATE: read_value=snap_state;
            `PLI_REG_SNAP_SESSION_LO: read_value=snap_session[31:0];
            `PLI_REG_SNAP_SESSION_HI: read_value=snap_session[63:32];
            `PLI_REG_SNAP_ACCEPTED_SEQ: read_value=snap_accepted_seq;
            `PLI_REG_SNAP_DONE_SEQ: read_value=snap_done_seq;
            `PLI_REG_SNAP_POSITION_VALID: read_value={28'd0,snap_position_valid};
            default: begin
                if (s_araddr[11:6]==2 && s_araddr[1:0]==0) begin
                    axis_index=s_araddr[5:4];
                    case (s_araddr[3:2])
                        0: read_value=snap_position[axis_index*64 +: 32];
                        1: read_value=snap_position[axis_index*64+32 +: 32];
                        2: read_value=snap_pulses[axis_index*64 +: 32];
                        3: read_value=snap_pulses[axis_index*64+32 +: 32];
                    endcase
                end else read_known=0;
            end
        endcase
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s_rvalid<=0; s_rdata<=0; s_rresp<=OKAY; end
        else begin
            if (s_rvalid && s_rready) s_rvalid<=0;
            if (s_arvalid && s_arready) begin
                s_rvalid<=1;
                if (!hit(s_araddr)) begin s_rdata<=0; s_rresp<=DECERR; end
                else if (!read_known || s_araddr[1:0]!=0) begin s_rdata<=0; s_rresp<=SLVERR; end
                else begin s_rdata<=read_value; s_rresp<=OKAY; end
            end
        end
    end
endmodule
