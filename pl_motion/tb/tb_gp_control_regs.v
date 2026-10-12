`timescale 1ns/1ps
`include "generated/interface_defs.vh"
module tb_gp_control_regs;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [32:0] s_awaddr=0,s_araddr=0;
    reg s_awvalid=0,s_wvalid=0,s_bready=0,s_arvalid=0,s_rready=0;
    reg [31:0] s_wdata=0; reg [3:0] s_wstrb=0;
    wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid,irq;
    wire [1:0] s_bresp,s_rresp; wire [31:0] s_rdata;
    reg [255:0] actual_position=0,actual_pulses=0;
    reg [3:0] actual_valid=0; reg [31:0] actual_state=0;
    reg [63:0] actual_session=0;
    reg [31:0] actual_accepted_seq=0,actual_done_seq=0;
    gp_control_regs dut(.clk(clk),.rst_n(rst_n),.s_awaddr(s_awaddr),.s_awvalid(s_awvalid),.s_awready(s_awready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_bresp(s_bresp),.s_bvalid(s_bvalid),.s_bready(s_bready),.s_araddr(s_araddr),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_rdata(s_rdata),.s_rresp(s_rresp),.s_rvalid(s_rvalid),.s_rready(s_rready),.actual_position(actual_position),.actual_pulses(actual_pulses),.actual_valid(actual_valid),.actual_state(actual_state),.actual_session(actual_session),.actual_accepted_seq(actual_accepted_seq),.actual_done_seq(actual_done_seq),.irq(irq));
    localparam [32:0] BASE={1'b0,`PLI_GP_GP_CONTROL_PROBE_V1_BASE};
    integer checks=0,seed=91,i,j,k; reg [31:0] value,expected_scratch=0,random_value;
    reg [3:0] strobe;
    reg [255:0] expected_position,expected_pulses;
    reg [63:0] expected_time,expected_session;
    reg [3:0] expected_valid;
    reg [31:0] expected_state,expected_accepted,expected_done;
    reg [63:0] ref_timestamp=0; integer ref_div=0;
    task check;
        input condition; input [255:0] message;
        begin checks=checks+1; if(condition!==1'b1) begin
            $display("FAIL %0s at %0t check %0d",message,$time,checks);$fatal(1);
        end end
    endtask
    task aw;
        input [32:0] address;
        begin @(negedge clk);s_awaddr=address;s_awvalid=1;
            @(posedge clk);while(!s_awready) @(posedge clk);
            @(negedge clk);s_awvalid=0;
        end
    endtask
    task wd;
        input [31:0] data; input [3:0] strb;
        begin @(negedge clk);s_wdata=data;s_wstrb=strb;s_wvalid=1;
            @(posedge clk);while(!s_wready) @(posedge clk);
            @(negedge clk);s_wvalid=0;
        end
    endtask
    task response;
        input [1:0] resp; input integer stall;
        integer n;
        begin
            while(!s_bvalid) @(negedge clk);
            check(s_bresp==resp,"BRESP");
            for(n=0;n<stall;n=n+1) begin
                @(negedge clk);check(s_bvalid && s_bresp==resp,"B stable under backpressure");
                check(!s_awready && !s_wready,"one write in flight");
            end
            s_bready=1;@(negedge clk);s_bready=0;
        end
    endtask
    task write;
        input [32:0] address; input [31:0] data; input [3:0] strb;
        input integer order; input [1:0] resp;
        begin
            case(order)
                0: begin aw(address);repeat(2) @(negedge clk);wd(data,strb);end
                1: begin wd(data,strb);repeat(2) @(negedge clk);aw(address);end
                2: fork aw(address);wd(data,strb);join
            endcase
            response(resp,3);
        end
    endtask
    task read;
        input [32:0] address; input [1:0] resp; output [31:0] data;
        integer n;
        begin @(negedge clk);s_araddr=address;s_arvalid=1;
            @(posedge clk);while(!s_arready) @(posedge clk);
            @(negedge clk);s_arvalid=0;
            while(!s_rvalid) @(negedge clk);
            data=s_rdata;check(s_rresp==resp,"RRESP");
            // Mutate address while R is blocked; captured response must not change.
            s_araddr=BASE+`PLI_REG_CMD_SUBMIT;
            for(n=0;n<3;n=n+1) begin
                @(negedge clk);check(s_rvalid && s_rdata===data && s_rresp==resp,"R stable under backpressure");
                check(!s_arready,"one read in flight");
            end
            s_rready=1;@(negedge clk);s_rready=0;
        end
    endtask
    task expect_read;
        input [31:0] offset,expected;
        begin read(BASE+offset,0,value);check(value===expected,"register read value");end
    endtask
    task shadows;
        input [31:0] id,op,arg;
        begin write(BASE+`PLI_REG_CMD_OPCODE,op,15,2,0);
            write(BASE+`PLI_REG_CMD_ARG,arg,15,0,0);
            write(BASE+`PLI_REG_TXN_ID,id,15,1,0);
        end
    endtask
    task command;
        input [31:0] id,op,arg,err;
        begin shadows(id,op,arg);write(BASE+`PLI_REG_CMD_SUBMIT,1,15,2,0);
            expect_read(`PLI_REG_ACK_ID,id);expect_read(`PLI_REG_ACK_ERROR,err);
            expect_read(`PLI_REG_CMD_STATUS,err==0 ? 14 : 10);
            expect_read(`PLI_REG_LAST_TXN_ID,id);
        end
    endtask
    task reset;
        begin @(negedge clk);rst_n=0;s_awvalid=0;s_wvalid=0;s_arvalid=0;s_bready=0;s_rready=0;
            #1;check(!irq && !s_bvalid && !s_rvalid,"asynchronous reset output");
            repeat(3) @(negedge clk);rst_n=1;repeat(2) @(negedge clk);
        end
    endtask
    // Independent time model. Producer values change on every edge, including
    // all signed64 endpoints; the expected sample observes PRE-edge values.
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin ref_timestamp<=0;ref_div<=0;end
        else begin
            if(ref_div==99) begin ref_timestamp<=ref_timestamp+1;ref_div<=0;end
            else ref_div<=ref_div+1;
            actual_position<=actual_position+256'h0000000000000001_ffffffffffffffff_0000000000000001_0000000000000001;
            actual_pulses<=actual_pulses+256'h0000000000000001_0000000000000001_0000000000000001_0000000000000001;
            actual_session<=actual_session+1;actual_valid<=actual_valid+1;
            actual_state<=actual_state+1;actual_accepted_seq<=actual_accepted_seq+1;actual_done_seq<=actual_done_seq+2;
            if(dut.busy && dut.phase==2 && !dut.duplicate && dut.result_error==0 && dut.captured_opcode==`PLI_CMD_SNAPSHOT) begin
                expected_position=actual_position;expected_pulses=actual_pulses;
                expected_session=actual_session;expected_valid=actual_valid;
                expected_state=actual_state;expected_accepted=actual_accepted_seq;expected_done=actual_done_seq;
                expected_time=ref_timestamp;
            end
        end
    end
    task frame;
        begin
            for(j=0;j<4;j=j+1) begin
                expect_read(`PLI_REG_SNAP_A0_POSITION_LO+j*16,expected_position[j*64 +: 32]);
                expect_read(`PLI_REG_SNAP_A0_POSITION_HI+j*16,expected_position[j*64+32 +: 32]);
                expect_read(`PLI_REG_SNAP_A0_PULSE_LO+j*16,expected_pulses[j*64 +: 32]);
                expect_read(`PLI_REG_SNAP_A0_PULSE_HI+j*16,expected_pulses[j*64+32 +: 32]);
            end
            expect_read(`PLI_REG_SNAP_TIME_LO,expected_time[31:0]);expect_read(`PLI_REG_SNAP_TIME_HI,expected_time[63:32]);
            expect_read(`PLI_REG_SNAP_SESSION_LO,expected_session[31:0]);expect_read(`PLI_REG_SNAP_SESSION_HI,expected_session[63:32]);
            expect_read(`PLI_REG_SNAP_STATE,expected_state);expect_read(`PLI_REG_SNAP_POSITION_VALID,expected_valid);
            expect_read(`PLI_REG_SNAP_ACCEPTED_SEQ,expected_accepted);expect_read(`PLI_REG_SNAP_DONE_SEQ,expected_done);
        end
    endtask
    initial begin
        reset();expect_read(`PLI_REG_VERSION,1);expect_read(`PLI_REG_CAPS,15);
        expect_read(`PLI_REG_FEATURES,7);expect_read(`PLI_REG_TICK_HZ,1000000);
        expect_read(`PLI_REG_STATE,`PLI_STATE_NOT_READY);expect_read(`PLI_REG_SNAP_VALID,0);
        expect_read(`PLI_REG_SNAP_DONE_SEQ,32'hffffffff);
        for(i=0;i<80;i=i+1) begin
            random_value=$random(seed);strobe=$random(seed);
            write(BASE+`PLI_REG_TEST_RW,random_value,strobe,i%3,0);
            for(k=0;k<4;k=k+1) if(strobe[k]) expected_scratch[k*8 +: 8]=random_value[k*8 +: 8];
            expect_read(`PLI_REG_TEST_RW,expected_scratch);
        end
        write(BASE+`PLI_REG_VERSION,123,15,2,2);
        write(BASE+`PLI_REG_TEST_RW+1,123,15,2,2);
        write(BASE+12'h07c,123,15,2,2);
        write(BASE+`PLI_REG_TEST_RW+4096,123,15,2,3);
        write(BASE+33'h100000000+`PLI_REG_TEST_RW,123,15,2,3);
        expect_read(`PLI_REG_TEST_RW,expected_scratch);
        read(BASE+4096,3,value);read(BASE+33'h100000000+`PLI_REG_TEST_RW,3,value);
        read(BASE+`PLI_REG_CMD_SUBMIT,2,value);read(BASE+12'h200,2,value);read(BASE+1,2,value);
        write(BASE+`PLI_REG_CMD_SUBMIT,1,1,2,2);write(BASE+`PLI_REG_CMD_SUBMIT,1,0,2,0);
        expect_read(`PLI_REG_LAST_TXN_ID,0);
        command(1,`PLI_CMD_NOP,0,0);expect_read(`PLI_REG_SNAP_VALID,0);
        // Masked event must latch and assert immediately on unmask.
        expect_read(`PLI_REG_IRQ_PENDING,1);check(!irq,"masked ACK");
        write(BASE+`PLI_REG_IRQ_MASK,1,15,2,0);check(irq,"unmask latched ACK");
        write(BASE+`PLI_REG_IRQ_PENDING,1,15,2,0);check(!irq,"clear ACK");
        command(2,`PLI_CMD_SNAPSHOT,0,0);expect_read(`PLI_REG_SNAP_ID,2);expect_read(`PLI_REG_SNAP_VALID,1);frame();
        // Repeat must reuse the frame despite continuously changing inputs.
        command(2,`PLI_CMD_SNAPSHOT,0,0);frame();
        shadows(2,`PLI_CMD_NOP,0);write(BASE+`PLI_REG_CMD_SUBMIT,1,15,2,2);expect_read(`PLI_REG_ACK_ID,2);frame();
        shadows(1,`PLI_CMD_NOP,0);write(BASE+`PLI_REG_CMD_SUBMIT,1,15,2,2);expect_read(`PLI_REG_LAST_TXN_ID,2);
        shadows(0,`PLI_CMD_NOP,0);write(BASE+`PLI_REG_CMD_SUBMIT,1,15,2,2);
        command(4,`PLI_CMD_START,0,`PLI_ERR_BAD_COMMAND);frame();
        command(4,`PLI_CMD_START,0,`PLI_ERR_BAD_COMMAND);
        command(5,`PLI_CMD_NOP,1,`PLI_ERR_BAD_COMMAND);frame();
        // Reserved writes and partial full-strobe writes are inert.
        write(BASE+`PLI_REG_IRQ_MASK,2,15,2,2);expect_read(`PLI_REG_IRQ_MASK,1);
        write(BASE+`PLI_REG_IRQ_PENDING,1,1,2,2);check(irq,"partial clear rejected");
        write(BASE+`PLI_REG_TEST_IRQ_LEVEL,3,15,2,2);
        write(BASE+`PLI_REG_IRQ_PENDING,1,15,2,0);
        write(BASE+`PLI_REG_TEST_IRQ_LEVEL,1,15,2,0);
        expect_read(`PLI_REG_IRQ_PENDING,128);check(!irq,"masked TEST");
        write(BASE+`PLI_REG_IRQ_MASK,129,1,2,0);check(irq,"byte unmask TEST");
        write(BASE+`PLI_REG_IRQ_PENDING,128,15,2,0);check(irq,"persistent set wins clear");
        write(BASE+`PLI_REG_TEST_IRQ_LEVEL,0,15,2,0);
        write(BASE+`PLI_REG_IRQ_PENDING,128,15,2,0);check(!irq,"source clear and rearm");
        // Explicit publish/W1C coincidence: clear ACK on the publish edge.
        shadows(6,`PLI_CMD_NOP,0);
        fork aw(BASE+`PLI_REG_CMD_SUBMIT);wd(1,15);join
        while(!s_bvalid) @(negedge clk);
        s_bready=1;@(negedge clk);s_bready=0;
        // Independent captures for W1C can be accepted here.
        s_awaddr=BASE+`PLI_REG_IRQ_PENDING;s_awvalid=1;s_wdata=1;s_wstrb=15;s_wvalid=1;
        @(negedge clk);s_awvalid=0;s_wvalid=0;
        response(0,0);expect_read(`PLI_REG_IRQ_PENDING,1);
        // Busy on same publish cycle must reject a competing submit.
        shadows(7,`PLI_CMD_NOP,0);
        fork aw(BASE+`PLI_REG_CMD_SUBMIT);wd(1,15);join
        while(!s_bvalid) @(negedge clk);s_bready=1;@(negedge clk);s_bready=0;
        s_awaddr=BASE+`PLI_REG_CMD_SUBMIT;s_awvalid=1;s_wdata=1;s_wstrb=15;s_wvalid=1;
        @(negedge clk);s_awvalid=0;s_wvalid=0;response(2,0);expect_read(`PLI_REG_ACK_ID,7);
        // ID upper bound supported without wrap.
        command(32'hffffffff,`PLI_CMD_NOP,0,0);
        shadows(1,`PLI_CMD_NOP,0);write(BASE+`PLI_REG_CMD_SUBMIT,1,15,2,2);
        // Cancel in every command phase, plus partial AW/W and held R/B.
        for(i=0;i<4;i=i+1) begin
            reset();shadows(1,`PLI_CMD_SNAPSHOT,0);
            fork aw(BASE+`PLI_REG_CMD_SUBMIT);wd(1,15);join
            while(!s_bvalid) @(negedge clk);
            repeat(i) @(negedge clk);reset();repeat(8) @(negedge clk);
            expect_read(`PLI_REG_CMD_STATUS,0);expect_read(`PLI_REG_SNAP_VALID,0);
            expect_read(`PLI_REG_LAST_TXN_ID,0);expect_read(`PLI_REG_IRQ_PENDING,0);
        end
        aw(BASE+`PLI_REG_TEST_RW);reset();wd(32'hdeadbeef,15);reset();expect_read(`PLI_REG_TEST_RW,0);
        @(negedge clk);s_araddr=BASE;s_arvalid=1;@(negedge clk);s_arvalid=0;
        check(s_rvalid,"held R before reset");reset();
        // Force two independent timestamp rollover boundaries as verification fixture.
        @(negedge clk);dut.timestamp=64'h00000000ffffffff;ref_timestamp=64'h00000000ffffffff;
        command(1,`PLI_CMD_SNAPSHOT,0,0);frame();
        @(negedge clk);dut.timestamp=64'hffffffffffffffff;ref_timestamp=64'hffffffffffffffff;
        dut.tick_div=99;ref_div=99;@(negedge clk);check(dut.timestamp==0,"u64 modulo rollover");
        actual_position=256'h8000000000000000_7fffffffffffffff_ffffffffffffffff_0000000000000000;
        command(2,`PLI_CMD_SNAPSHOT,0,0);frame();
        // Read channel progresses while B is held; write channel progresses
        // while R is held, and a captured R payload never tracks later writes.
        fork aw(BASE+`PLI_REG_TEST_RW);wd(32'h12345678,15);join
        while(!s_bvalid) @(negedge clk);
        expect_read(`PLI_REG_TEST_RW,32'h12345678);check(s_bvalid,"read while B stalled");response(0,0);
        @(negedge clk);s_araddr=BASE+`PLI_REG_TEST_RW;s_arvalid=1;
        @(negedge clk);s_arvalid=0;check(s_rvalid && s_rdata==32'h12345678,"captured R before parallel W");
        write(BASE+`PLI_REG_TEST_RW,32'h87654321,15,2,0);
        check(s_rvalid && s_rdata==32'h12345678,"R held through parallel W");
        s_rready=1;@(negedge clk);s_rready=0;expect_read(`PLI_REG_TEST_RW,32'h87654321);
        $display("PASS gp_control_regs checks=%0d",checks);$finish;
    end
    initial begin #1000000;$fatal(1,"timeout");end
endmodule
