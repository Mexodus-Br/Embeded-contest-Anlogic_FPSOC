"""Isolated prepared-FIFO data-write cofactor; control handshakes stay fenced."""
import argparse,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);a=p.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
    out=HERE/a.tag;out.mkdir(exist_ok=False)
    s=(ROOT/'pl_motion/rtl/motion_fifo.v').read_text()
    old='DEPTH=2, SPARE_SLOT=0)';assert s.count(old)==1
    s=s.replace(old,'DEPTH=2, SPARE_SLOT=0, SPECULATIVE_STORAGE=0)')
    old='if(push)begin memory[wr]<=in_data;wr<=';assert s.count(old)==1
    s=s.replace(old,'if(push)begin wr<=')
    old='    always @(posedge clk or negedge rst_n)begin';assert s.count(old)==1
    s=s.replace(old,'''    // A flush invalidates the queue through its original control edge.
    // With the private opt-in, a speculative write on that edge is invisible:
    // no count/pointer advances and every newly admitted slot is overwritten.
    // Avoid routing the cancellation cone to every payload memory write pin.
    wire store=SPECULATIVE_STORAGE ?
        in_valid && (count<DEPTH || (count!=0 && out_ready)) : push;
    always @(posedge clk)if(store)memory[wr]<=in_data;
'''+old)
    (out/'motion_fifo.v').write_text(s)
    s=(ROOT/'pl_motion/rtl/motion_planner.v').read_text()
    old='output wire [1196:0] plan_data,output reg error';assert s.count(old)==1
    s=s.replace(old,'output wire [1196:0] plan_data,output reg error,\n // Private data-storage request; public validity still fences cancellation.\n output wire plan_pending')
    old='assign plan_valid=state==HOLD && !cancel;';assert s.count(old)==1
    s=s.replace(old,'assign plan_pending=state==HOLD;\n'+old)
    (out/'motion_planner.v').write_text(s)
    s=(ROOT/'pl_motion/rtl/continuous_motion.v').read_text()
    s=s.replace('wire planner_ready,planner_busy,planner_valid,planner_error,executor_error;',
                'wire planner_ready,planner_busy,planner_valid,planner_pending,planner_error,executor_error;')
    old='.plan_ready(prepared_push_ready),.plan_data(planner_data),.error(planner_error));';assert s.count(old)==1
    s=s.replace(old,'.plan_ready(prepared_push_ready),.plan_data(planner_data),.error(planner_error),.plan_pending(planner_pending));')
    old='motion_fifo #(.WIDTH(1197),.DEPTH(PLAN_DEPTH)) plan_fifo(';assert s.count(old)==1
    s=s.replace(old,'motion_fifo #(.WIDTH(1197),.DEPTH(PLAN_DEPTH),.SPECULATIVE_STORAGE(1)) plan_fifo(')
    old='.flush(flush_all),.in_valid(planner_valid),.in_ready(prepared_push_ready)';assert s.count(old)==1
    s=s.replace(old,'.flush(flush_all),.in_valid(planner_pending),.in_ready(prepared_push_ready)')
    (out/'continuous_motion.v').write_text(s)
    print('PASS isolated prepared storage candidate; original control/flush/count kept')

if __name__=='__main__':main()
