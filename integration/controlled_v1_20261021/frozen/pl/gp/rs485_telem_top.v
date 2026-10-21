module rs485_telem_top #(parameter integer FIFO_DEPTH=256)(
 input wire clk,rst_n,dma_ready,dma_quiescent,input wire [63:0] time_us,
 input wire event_valid,input wire [255:0] event_raw,input wire [31:0] collector_generation,event_revision,input wire [159:0] active_period_us,input wire [4:0] active_mask,
 input wire [32:0] s_awaddr,s_araddr,input wire [31:0] s_wdata,input wire [3:0] s_wstrb,
 input wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready,
 output wire s_awready,s_wready,s_arready,s_bvalid,s_rvalid,output wire [1:0] s_bresp,s_rresp,output wire [31:0] s_rdata,output wire irq,
 output wire [63:0] m_data,output wire [7:0] m_keep,output wire m_last,m_valid,input wire m_ready);
wire enable_write;
wire enable_value;
wire recover;
wire cancel;
wire arm;
wire complete;
wire [31:0] recover_generation;
wire [31:0] arm_id;
wire [31:0] arm_generation;
wire [31:0] arm_bytes;
wire [31:0] complete_id;
wire [31:0] complete_generation;
wire [31:0] complete_result;
wire [31:0] command_error;
wire command_result;
wire [31:0] status;
wire [31:0] transport_generation;
wire [31:0] packet_id;
wire [31:0] packet_generation;
wire [31:0] packet_count;
wire [31:0] packet_bytes;
wire [31:0] fifo_level;
wire [31:0] full_drop;
wire [31:0] disabled_drop;
wire [31:0] cancel_drop;
wire [31:0] stream_records;
wire [31:0] stream_packets;
wire [31:0] dma_ok;
wire [31:0] dma_failed;
wire [63:0] completion_serial;
wire [31:0] wait_arm_max_us;
wire [31:0] backpressure_max_cycles;
wire [31:0] ready_lateness_max_us;
wire [4:0] events;
wire snapshot_capture;
wire [8:0] cache_word;
wire [31:0] cache_data;
wire [31:0] parse_errors;
rs485_telem_regs regs(.clk(clk),.rst_n(rst_n),.time_us(time_us),.s_awaddr(s_awaddr),.s_araddr(s_araddr),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_awvalid(s_awvalid),.s_wvalid(s_wvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_rready(s_rready),.s_awready(s_awready),.s_wready(s_wready),.s_bvalid(s_bvalid),.s_arready(s_arready),.s_rvalid(s_rvalid),.s_bresp(s_bresp),.s_rresp(s_rresp),.s_rdata(s_rdata),.irq(irq),.collector_generation(collector_generation),.active_mask(active_mask),.snapshot_capture(snapshot_capture),.cache_word(cache_word),.cache_data(cache_data),.parse_errors(parse_errors),.enable_write(enable_write),.enable_value(enable_value),.recover(recover),.cancel(cancel),.arm(arm),.complete(complete),.recover_generation(recover_generation),.arm_id(arm_id),.arm_generation(arm_generation),.arm_bytes(arm_bytes),.complete_id(complete_id),.complete_generation(complete_generation),.complete_result(complete_result),.command_error(command_error),.command_result(command_result),.status(status),.transport_generation(transport_generation),.packet_id(packet_id),.packet_generation(packet_generation),.packet_count(packet_count),.packet_bytes(packet_bytes),.fifo_level(fifo_level),.full_drop(full_drop),.disabled_drop(disabled_drop),.cancel_drop(cancel_drop),.stream_records(stream_records),.stream_packets(stream_packets),.dma_ok(dma_ok),.dma_failed(dma_failed),.completion_serial(completion_serial),.wait_arm_max_us(wait_arm_max_us),.backpressure_max_cycles(backpressure_max_cycles),.ready_lateness_max_us(ready_lateness_max_us),.events(events),.cfg_revision(event_revision));
rs485_telemetry #(.DEPTH(FIFO_DEPTH)) transport(.clk(clk),.rst_n(rst_n),.dma_ready(dma_ready),.dma_quiescent(dma_quiescent),.time_us(time_us),.event_valid(event_valid),.event_raw(event_raw),.enable_write(enable_write),.enable_value(enable_value),.recover(recover),.cancel(cancel),.arm(arm),.complete(complete),.recover_generation(recover_generation),.arm_id(arm_id),.arm_generation(arm_generation),.arm_bytes(arm_bytes),.complete_id(complete_id),.complete_generation(complete_generation),.complete_result(complete_result),.command_error(command_error),.command_result(command_result),.status(status),.transport_generation(transport_generation),.packet_id(packet_id),.packet_generation(packet_generation),.packet_count(packet_count),.packet_bytes(packet_bytes),.fifo_level(fifo_level),.full_drop(full_drop),.disabled_drop(disabled_drop),.cancel_drop(cancel_drop),.stream_records(stream_records),.stream_packets(stream_packets),.dma_ok(dma_ok),.dma_failed(dma_failed),.completion_serial(completion_serial),.wait_arm_max_us(wait_arm_max_us),.backpressure_max_cycles(backpressure_max_cycles),.ready_lateness_max_us(ready_lateness_max_us),.events(events),.m_data(m_data),.m_keep(m_keep),.m_last(m_last),.m_valid(m_valid),.m_ready(m_ready),.event_generation(collector_generation),.event_revision(event_revision));
rs485_latest_cache cache(.clk(clk),.rst_n(rst_n),.time_us(time_us),.collector_generation(collector_generation),.event_valid(event_valid),.event_raw(event_raw),.event_revision(event_revision),.active_period_us(active_period_us),.active_mask(active_mask),.snapshot_capture(snapshot_capture),.parse_errors(parse_errors),.event_generation(collector_generation),.snapshot_word(cache_word),.snapshot_data(cache_data));
endmodule
