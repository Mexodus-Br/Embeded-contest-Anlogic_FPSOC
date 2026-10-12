`timescale 1ns/1ps
module tb_gp_ps_write_adapter;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;reg [11:0] s_awid=0;
    reg s_awvalid=0,s_wvalid=0,s_wlast=0,s_bready=0;
    reg m_awready=0,m_wready=0,m_bvalid=0;
    wire s_awready,s_wready,s_bvalid,m_awvalid,m_wvalid,m_bready;
    wire [11:0] m_wid;
    gp_ps_write_adapter dut(.clk(clk),.rst_n(rst_n),.s_awid(s_awid),.s_awvalid(s_awvalid),.s_awready(s_awready),
        .s_wvalid(s_wvalid),.s_wlast(s_wlast),.s_wready(s_wready),.s_bvalid(s_bvalid),.s_bready(s_bready),
        .m_awvalid(m_awvalid),.m_awready(m_awready),.m_wid(m_wid),.m_wvalid(m_wvalid),.m_wready(m_wready),.m_bvalid(m_bvalid),.m_bready(m_bready));
    integer checks=0,i,n,beats;reg [11:0] accepted_id;
    task check;input cond;input [255:0] msg;
        begin checks=checks+1;if(cond!==1'b1) begin $display("FAIL %0s",msg);$fatal(1);end end
    endtask
    task reset;
        begin @(negedge clk);rst_n=0;#1;check(!s_awready && !s_wready && !s_bvalid && !m_bready,"async reset gates all handshakes");
            s_awvalid=0;s_wvalid=0;s_wlast=0;s_bready=0;m_awready=0;m_wready=0;m_bvalid=0;
            repeat(2) @(negedge clk);rst_n=1;
        end
    endtask
    initial begin
        reset();
        for(i=0;i<80;i=i+1) begin
            // W precedes AW and must wait. Downstream AW/W backpressure varies.
            @(negedge clk);s_wvalid=1;m_wready=1;
            repeat(2) begin @(negedge clk);check(!m_wvalid && !s_wready,"W cannot precede owned AW");end
            s_awid=i*37+12'hd01;accepted_id=s_awid;s_awvalid=1;
            repeat(i%3) begin @(negedge clk);check(!s_awready,"AW downstream backpressure");end
            m_awready=1;@(negedge clk);
            // Keep next AW pending with a different ID while first write owns W.
            s_awid=~accepted_id;m_wready=0;beats=i%16+1;#1;
            for(n=0;n<beats;n=n+1) begin
                s_wlast=(n==beats-1);
                check(!m_awvalid && !s_awready,"no second outstanding AW");
                check(m_wvalid && m_wid==accepted_id && !s_wready,"latched owner WID under stall");
                @(negedge clk);m_wready=1;@(negedge clk);m_wready=0;#1;
                check(m_wid==accepted_id,"WID cannot follow live next AWID");
            end
            // Next write's W can arrive early while B is stalled; it must not
            // be tagged with the prior ID or accepted until its own AW.
            s_wvalid=1;m_wready=1;m_bvalid=1;
            repeat(4) begin @(negedge clk);check(s_bvalid && !m_bready && !s_awready,"B held owns write");
                check(!m_wvalid && !s_wready,"next W blocked after prior WLAST");end
            s_bready=1;@(negedge clk);s_bready=0;m_bvalid=0;
            check(s_awready && m_awvalid,"next AW released after B handshake");
            // Let next AW accept and reset before any W is transferred.
            @(negedge clk);check(m_wid==~accepted_id,"new ID ownership");reset();
        end
        // Cancel W-owned and blocked-B states; no stale owner can survive reset.
        for(i=0;i<3;i=i+1) begin
            @(negedge clk);s_awid=12'hfff;s_awvalid=1;m_awready=1;
            @(negedge clk);s_awvalid=0;
            if(i>=1) begin s_wvalid=1;s_wlast=1;m_wready=1;@(negedge clk);s_wvalid=0;end
            if(i==2) begin m_bvalid=1;@(negedge clk);check(s_bvalid,"B exists before reset");end
            reset();s_wvalid=1;m_wready=1;@(negedge clk);check(!m_wvalid && !s_wready,"old W remains gated after cancel");
            s_wvalid=0;m_wready=0;
        end
        $display("PASS gp_ps_write_adapter checks=%0d",checks);$finish;
    end
    initial begin #1000000;$fatal(1,"adapter timeout");end
endmodule
