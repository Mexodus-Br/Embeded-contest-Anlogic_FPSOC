`timescale 1ns/1ps
module tb_motion_fifo;
    parameter DEPTH=3;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,flush=0,in_valid=0,out_ready=0;
    reg [15:0] in_data=0;
    wire in_ready,out_valid;wire [15:0] out_data;wire [31:0] level;
    motion_fifo #(.DEPTH(DEPTH)) dut(clk,rst_n,flush,in_valid,in_ready,in_data,out_valid,out_ready,out_data,level);
    reg [15:0] model[0:DEPTH-1];integer count=0,checks=0,j,i,seed=12345;
    reg push,pop;reg [15:0] held;
    task check;input condition;begin checks=checks+1;if(condition!==1'b1)$fatal(1,"FIFO check %0d",checks);end endtask
    task tick;
        begin @(posedge clk);
            if(!rst_n || flush)count=0;
            else begin
                check(out_valid==(count!=0));
                pop=out_valid&&out_ready;push=in_valid&&in_ready;
                check(in_ready==(count<DEPTH || pop));
                if(out_valid)check(out_data===model[0]);
                if(pop)begin for(j=0;j<count-1;j=j+1)model[j]=model[j+1];count=count-1;end
                if(push)begin model[count]=in_data;count=count+1;end
            end
            #2;check(level==count);
        end
    endtask
    initial begin
        tick;@(negedge clk);rst_n=1;
        for(i=0;i<DEPTH;i=i+1)begin in_valid=1;in_data=i;tick;@(negedge clk);end
        check(!in_ready && level==DEPTH);held=out_data;
        repeat(8)begin in_data=in_data+1;tick;check(out_data==held);@(negedge clk);end
        out_ready=1;repeat(DEPTH*3)begin in_data=in_data+1;tick;check(level==DEPTH);@(negedge clk);end
        flush=1;tick;check(!out_valid && !in_ready);@(negedge clk);flush=0;in_valid=0;
        tick;check(!out_valid);@(negedge clk);
        for(i=0;i<2000;i=i+1)begin
            in_valid=$random(seed);out_ready=$random(seed);in_data=$random(seed);flush=(i%127==0);
            tick;@(negedge clk);
        end
        flush=0;in_valid=0;out_ready=1;repeat(DEPTH+2)begin tick;@(negedge clk);end
        check(level==0);$display("PASS FIFO depth=%0d checks=%0d",DEPTH,checks);$finish;
    end
endmodule
