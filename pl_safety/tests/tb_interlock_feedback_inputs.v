`timescale 1ns/1ps
// Preparation only: exercise the EXISTING parser's eligibility inputs.
// No interlock RTL, deadline, production parameter or wire-frame validation.
module tb_interlock_feedback_inputs;
 reg [255:0] raw;
 wire [5:0] task_index;
 wire formed,valid,known;
 wire [63:0] signed_value;
 wire [31:0] carry;
 wire [15:0] value;
 wire [7:0] enum_raw;
 integer checks=0,node,enumeration,field;
 reg [255:0] good;
 rs485_light_parse dut(raw,task_index,formed,valid,known,signed_value,carry,value,enum_raw);
 // enum_known alone is insufficient: the existing parser can expose it for
 // malformed data. The future monitor must also require a real commit event,
 // valid/formed data, matching generation/revision and this monitoring round.
 wire eligible=formed && valid && known &&
   (task_index==4 || task_index==9 || task_index==14);
 task check;
  input expected;
  input integer expected_axis;
  begin
   #1;checks=checks+1;
   if(eligible!==expected) $fatal(1,"feedback eligibility raw=%h expected=%b actual=%b",raw,expected,eligible);
   if(expected && (task_index/5!=expected_axis || enum_raw!==raw[7:0]))
    $fatal(1,"feedback axis/payload routing");
  end
 endtask
 initial begin
  for(node=0;node<3;node=node+1)begin
   for(enumeration=0;enumeration<256;enumeration=enumeration+1)begin
    raw=0;raw[255:248]=1;raw[247:240]=8'he0+node;
    raw[239:232]=8'h3e;raw[215:208]=1;raw[7:0]=enumeration;
    check(enumeration==1 || enumeration==2,node);
   end
   raw=0;raw[255:248]=1;raw[247:240]=8'he0+node;
   raw[239:232]=8'h3e;raw[215:208]=1;raw[7:0]=2;
   good=raw;
   for(field=1;field<256;field=field+1)begin
    raw=good;raw[231:224]=field;check(0,node);
   end
   for(field=0;field<256;field=field+1)begin
    if(field!=1)begin raw=good;raw[215:208]=field;check(0,node);end
    if(field!=1)begin raw=good;raw[255:248]=field;check(0,node);end
    if(field!=8'h3e)begin raw=good;raw[239:232]=field;check(0,node);end
   end
   for(field=8;field<48;field=field+1)begin
    raw=good;raw[field]=1;check(0,node);
   end
  end
  for(field=0;field<256;field=field+1)begin
   raw=good;raw[247:240]=field;
   check(field>=8'he0 && field<=8'he2,field-8'he0);
  end
  $display("PASS interlock_feedback_input_baseline checks=%0d (parser only)",checks);
  $finish;
 end
endmodule
