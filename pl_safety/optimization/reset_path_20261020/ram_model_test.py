"""Exercise the unedited vendor ERAM model with exact exported RAM parameters.

Run only after the real-IP serial suite exits (the same single Questa license).
This bank test supplements RTL/full-system tests; it is not a top resource proxy.
"""
import argparse,json,re,shutil,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
TD=Path('D:/Anlogic/TD_Release_2026.1_SP2.200.067')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True)
    ap.add_argument('--netlist',default=str(HERE/'ram17_export_r1/mapped.v'))
    ap.add_argument('--spare-slot',action='store_true');a=ap.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
    out=HERE/a.tag;out.mkdir(exist_ok=False)
    source=Path(a.netlist).read_text()
    i=source.index('  // control/core/fabric/dma_core/motion/motion/kernel/raw_fifo/ramread')
    fragment=source[i:source.index('));',i)+3]
    params=fragment[fragment.index('#(')+2:fragment.index('))\n    \\')+1]
    assert '.DATA_WIDTH_A("40")' in params and '.DATA_WIDTH_B("40")' in params
    (out/'actual_bank.v.txt').write_text(fragment)
    tb='''`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg wen=0,ren=0;reg [5:0] wa=0,ra=0;reg [39:0] wd=0;
wire [39:0] rd;
DR1_PHY_ERAM #(
'''+params+''') dut(
 .clka(clk),.clkb(clk),.addra({3'b000,wa,5'b11111}),.addrb({3'b000,ra,5'b11111}),
 .csa({wen,2'b00}),.csb({ren,2'b00}),
 .dia({wd[18:15],wd[13:10],wd[8:5],wd[3:0]}),.dia_extra({wd[19],wd[14],wd[9],wd[4]}),
 .dib({wd[38:35],wd[33:30],wd[28:25],wd[23:20]}),.dib_extra({wd[39],wd[34],wd[29],wd[24]}),
 .doa({rd[18:15],rd[13:10],rd[8:5],rd[3:0]}),.doa_extra({rd[19],rd[14],rd[9],rd[4]}),
 .dob({rd[38:35],rd[33:30],rd[28:25],rd[23:20]}),.dob_extra({rd[39],rd[34],rd[29],rd[24]}));
reg [39:0] memory[0:63];reg [39:0] expected;
integer i,j,checks=0,collisions=0;
task cycle;
 input w,r;input [5:0] waddr,raddr;input [39:0] data;
 begin
  @(negedge clk);wen=w;ren=r;wa=waddr;ra=raddr;wd=data;
  @(posedge clk);
  if(r)expected=memory[raddr];
  if(w)memory[waddr]=data;
  #2;
  if(r)begin
   checks=checks+1;
   if(w && waddr==raddr)collisions=collisions+1;
   if(rd!==expected)begin
    $display("addr=%0d write=%0d got=%h expected=%h collision=%0d",raddr,w,rd,expected,w&&waddr==raddr);
    $fatal(1,"mapped vendor ERAM old-head semantics");
   end
  end
 end
endtask
initial begin
 #1000;
 for(i=0;i<64;i=i+1)cycle(1,0,i,0,40'h1234500000+i);
 for(j=0;j<8;j=j+1)for(i=0;i<64;i=i+1)
  cycle(1,1,i,i,40'h8000000000+j*1024+i);
 for(i=0;i<64;i=i+1)cycle(0,1,0,i,0);
 for(i=0;i<256;i=i+1)cycle(1,1,0,0,40'h7fffffffff-i);
 for(i=0;i<1024;i=i+1)cycle(1,1,(i*7)%64,(i*13+3)%64,{8'hff,i[31:0]});
 $display("PASS mapped_vendor_eram checks=%0d same_address=%0d",checks,collisions);$finish;
end
initial begin #1000000;$fatal(1,"RAM test timeout");end
endmodule
'''
    if a.spare_slot:tb=(HERE/'tb_spare_eram.v').read_text().replace('ACTUAL_PARAMETERS',params)
    (out/'tb.v').write_text(tb);result={'passed':False,'hashes_computed':False,'parameters_from':a.netlist,'spare_slot':a.spare_slot}
    try:
        commands=[('library',[shutil.which('vlib'),'work']),
          ('compile',[shutil.which('vlog'),'-work','work',str(TD/'sim_release/dr1/dr1_phy_gsr.v'),
                      str(TD/'sim_release/dr1/dr1_phy_eram.v'),*([str(ROOT/'pl_motion/rtl/motion_fifo.v')] if a.spare_slot else []),str(out/'tb.v')]),
          ('simulation',[shutil.which('vsim'),'-batch','work.tb','work.DR1_PHY_GSR','-do',
                         'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'])]
        for phase,cmd in commands:
            with (out/(phase+'.log')).open('w') as log:
                p=subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=180)
            assert p.returncode==0,(phase,p.returncode)
        log=(out/'simulation.log').read_text()
        assert not re.search(r'# \*\* (?:Fatal|Error)',log), 'Vendor model/scoreboard failure'
        if a.spare_slot:
            m=re.search(r'PASS spare_vendor_eram checks=(\d+) full_dual=(\d+) single_dual=(\d+)',log);assert m
            result.update(passed=True,checks=int(m[1]),full_dual=int(m[2]),single_dual=int(m[3]),same_address=0,vendor_model_unedited=True)
        else:
            m=re.search(r'PASS mapped_vendor_eram checks=(\d+) same_address=(\d+)',log);assert m
            result.update(passed=True,checks=int(m[1]),same_address=int(m[2]),vendor_model_unedited=True)
        print(result)
    except Exception:
        result['failure']=traceback.format_exc();raise
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
