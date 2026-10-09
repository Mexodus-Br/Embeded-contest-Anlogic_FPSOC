`timescale 1ns/1ps
// Single-clock execution channel. All requests are synchronous strobes except
// fault (level). Upstream owns FIFO flush, session ID uniqueness and HOME.
module axis_motion #(
    parameter [63:0] STEP_HIGH_CYCLES = 0,
    parameter [63:0] STEP_LOW_CYCLES = 0,
    parameter [63:0] DIR_SETUP_CYCLES = 0,
    parameter [63:0] DIR_HOLD_CYCLES = 0,
    parameter [63:0] EN_SETUP_CYCLES = 0,
    parameter [63:0] EN_DISABLE_CYCLES = 0,
    parameter [63:0] STEP_PERIOD_CYCLES = 0,
    parameter [63:0] CLOCK_HZ = 100000000,
    parameter [63:0] MAX_STEP_HZ = 0,
    parameter EN_ACTIVE_LEVEL = 1'b1
) (
    input wire clk, input wire rst_n,
    input wire enable_req, input wire disable_req,
    input wire rebase_req, input wire signed [63:0] rebase_position,
    input wire open_req, input wire [63:0] open_session_id,
    input wire cmd_valid, input wire [63:0] cmd_session_id,
    input wire signed [63:0] cmd_target,
    input wire stop_req, input wire underflow, input wire fault,
    input wire clear_fault,
    output reg step, output reg dir, output wire en,
    output reg signed [63:0] position,
    output reg position_valid, output reg session_valid,
    output reg [63:0] session_id,
    output reg fault_latched,
    output wire config_valid, output wire cmd_ready, output wire busy,
    output reg cmd_accepted, output reg rebase_accepted,
    output reg open_accepted, output reg rejected,
    output reg pulse_event, output reg done, output reg stopped,
    output reg cancelled
);
    // 128-bit products avoid overflow in parameter validation.
    localparam [127:0] RATE_PRODUCT = {64'b0, MAX_STEP_HZ} *
                                           {64'b0, STEP_PERIOD_CYCLES};
    localparam [64:0] MIN_PERIOD = {1'b0, STEP_HIGH_CYCLES} +
                                  {1'b0, STEP_LOW_CYCLES};
    assign config_valid = STEP_HIGH_CYCLES > 0 && STEP_LOW_CYCLES > 0 &&
        CLOCK_HZ > 0 && MAX_STEP_HZ > 0 && STEP_PERIOD_CYCLES > 0 &&
        {1'b0, STEP_PERIOD_CYCLES} >= MIN_PERIOD && RATE_PRODUCT >= CLOCK_HZ;

    reg enabled, active, draining, completing, disabling;
    reg signed [63:0] target;
    reg positive;
    reg [63:0] high_left, edge_age, low_age, dir_age, en_age, off_left;
    wire safety = stop_req || underflow || fault || disable_req;
    wire safe = !step && low_age >= STEP_LOW_CYCLES &&
                                    edge_age >= DIR_HOLD_CYCLES;
    assign busy = active || draining || completing || disabling || step;
    assign en = enabled ? EN_ACTIVE_LEVEL : !EN_ACTIVE_LEVEL;
    assign cmd_ready = config_valid && position_valid && session_valid &&
        enabled && en_age >= EN_SETUP_CYCLES && !busy && !fault_latched && !safety;
    wire signed [64:0] delta = $signed({cmd_target[63], cmd_target}) -
                                      $signed({position[63], position});
    wire signed [64:0] next_position = $signed({position[63], position}) +
                                      (positive ? 65'sd1 : -65'sd1);
    function [63:0] age_next;
        input [63:0] age;
        begin age_next = (&age) ? age : age + 64'd1; end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            step <= 0; dir <= 1; enabled <= 0; position <= 0;
            position_valid <= 0; session_valid <= 0; session_id <= 0;
            fault_latched <= 0; active <= 0; draining <= 0;
            completing <= 0; disabling <= 0; target <= 0; positive <= 1;
            high_left <= 0; edge_age <= 0; low_age <= 0;
            dir_age <= 0; en_age <= 0; off_left <= 0;
            cmd_accepted <= 0; rebase_accepted <= 0; open_accepted <= 0;
            rejected <= 0; pulse_event <= 0; done <= 0;
            stopped <= 0; cancelled <= 0;
        end else begin
            cmd_accepted <= 0; rebase_accepted <= 0; open_accepted <= 0;
            rejected <= 0; pulse_event <= 0; done <= 0;
            stopped <= 0; cancelled <= 0;
            edge_age <= age_next(edge_age); dir_age <= age_next(dir_age);
            if (!step) low_age <= age_next(low_age);
            if (enabled) en_age <= age_next(en_age);
            // Pulse completion is independent of cancellation. No truncation.
            if (step) begin
                if (high_left == 1) begin
                    step <= 0; high_left <= 0; low_age <= 0;
                end else high_left <= high_left - 64'd1;
            end

            if (fault) fault_latched <= 1;
            else if (clear_fault && !busy && !safety) fault_latched <= 0;

            if (safety) begin
                active <= 0; completing <= 0; session_valid <= 0;
                if (session_valid || active || completing) cancelled <= 1;
                // A persistent fault inhibits execution but does not hold the
                // drain state forever. A request strobe reports completion.
                if (!draining && (active || completing || step || session_valid || stop_req ||
                                  underflow || disable_req)) draining <= 1;
                if (disable_req) begin
                    position_valid <= 0; disabling <= 1;
                    off_left <= EN_DISABLE_CYCLES;
                end
                if (cmd_valid || open_req || rebase_req || enable_req) rejected <= 1;
            end else begin
                // Mutating maintenance/control requests are mutually exclusive.
                if ((rebase_req && (open_req || enable_req || cmd_valid)) ||
                    (open_req && (enable_req || cmd_valid)) ||
                    (enable_req && cmd_valid)) rejected <= 1;
                else if (rebase_req) begin
                    if (!enabled && !busy && !session_valid && !fault_latched) begin
                        position <= rebase_position; position_valid <= 1;
                        rebase_accepted <= 1;
                    end else rejected <= 1;
                end else if (enable_req) begin
                    if (config_valid && position_valid && !busy && !fault_latched) begin
                        if (!enabled) en_age <= 0;
                        enabled <= 1;
                    end else rejected <= 1;
                end else if (open_req) begin
                    if (config_valid && position_valid && !busy && !session_valid &&
                        !fault_latched && open_session_id != 0 &&
                        open_session_id != session_id) begin
                        session_valid <= 1; session_id <= open_session_id;
                        open_accepted <= 1;
                    end else rejected <= 1;
                end else if (cmd_valid) begin
                    if (cmd_ready && cmd_session_id == session_id) begin
                        cmd_accepted <= 1; target <= cmd_target;
                        positive <= !delta[64];
                        if (delta == 0) completing <= 1;
                        else active <= 1;
                    end else rejected <= 1;
                end

                if (active) begin
                    if (!step && dir != positive && edge_age >= DIR_HOLD_CYCLES) begin
                        dir <= positive; dir_age <= 0;
                    end else if (!step && dir == positive &&
                        dir_age >= DIR_SETUP_CYCLES && en_age >= EN_SETUP_CYCLES &&
                        low_age >= STEP_LOW_CYCLES && edge_age >= STEP_PERIOD_CYCLES) begin
                        if (next_position[64] != next_position[63]) begin
                            fault_latched <= 1; session_valid <= 0;
                            active <= 0; draining <= 1; cancelled <= 1;
                        end else begin
                            step <= 1; high_left <= STEP_HIGH_CYCLES;
                            edge_age <= 0; pulse_event <= 1;
                            position <= next_position[63:0];
                            if ($signed(next_position[63:0]) == target) begin
                                active <= 0; completing <= 1;
                            end
                        end
                    end
                end
            end
            if (completing && safe && !safety) begin completing <= 0; done <= 1; end
            if (draining && safe) begin draining <= 0; stopped <= 1; end
            // Disable delay starts only after the pulse and DIR hold are safe.
            if (disabling && !draining && safe && !disable_req) begin
                if (off_left == 0) begin enabled <= 0; disabling <= 0; end
                else off_left <= off_left - 64'd1;
            end
        end
    end
endmodule
