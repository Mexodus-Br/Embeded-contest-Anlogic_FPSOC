module rs485_gp_bridge #(

 parameter INTERLOCK_SUPPORT=0,
 `include "parameters.vh"
 ,
 `include "rate_parameters.vh"
)(input wire clk,rst_n,input wire [63:0] time_us,input wire rx,output wire tx,de,irq,
 input wire [32:0] s_awaddr,s_araddr,input wire [31:0] s_wdata,input wire [3:0] s_wstrb,
 input wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready,
 output wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid,
 output wire [1:0] s_bresp,s_rresp,output wire [31:0] s_rdata,
 output wire completed_valid,output wire [255:0] completed_raw,output wire [31:0] completed_generation,completed_revision,
 output wire [159:0] current_periods,output wire [4:0] current_mask,
 input wire interlock_idle,interlock_idle_off,
 output wire interlock_run,interlock_reset,interlock_config_pending,interlock_config_change,interlock_busy,interlock_stop_commit);
wire run,collector_rst_n,cv,cr,ca,ce,busy,rv,rr,push;
wire [159:0] cp,ap;wire [4:0] cm,am;wire [7:0] cerr;
wire [31:0] revision,sequence,load,level,drop,ok,err,ignored,bus_events;
wire [255:0] data,push_data;wire [7999:0] tasks;wire [1279:0] nodes;wire [9:0] offline;
assign completed_valid=push;assign completed_raw=push_data;assign completed_revision=revision;
assign current_periods=ap;assign current_mask=am;
assign interlock_busy=busy;
rs485_multirate #(.CLK_HZ(CLK_HZ),.BAUD(BAUD),.SLAVE_COUNT(SLAVE_COUNT),.SLAVE_ADDRS(SLAVE_ADDRS),.POLL_CYCLES(POLL_CYCLES),.TIMEOUT_CYCLES(TIMEOUT_CYCLES),.INTERBYTE_CYCLES(INTERBYTE_CYCLES),.RETRIES(RETRIES),.PRE_CYCLES(PRE_CYCLES),.POST_CYCLES(POST_CYCLES),.TURN_CYCLES(TURN_CYCLES),.QUIET_CYCLES(QUIET_CYCLES),.FIFO_DEPTH(FIFO_DEPTH),.NORMAL_CYCLES(NORMAL_CYCLES),.ERROR_CYCLES(ERROR_CYCLES),.DEFAULT_PERIODS(DEFAULT_PERIODS),.MIN_PERIOD_US(MIN_PERIOD_US),.MAX_PERIOD_US(MAX_PERIOD_US),.LOAD_LIMIT_PPM(LOAD_LIMIT_PPM),.RESPONSE_BUDGET_US(RESPONSE_BUDGET_US),.FAILURE_THRESHOLD(FAILURE_THRESHOLD),.BACKOFF_US(BACKOFF_US)) collector(
.clk(clk),.rst_n(collector_rst_n),.enable(run),.time_us(time_us),.rx(rx),.tx(tx),.de(de),.debug_task(6'd0),.debug_node(4'd0),.cfg_valid(cv),.cfg_ready(cr),.cfg_applied(ca),.cfg_rejected(ce),.cfg_error(cerr),.cfg_period_us(cp),.cfg_mask(cm),.active_period_us(ap),.active_mask(am),.cfg_revision(revision),.cfg_apply_sequence(sequence),.config_load_ppm(load),.busy(busy),.record_valid(rv),.record_data(data),.record_ready(rr),.fifo_level(level),.dropped(drop),.accepted(ok),.errors(err),.ignored_rx(ignored),.bus_busy_events(bus_events),.node_offline(offline),.observe_push(push),.observe_data(push_data),.observe_tasks(tasks),.observe_nodes(nodes));
rs485_gp_regs #(.FIFO_DEPTH(FIFO_DEPTH),.SLAVE_COUNT(SLAVE_COUNT),.INTERLOCK_SUPPORT(INTERLOCK_SUPPORT)) regs(
.interlock_idle(interlock_idle),.interlock_idle_off(interlock_idle_off),.interlock_run(interlock_run),.interlock_stop_commit(interlock_stop_commit),
.interlock_reset(interlock_reset),.interlock_config_pending(interlock_config_pending),.interlock_config_change(interlock_config_change),
.observe_generation(completed_generation),.clk(clk),.rst_n(rst_n),.time_us(time_us),.s_awaddr(s_awaddr),.s_araddr(s_araddr),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_awvalid(s_awvalid),.s_wvalid(s_wvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_rready(s_rready),.s_awready(s_awready),.s_wready(s_wready),.s_bvalid(s_bvalid),.s_arready(s_arready),.s_rvalid(s_rvalid),.s_bresp(s_bresp),.s_rresp(s_rresp),.s_rdata(s_rdata),.irq(irq),.run(run),.collector_rst_n(collector_rst_n),.cfg_valid(cv),.cfg_ready(cr),.cfg_applied(ca),.cfg_rejected(ce),.cfg_error(cerr),.cfg_period_us(cp),.cfg_mask(cm),.active_period_us(ap),.active_mask(am),.cfg_revision(revision),.cfg_apply_sequence(sequence),.config_load_ppm(load),.busy(busy),.record_valid(rv),.record_data(data),.record_ready(rr),.fifo_level(level),.dropped(drop),.accepted(ok),.errors(err),.ignored_rx(ignored),.bus_busy_events(bus_events),.node_offline(offline),.observe_push(push),.observe_data(push_data),.observe_tasks(tasks),.observe_nodes(nodes));
endmodule
