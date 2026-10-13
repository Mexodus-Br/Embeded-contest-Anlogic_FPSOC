module td_probe(input clk,rst_n,scan_in,load,rx_async,output scan_out,tx,de);
reg [241:0] inp;
reg [997:0] obs;
wire [0:0] busy;
wire [0:0] cfg_ready;
wire [0:0] cfg_applied;
wire [0:0] cfg_rejected;
wire [7:0] cfg_error;
wire [31:0] cfg_revision;
wire [31:0] cfg_apply_sequence;
wire [159:0] active_period_us;
wire [4:0] active_mask;
wire [31:0] config_load_ppm;
wire [0:0] record_valid;
wire [255:0] record_data;
wire [31:0] fifo_level;
wire [31:0] dropped;
wire [31:0] accepted;
wire [31:0] errors;
wire [31:0] ignored_rx;
wire [31:0] bus_busy_events;
wire [9:0] node_offline;
wire [31:0] stat_scheduled;
wire [31:0] stat_sent;
wire [31:0] stat_valid;
wire [31:0] stat_missed;
wire [31:0] stat_max_lateness_us;
wire [7:0] node_failure_streak;
wire [63:0] node_cooldown_until_us;
wire [31:0] node_backoff_entries;
always @(posedge clk) begin inp<={inp[240:0],scan_in}; if(load) obs<={tx,de,busy,cfg_ready,cfg_applied,cfg_rejected,cfg_error,cfg_revision,cfg_apply_sequence,active_period_us,active_mask,config_load_ppm,record_valid,record_data,fifo_level,dropped,accepted,errors,ignored_rx,bus_busy_events,node_offline,stat_scheduled,stat_sent,stat_valid,stat_missed,stat_max_lateness_us,node_failure_streak,node_cooldown_until_us,node_backoff_entries}; else obs<={obs[996:0],1'b0}; end
assign scan_out=obs[997];
rs485_multirate  dut(.clk(clk),.rst_n(rst_n),.rx(rx_async),
.enable(inp[0 +: 1]),
.time_us(inp[1 +: 64]),
.cfg_valid(inp[65 +: 1]),
.cfg_period_us(inp[66 +: 160]),
.cfg_mask(inp[226 +: 5]),
.record_ready(inp[231 +: 1]),
.debug_task(inp[232 +: 6]),
.debug_node(inp[238 +: 4]),
.tx(tx),
.de(de),
.busy(busy),
.cfg_ready(cfg_ready),
.cfg_applied(cfg_applied),
.cfg_rejected(cfg_rejected),
.cfg_error(cfg_error),
.cfg_revision(cfg_revision),
.cfg_apply_sequence(cfg_apply_sequence),
.active_period_us(active_period_us),
.active_mask(active_mask),
.config_load_ppm(config_load_ppm),
.record_valid(record_valid),
.record_data(record_data),
.fifo_level(fifo_level),
.dropped(dropped),
.accepted(accepted),
.errors(errors),
.ignored_rx(ignored_rx),
.bus_busy_events(bus_busy_events),
.node_offline(node_offline),
.stat_scheduled(stat_scheduled),
.stat_sent(stat_sent),
.stat_valid(stat_valid),
.stat_missed(stat_missed),
.stat_max_lateness_us(stat_max_lateness_us),
.node_failure_streak(node_failure_streak),
.node_cooldown_until_us(node_cooldown_until_us),
.node_backoff_entries(node_backoff_entries));
endmodule
