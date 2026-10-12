`timescale 1ns/1ps
`include "generated/interface_defs.vh"
`ifdef GP_PS_BOUNDARY
module tb_gp_ps_control_top;
`else
module tb_gp_control_top;
`endif
    reg clk_100m=0;always #5 clk_100m=~clk_100m;
    reg arst_n=0;
    wire gp0_aclk,control_rst_n;wire [15:0] f2p_irq;
    reg [11:0] gp_awid=0,gp_wid=0,gp_arid=0;
    reg [32:0] gp_awaddr=0,gp_araddr=0;
    reg [3:0] gp_awlen=0,gp_arlen=0;
`ifdef GP_PS_BOUNDARY
    reg [1:0] gp_awsize=2,gp_arsize=2;
    reg gp_awlock=0,gp_arlock=0;
`else
    reg [2:0] gp_awsize=2,gp_arsize=2;
    reg [1:0] gp_awlock=0,gp_arlock=0;
`endif
    reg [1:0] gp_awburst=1,gp_arburst=1;
    reg [3:0] gp_awcache=0,gp_arcache=0;
    reg [2:0] gp_awprot=0,gp_arprot=0;
    reg gp_awvalid=0,gp_wvalid=0,gp_wlast=0,gp_bready=0,gp_arvalid=0,gp_rready=0;
    reg [31:0] gp_wdata=0;reg [3:0] gp_wstrb=0;
    wire gp_awready,gp_wready,gp_bvalid,gp_arready,gp_rvalid,gp_rlast;
    wire [11:0] gp_bid,gp_rid;wire [1:0] gp_bresp,gp_rresp;wire [31:0] gp_rdata;
