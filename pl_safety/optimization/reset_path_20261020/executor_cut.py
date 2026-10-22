"""Isolate private executor data from global stop/reset; observable owners stay."""
import argparse, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);args=ap.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+',args.tag)
    out=HERE/args.tag;out.mkdir(exist_ok=False)
    s=(ROOT/'pl_motion/rtl/motion_executor.v').read_text()
    start=s.index("      sum_time={1'b0,time_remainder}")
    end=s.index('      for(i=0;i<4;i=i+1)if(moving[i])begin',start)
    s=s[:start]+s[end:]
    s=s.replace("       sum_axis={1'b0,accumulator[i]}+{1'b0,count[i]};",'')
    names='moving|positive|cycles|master|quotient|remainder|elapsed|next_slot|slot_index|time_remainder'
    pattern=r'\b(?:(?:'+names+r')|(?:count|accumulator)\[[^]]+\])\s*<=.*?;'
    # 12 reset sites, three RUN sites and 12 commit sites; timing arithmetic
    # assignments were removed as a complete block above.
    s,n=re.subn(pattern,'',s);assert n==27,n
    s=s.replace('reg [64:0] sum_time,sum_axis;','')
    assert 'sum_time' not in s and 'sum_axis' not in s
    extra='''
// Private plan data are overwritten before every RUN grant. Writes while
// IDLE/at the old boundary may be speculative; only the original control
// process can accept a plan, emit STEP, update position or publish events.
// On cancellation/failure, its state invalidates the entire data set on the
// original edge. No global stop/reset enable is needed on these data flops.
reg [64:0] data_time,data_axis;
integer data_lane;
always @(posedge clk)begin
 if(state==RUN)begin
  elapsed<=elapsed+64'd1;
  if(slot_due)begin
   slot_index<=slot_index+64'd1;
   data_time={1'b0,time_remainder}+{1'b0,remainder};
   if(data_time>={1'b0,master})begin
    time_remainder<=data_time-{1'b0,master};next_slot<=next_slot+quotient+64'd1;
   end else begin time_remainder<=data_time[63:0];next_slot<=next_slot+quotient;end
   for(data_lane=0;data_lane<4;data_lane=data_lane+1)if(moving[data_lane])begin
    data_axis={1'b0,accumulator[data_lane]}+{1'b0,count[data_lane]};
    accumulator[data_lane]<=emit[data_lane] ? data_axis-{1'b0,master}:data_axis[63:0];
   end
  end
 end
 // The control grant can occur only in IDLE or at this exact boundary.
 // Rejected/unowned input data may be copied, but never create RUN/STEP.
 if(state==IDLE || boundary)begin
  cycles<=plan_cycles;master<=plan_master;quotient<=plan_quotient;remainder<=plan_remainder;
  moving<=plan_moving;positive<=plan_positive;elapsed<=1;next_slot<=plan_guard;slot_index<=0;time_remainder<=0;
  for(data_lane=0;data_lane<4;data_lane=data_lane+1)begin
   count[data_lane]<=plan_counts[data_lane*64+:64];
   accumulator[data_lane]<=plan_master-plan_counts[data_lane*64+:64];
  end
 end
end
'''
    s=s.replace('endmodule',extra+'\nendmodule')
    (out/'motion_executor.v').write_text(s)
    print('PASS isolated executor data candidate, removed assignment sites',n)
