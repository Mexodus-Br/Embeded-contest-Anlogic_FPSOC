// Pure field interpretation. No motion control, calibration or floating point.
module rs485_light_parse #(parameter integer SLAVE_COUNT=3,parameter [79:0] SLAVE_ADDRS=80'he2e1e0)(
 input wire [255:0] raw,output reg [5:0] task_index,
 output reg well_formed,data_valid,enum_known,output reg [63:0] signed_value,
 output wire [31:0] carry,output wire [15:0] value,output wire [7:0] enum_raw);
 `include "rs485_defs.vh"
 integer i,q,node,len;
 assign carry=raw[47:16];assign value=raw[15:0];assign enum_raw=raw[7:0];
 always @* begin
  node=-1;q=-1;len=0;
  for(i=0;i<SLAVE_COUNT;i=i+1) if(raw[247:240]==SLAVE_ADDRS[i*8+:8]) node=i;
  for(i=0;i<5;i=i+1) if(raw[239:232]==query_code(i)) begin q=i;len=query_length(i);end
  task_index=0;well_formed=0;data_valid=0;enum_known=0;signed_value=0;
  if(node>=0 && q>=0 && raw[255:248]==`RS_VERSION) begin
   task_index=node*5+q;
   if(raw[231:224]==`RS_STATUS_VALID) begin
    well_formed=raw[215:208]==len && (len==6 || (raw[47:0]>>(len*8))==0);
    data_valid=well_formed;
    case(q)
     0:signed_value={{32{raw[47]}},raw[47:16]};
     1:signed_value={{32{raw[31]}},raw[31:0]};
     2:signed_value={{48{raw[15]}},raw[15:0]};
     3,4:begin signed_value={56'd0,raw[7:0]};enum_known=raw[7:0]==1 || raw[7:0]==2;end
    endcase
   end else well_formed=raw[231:224]<=`RS_STATUS_BUS_BUSY && raw[215:208]==0 && raw[47:0]==0;
  end
 end
endmodule