`ifdef GP_PS_BOUNDARY
    gp_ps_control_top dut(
`else
    gp_control_top dut(
`endif
        .clk_100m(clk_100m),.arst_n(arst_n),.gp0_aclk(gp0_aclk),.control_rst_n(control_rst_n),.f2p_irq(f2p_irq),
        .gp_awid(gp_awid),.gp_awaddr(gp_awaddr),.gp_awlen(gp_awlen),.gp_awsize(gp_awsize),
        .gp_awburst(gp_awburst),.gp_awlock(gp_awlock),.gp_awcache(gp_awcache),.gp_awprot(gp_awprot),
        .gp_awvalid(gp_awvalid),.gp_awready(gp_awready),.gp_wdata(gp_wdata),
`ifndef GP_PS_BOUNDARY
        .gp_wid(gp_wid),
`endif
        .gp_wstrb(gp_wstrb),.gp_wlast(gp_wlast),.gp_wvalid(gp_wvalid),.gp_wready(gp_wready),
        .gp_bid(gp_bid),.gp_bresp(gp_bresp),.gp_bvalid(gp_bvalid),.gp_bready(gp_bready),
        .gp_arid(gp_arid),.gp_araddr(gp_araddr),.gp_arlen(gp_arlen),.gp_arsize(gp_arsize),
        .gp_arburst(gp_arburst),.gp_arlock(gp_arlock),.gp_arcache(gp_arcache),.gp_arprot(gp_arprot),
        .gp_arvalid(gp_arvalid),.gp_arready(gp_arready),.gp_rid(gp_rid),.gp_rdata(gp_rdata),
        .gp_rresp(gp_rresp),.gp_rlast(gp_rlast),.gp_rvalid(gp_rvalid),.gp_rready(gp_rready)
    );
    localparam [32:0] BASE={1'b0,`PLI_GP_GP_CONTROL_PROBE_V1_BASE};
    integer checks=0,i,j,k,seed=418;reg [31:0] value,random_value,expected=0;
    reg [3:0] strb;reg [11:0] id=0;
    task check;
        input condition;input [255:0] message;
        begin checks=checks+1;if(condition!==1'b1) begin $display("FAIL %0s at %0t",message,$time);$fatal(1);end end
    endtask
    task reset;
        begin @(negedge clk_100m);arst_n=0;
            gp_awvalid=0;gp_wvalid=0;gp_arvalid=0;gp_bready=0;gp_rready=0;
            #1;check(control_rst_n==0 && f2p_irq==0,"async assert");
            repeat(3) @(negedge clk_100m);arst_n=1;
            @(negedge clk_100m);check(!control_rst_n,"release stage1");
            @(negedge clk_100m);check(control_rst_n,"release stage2");
            repeat(3) @(negedge clk_100m);
        end
    endtask
    task send_aw;
        input [32:0] address;input [11:0] tid;input integer len,delay;
        begin repeat(delay) @(negedge clk_100m);
            @(negedge clk_100m);gp_awaddr=address;gp_awid=tid;gp_awlen=len;gp_awvalid=1;
            @(posedge clk_100m);while(!gp_awready) @(posedge clk_100m);
            @(negedge clk_100m);gp_awvalid=0;
        end
    endtask
    task send_w;
        input [31:0] data;input [3:0] strobe;input [11:0] tid;input last;input integer delay;
        begin repeat(delay) @(negedge clk_100m);
            @(negedge clk_100m);gp_wdata=data;gp_wstrb=strobe;gp_wid=tid;gp_wlast=last;gp_wvalid=1;
            @(posedge clk_100m);while(!gp_wready) @(posedge clk_100m);
            @(negedge clk_100m);gp_wvalid=0;
        end
    endtask
    task b_response;
        input [11:0] tid;input [1:0] resp;
        integer n;
        begin while(!gp_bvalid) @(negedge clk_100m);
            for(n=0;n<5;n=n+1) begin
                check(gp_bvalid && gp_bid==tid && gp_bresp==resp,"ID/BRESP stable");@(negedge clk_100m);
            end
            gp_bready=1;@(negedge clk_100m);gp_bready=0;
        end
    endtask
    task write;
        input [32:0] address;input [31:0] data;input [3:0] strobe;input [1:0] resp;
        begin id=id+12'd197;
            fork send_aw(address,id,0,id%4);send_w(data,strobe,id,1,(id+2)%4);join
            b_response(id,resp);
        end
    endtask
    task read;
        input [32:0] address;input [1:0] resp;output [31:0] data;
        integer n;
        begin id=id+12'd301;
            @(negedge clk_100m);gp_araddr=address;gp_arid=id;gp_arlen=0;gp_arvalid=1;
            @(posedge clk_100m);while(!gp_arready) @(posedge clk_100m);
            @(negedge clk_100m);gp_arvalid=0;
            while(!gp_rvalid) @(negedge clk_100m);data=gp_rdata;
            for(n=0;n<5;n=n+1) begin
                check(gp_rvalid && gp_rdata===data && gp_rid==id && gp_rresp==resp && gp_rlast,"ID/R stable");
                @(negedge clk_100m);
            end
            gp_rready=1;@(negedge clk_100m);gp_rready=0;
        end
    endtask
    task expect_read;
        input [31:0] offset,expected_value;
        begin read(BASE+offset,0,value);check(value===expected_value,"integrated read");end
    endtask
    task command;
        input [31:0] txn,op;
        begin write(BASE+`PLI_REG_CMD_OPCODE,op,15,0);write(BASE+`PLI_REG_CMD_ARG,0,15,0);
            write(BASE+`PLI_REG_TXN_ID,txn,15,0);write(BASE+`PLI_REG_CMD_SUBMIT,1,15,0);
            expect_read(`PLI_REG_ACK_ID,txn);expect_read(`PLI_REG_ACK_ERROR,0);expect_read(`PLI_REG_CMD_STATUS,14);
        end
    endtask
    always @(negedge clk_100m) begin
        check(gp0_aclk===clk_100m,"GP ACLK common source");check(f2p_irq[15:1]==0,"only f2p_irq bit0 used");
    end
    initial begin
        reset();expect_read(`PLI_REG_VERSION,1);expect_read(`PLI_REG_CAPS,15);expect_read(`PLI_REG_FEATURES,7);
        for(i=0;i<48;i=i+1) begin
            random_value=$random(seed);strb=$random(seed);
            write(BASE+`PLI_REG_TEST_RW,random_value,strb,0);
            for(k=0;k<4;k=k+1) if(strb[k]) expected[k*8 +: 8]=random_value[k*8 +: 8];
            expect_read(`PLI_REG_TEST_RW,expected);
        end
        write(BASE+33'h100000000+`PLI_REG_TEST_RW,0,15,3);
        read(BASE+33'h100000000+`PLI_REG_VERSION,3,value);expect_read(`PLI_REG_TEST_RW,expected);
        write(BASE+`PLI_REG_VERSION,0,15,2);read(BASE+12'h07c,2,value);
        // AXI3 INCR three-beat write to contiguous command shadows.
        id=12'hf63;
        fork
            send_aw(BASE+`PLI_REG_CMD_OPCODE,id,2,0);
            begin send_w(`PLI_CMD_SNAPSHOT,15,id,0,2);send_w(0,15,id,0,2);send_w(1,15,id,1,2);end
        join
        b_response(id,0);write(BASE+`PLI_REG_CMD_SUBMIT,1,15,0);
        expect_read(`PLI_REG_ACK_ID,1);expect_read(`PLI_REG_SNAP_VALID,1);expect_read(`PLI_REG_SNAP_ID,1);
        for(i=0;i<4;i=i+1) begin
            for(j=0;j<4;j=j+1) expect_read(`PLI_REG_SNAP_A0_POSITION_LO+i*16+j*4,0);
        end
        expect_read(`PLI_REG_SNAP_POSITION_VALID,0);expect_read(`PLI_REG_SNAP_STATE,1);
        expect_read(`PLI_REG_SNAP_SESSION_LO,0);expect_read(`PLI_REG_SNAP_SESSION_HI,0);
        expect_read(`PLI_REG_SNAP_DONE_SEQ,32'hffffffff);
        // Two-beat read, response ID and RLAST at each actual beat, backpressure.
        id=12'hdaa;
        @(negedge clk_100m);gp_araddr=BASE+`PLI_REG_SNAP_A0_POSITION_LO;gp_arid=id;gp_arlen=1;gp_arvalid=1;
        @(posedge clk_100m);while(!gp_arready) @(posedge clk_100m);
        @(negedge clk_100m);gp_arvalid=0;
        for(i=0;i<2;i=i+1) begin
            while(!gp_rvalid) @(negedge clk_100m);
            check(gp_rdata==0 && gp_rid==id && gp_rresp==0 && gp_rlast==(i==1),"INCR read beat");
            repeat(4) @(negedge clk_100m);gp_rready=1;@(negedge clk_100m);gp_rready=0;
        end
        write(BASE+`PLI_REG_IRQ_MASK,129,15,0);check(f2p_irq==1,"ACK irq mapped");
        write(BASE+`PLI_REG_IRQ_PENDING,1,15,0);check(f2p_irq==0,"ACK clear");
        write(BASE+`PLI_REG_TEST_IRQ_LEVEL,1,15,0);check(f2p_irq==1,"test IRQ source");
        write(BASE+`PLI_REG_IRQ_PENDING,128,15,0);check(f2p_irq==1,"persistent IRQ reassert");
        write(BASE+`PLI_REG_IRQ_MASK,0,15,0);check(f2p_irq==0,"disable IRQ");
        write(BASE+`PLI_REG_TEST_IRQ_LEVEL,0,15,0);write(BASE+`PLI_REG_IRQ_PENDING,128,15,0);
        write(BASE+`PLI_REG_IRQ_MASK,129,15,0);check(f2p_irq==0,"re-enable clean IRQ");
        command(2,`PLI_CMD_NOP);check(f2p_irq==1,"new event after rearm");
        // Time increases, duplicate snapshot does not resample.
        read(BASE+`PLI_REG_SNAP_TIME_LO,0,value);expected=value;
        command(3,`PLI_CMD_SNAPSHOT);read(BASE+`PLI_REG_SNAP_TIME_LO,0,value);check(value>expected,"1MHz snapshot time progression");
        expected=value;command(3,`PLI_CMD_SNAPSHOT);expect_read(`PLI_REG_SNAP_TIME_LO,expected);
        // AW, W, B, AR, R partial/blocked cancellation through real converter.
        for(i=0;i<5;i=i+1) begin
            reset();
            case(i)
                0: begin @(negedge clk_100m);gp_awaddr=BASE;gp_awvalid=1;end
                1: begin @(negedge clk_100m);gp_wdata=1;gp_wstrb=15;gp_wvalid=1;end
                2: begin fork send_aw(BASE+`PLI_REG_TEST_RW,1,0,0);send_w(1,15,1,1,0);join
                    while(!gp_bvalid) @(negedge clk_100m);end
                3: begin @(negedge clk_100m);gp_araddr=BASE;gp_arvalid=1;end
                4: begin @(negedge clk_100m);gp_araddr=BASE;gp_arvalid=1;
                    @(posedge clk_100m);while(!gp_arready) @(posedge clk_100m);
                    @(negedge clk_100m);gp_arvalid=0;while(!gp_rvalid) @(negedge clk_100m);end
            endcase
            reset();check(!gp_bvalid && !gp_rvalid,"reset cancels converter responses");
            command(1,`PLI_CMD_NOP);expect_read(`PLI_REG_SNAP_VALID,0);
        end
        fork send_aw(BASE+`PLI_REG_TEST_RW,12'habc,0,0);send_w(32'habcdef01,15,12'habc,1,0);join
        while(!gp_bvalid) @(negedge clk_100m);
        expect_read(`PLI_REG_TEST_RW,32'habcdef01);check(gp_bvalid,"real converter R progresses with B held");b_response(12'habc,0);
        id=12'h123;
        @(negedge clk_100m);gp_araddr=BASE+`PLI_REG_TEST_RW;gp_arid=id;gp_arlen=0;gp_arvalid=1;
        @(posedge clk_100m);while(!gp_arready) @(posedge clk_100m);
        @(negedge clk_100m);gp_arvalid=0;while(!gp_rvalid) @(negedge clk_100m);
        write(BASE+`PLI_REG_TEST_RW,32'h10203040,15,0);
        check(gp_rvalid && gp_rdata==32'habcdef01 && gp_rid==12'h123,"real R held through parallel W");
        gp_rready=1;@(negedge clk_100m);gp_rready=0;expect_read(`PLI_REG_TEST_RW,32'h10203040);
`ifdef GP_PS_BOUNDARY
        $display("PASS gp_ps_control_top checks=%0d",checks);$finish;
`else
        $display("PASS gp_control_top checks=%0d",checks);$finish;
`endif
    end
    initial begin #2000000;$fatal(1,"integration timeout");end
endmodule
