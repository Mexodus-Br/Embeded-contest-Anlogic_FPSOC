 `include "telem_defs.vh"
 reg [32:0] s_awaddr=0,s_araddr=0;reg [31:0] s_wdata=0;reg [3:0] s_wstrb=0;
 reg s_awvalid=0,s_wvalid=0,s_bready=0,s_arvalid=0,s_rready=0;
 wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid;wire [1:0] s_bresp,s_rresp;wire [31:0] s_rdata;
 integer seed=20261014,seed_arg,checks=0;
 initial begin if($value$plusargs("seed=%d",seed_arg)) seed=seed_arg;end
 task ticks;input integer n;begin repeat(n) @(negedge clk);end endtask
 task write_address;input [32:0] a;
  begin s_awaddr=a;s_awvalid=1;@(posedge clk);while(!s_awready) @(posedge clk);@(negedge clk);s_awvalid=0;end
 endtask
 task write_data;input [31:0] d;input [3:0] st;
  begin s_wdata=d;s_wstrb=st;s_wvalid=1;@(posedge clk);while(!s_wready) @(posedge clk);@(negedge clk);s_wvalid=0;end
 endtask
 task wr_abs;input [32:0] a;input [31:0] d;input [3:0] st;input integer order,stall;input [1:0] expected;
  integer k;reg [1:0] held;
  begin
   @(negedge clk);
   case(order)
    1:begin write_address(a);ticks(3);write_data(d,st);end
    2:begin write_data(d,st);ticks(4);write_address(a);end
    default:fork write_address(a);write_data(d,st);join
   endcase
   wait(s_bvalid);@(negedge clk);held=s_bresp;
   for(k=0;k<stall;k=k+1) begin ticks(1);if(!s_bvalid || s_bresp!==held) $fatal(1,"B backpressure");end
   if(held!==expected) $fatal(1,"write addr=%h data=%h got=%h expected=%h",a,d,held,expected);
   s_bready=1;@(posedge clk);@(negedge clk);s_bready=0;checks=checks+1;
  end
 endtask
 task wr;input [31:0] off,d;input [3:0] st;input [1:0] expected;
  integer r;
  begin r=$random(seed)&32'h7fffffff;wr_abs({1'b0,`RT_BASE}+off,d,st,r%3,r%7,expected);end
 endtask
 task rd_abs;input [32:0] a;input integer stall;input [1:0] expected;output [31:0] d;
  integer k;reg [31:0] held;reg [1:0] resp;
  begin
   @(negedge clk);s_araddr=a;s_arvalid=1;@(posedge clk);while(!s_arready) @(posedge clk);
   @(negedge clk);s_arvalid=0;wait(s_rvalid);@(negedge clk);held=s_rdata;resp=s_rresp;
   for(k=0;k<stall;k=k+1) begin ticks(1);if(!s_rvalid || s_rdata!==held || s_rresp!==resp) $fatal(1,"R backpressure");end
   if(resp!==expected) $fatal(1,"read addr=%h got=%h expected=%h",a,resp,expected);
   d=held;s_rready=1;@(posedge clk);@(negedge clk);s_rready=0;checks=checks+1;
  end
 endtask
 task rd;input [31:0] off;input [1:0] expected;output [31:0] d;
  integer r;begin r=$random(seed)&32'h7fffffff;rd_abs({1'b0,`RT_BASE}+off,r%9,expected,d);end
 endtask
 task eq;input [31:0] off,expected;reg [31:0] v;
  begin rd(off,0,v);if(v!==expected) $fatal(1,"reg %h got=%h expected=%h",off,v,expected);end
 endtask
 task read_record;output [255:0] data;integer k;reg [31:0] v;
  begin for(k=7;k>=0;k=k-1) begin rd((`RT_ROW_BASE+`RT_ROW_VALID_RAW)+k*4,0,v);data[k*32+:32]=v;end end
 endtask
