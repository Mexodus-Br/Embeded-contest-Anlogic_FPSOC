"""Project current management-empty qualification from exact next source state.

The clocked source processes stay intact. A mechanical combinational projection
retains every branch and assignment priority, selecting only specified D values.
It is registered on the same edge as the source registers, so no grant/stop is
delayed. Assertions check equality with the original current predicate.
"""
import argparse,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent

def project(text,stop,targets,extra):
    marker='always @(posedge clk or negedge rst_n)begin'
    assert text.count(marker)==1
    start=text.index(marker);end=text.index(stop,start)
    process=text[start:end].strip();assert process.endswith('end')
    body=re.sub(r'//[^\n]*|/\*.*?\*/','',process[len(marker):-3],flags=re.S)
    counts={n:0 for n in targets}
    # <= inside an if/case expression is a comparison, not an NBA. Select
    # procedural assignments only at parenthesis depth zero, then replace
    # from right to left so every original branch/expression is retained.
    depth=0;levels=[]
    for char in body:
        levels.append(depth)
        if char=='(':depth+=1
        elif char==')':depth-=1
    assert depth==0
    edits=[]
    for token in re.finditer('<=',body):
        if levels[token.start()]!=0:continue
        lhs=re.search(r'(\w+(?:\[[^]]+\])?)\s*$',body[:token.start()]);assert lhs
        end_rhs=body.index(';',token.end());target=lhs[1];rhs=body[token.end():end_rhs]
        replacement=';'
        if target in targets:counts[target]+=1;replacement='projected_'+target+'='+rhs+';'
        edits.append((lhs.start(),end_rhs+1,replacement))
    for lo,hi,replacement in reversed(edits):body=body[:lo]+replacement+body[hi:]
    assert all(counts.values()),counts
    declarations='\n'.join('reg '+width+' projected_'+n+';' for n,width in targets.items())
    defaults='\n'.join('projected_'+n+'='+n+';' for n in targets)
    # Empty original branches are deliberate. They preserve guard/priority
    # exactly while synthesis removes logic that cannot affect the selected D.
    logic='\n// Exact next-state projection for current management qualification.\n'+declarations+'\nalways @*begin\n'+defaults+'\n'+body+'\nend\n'+extra+'\n'
    return text.replace('endmodule',logic+'endmodule'),counts

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);a=p.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
    out=HERE/a.tag;out.mkdir(exist_ok=False)
    s=(ROOT/'pl_motion/rtl/motion_stream_rx.v').read_text()
    old='output reg [31:0] packet_count';assert s.count(old)==1
    s=s.replace(old,old+',\n output wire next_packet_empty')
    s,n=project(s,'endmodule',{'state':'[2:0]'},'assign next_packet_empty=projected_state==IDLE;')
    (out/'motion_stream_rx.v').write_text(s);print('RX source state assignment sites',n)
    s=(ROOT/'pl_motion/rtl/continuous_motion.v').read_text()
    old='output wire [2:0] home_fault';assert s.count(old)==1
    s=s.replace(old,old+',output wire next_session_empty')
    s,n=project(s,' // synthesis translate_off',{'session_valid':''},'assign next_session_empty=!projected_session_valid;')
    (out/'continuous_motion.v').write_text(s);print('Session source assignment sites',n)
    s=(ROOT/'pl_motion/rtl/motion_service.v').read_text()
    old='wire idle_admission_fence=!session_valid && !command_busy && !ah && !wh &&\n  !packet_busy &&\n  !(HOME_SUPPORT && home_owner);';assert s.count(old)==1
    s=s.replace(old,'''wire next_session_empty,next_packet_empty;
 reg management_clear_q;
 wire idle_admission_fence=management_clear_q && !(HOME_SUPPORT && home_owner);''')
    old='.packet_closed(packet_closed),.packet_count(packet_count));';assert s.count(old)==1
    s=s.replace(old,'.packet_closed(packet_closed),.packet_count(packet_count),.next_packet_empty(next_packet_empty));')
    old='.safety_invalidate(safety_invalidate),.safety_pulse_safe(safety_pulse_safe),.home_fault(home_fault));'
    assert s.count(old)==1, 'Locate exact existing kernel connection'
    s=s.replace(old,old[:-2]+',.next_session_empty(next_session_empty));')
    extra='''always @(posedge clk or negedge rst_n)
 if(!rst_n)management_clear_q<=1;
 else management_clear_q<=next_session_empty && next_packet_empty &&
      !projected_ah && !projected_wh && !projected_command_busy;
// synthesis translate_off
always @(posedge clk)if(rst_n)
 if(management_clear_q !== (!session_valid && !packet_busy && !ah && !wh && !command_busy))
  $fatal(1,"management current-state projection mismatch");
// synthesis translate_on'''
    s,n=project(s,' // Full atomic replacement',{'ah':'','wh':'','command_busy':''},extra)
    (out/'motion_service.v').write_text(s);print('Mailbox source assignment sites',n)
    print('PASS isolated management projection; one FF, zero added interface cycles')

if __name__=='__main__':main()
