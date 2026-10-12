`timescale 1ns/1ps
// The actual PS GP0 has no WID. Serialize AW..B ownership and tag W from
// accepted AWID, never the live AWID bus. All other AXI payload passes unchanged.
module gp_ps_write_adapter(
    input wire clk,rst_n,
    input wire [11:0] s_awid,input wire s_awvalid,output wire s_awready,
    input wire s_wvalid,s_wlast,output wire s_wready,
    output wire s_bvalid,input wire s_bready,
    output wire m_awvalid,input wire m_awready,
    output wire [11:0] m_wid,output wire m_wvalid,input wire m_wready,
    input wire m_bvalid,output wire m_bready
);
    reg owned,data_done;
    reg [11:0] owner_id;
    assign m_awvalid=rst_n && !owned && s_awvalid;
    assign s_awready=rst_n && !owned && m_awready;
    assign m_wid=owner_id;
    assign m_wvalid=rst_n && owned && !data_done && s_wvalid;
    assign s_wready=rst_n && owned && !data_done && m_wready;
    assign s_bvalid=rst_n && owned && m_bvalid;
    assign m_bready=rst_n && owned && s_bready;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin owned<=0;data_done<=0;owner_id<=0;end
        else begin
            if(s_awvalid && s_awready) begin owned<=1;data_done<=0;owner_id<=s_awid;end
            if(s_wvalid && s_wready && s_wlast) data_done<=1;
            if(s_bvalid && s_bready) begin owned<=0;data_done<=0;end
        end
    end
endmodule
