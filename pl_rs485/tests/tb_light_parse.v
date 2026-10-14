`timescale 1ns/1ps
module tb_light_parse;
 reg [255:0] raw=0;wire [5:0] index;wire formed,valid,known;wire [63:0] signed_value;wire [31:0] carry;wire [15:0] value;wire [7:0] enum_raw;
 rs485_light_parse dut(raw,index,formed,valid,known,signed_value,carry,value,enum_raw);
 integer checks=0,node,k;reg [7:0] address;
 task vector;input [7:0] q,len;input [47:0] data;input [63:0] expected;input integer slot,enum_expected;
  begin raw={8'd1,address,q,8'd0,8'd1,len,32'd5,64'hfffffffffffffff0,64'd3,data};#1;
   checks=checks+1;if(!formed || !valid || index!=node*5+slot || signed_value!==expected || known!=enum_expected) $fatal(1,"parse boundary node=%d q=%h data=%h result=%h expected=%h",node,q,data,signed_value,expected);
   if(slot==0 && (carry!==data[47:16] || value!==data[15:0])) $fatal(1,"separate carry/value");
  end
 endtask
 initial begin
  for(node=0;node<3;node=node+1) begin address=8'he0+node;
   vector(8'h30,6,48'h800000000000,64'hffffffff80000000,0,0);
   vector(8'h30,6,48'hffffffffffff,64'hffffffffffffffff,0,0);
   vector(8'h30,6,48'h000000000000,0,0,0);
   vector(8'h30,6,48'h7fffffffffff,64'h000000007fffffff,0,0);
   vector(8'h33,4,48'h000080000000,64'hffffffff80000000,1,0);
   vector(8'h33,4,48'h0000ffffffff,64'hffffffffffffffff,1,0);
   vector(8'h33,4,0,0,1,0);vector(8'h33,4,1,1,1,0);vector(8'h33,4,48'h00007fffffff,64'h7fffffff,1,0);
   vector(8'h39,2,48'h000000008000,64'hffffffffffff8000,2,0);
   vector(8'h39,2,48'h00000000ffff,64'hffffffffffffffff,2,0);
   vector(8'h39,2,0,0,2,0);vector(8'h39,2,1,1,2,0);vector(8'h39,2,48'h000000007fff,32767,2,0);
   for(k=0;k<2;k=k+1) begin
    vector(k==0?8'h3a:8'h3e,1,0,0,k+3,0);vector(k==0?8'h3a:8'h3e,1,1,1,k+3,1);
    vector(k==0?8'h3a:8'h3e,1,2,2,k+3,1);vector(k==0?8'h3a:8'h3e,1,255,255,k+3,0);
   end
  end
  raw[231:224]=3;raw[215:208]=0;raw[47:0]=0;#1;if(!formed || valid) $fatal(1,"communication failure validity");
  raw[47:0]=1;#1;if(formed) $fatal(1,"error with fake data");
  raw[47:0]=0;raw[247:240]=8'he3;#1;if(formed) $fatal(1,"M4 disabled");
  $display("PASS light parse all nodes signed extrema/zero/unknown checks=%0d",checks);$finish;
 end
endmodule
