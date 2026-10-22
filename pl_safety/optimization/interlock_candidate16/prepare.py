"""Isolate complete current-context projections using exact source next values."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OUT=HERE/'sources_r1'
def change(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b)
def main():
 OUT.mkdir(exist_ok=False)
 paths=['pl_rs485/rtl/'+x for x in ['rs485_gp_regs.v','rs485_multirate.v','rs485_gp_bridge.v']]
 paths+=['pl_safety/rtl/'+x for x in ['safety_interlock.v','safety_interlock_regs.v','safety_motion_service.v']]
 paths+=['pl_safety/generate_top.py']
 f={p:(ROOT/p).read_text() for p in paths}
 for p in paths:
  if p.endswith('.v'):assert (ROOT/p).read_bytes()==(ROOT/'pl_safety/build/interlock_route15/gp'/Path(p).name).read_bytes(),p
 p=paths[0];s=f[p]
 s=change(s,'output wire reset_commit);','output wire reset_commit,output wire next_reset);')
 s=change(s,' assign next_generation='," assign next_reset=rst_n && (reset_commit || reset_count>1);\n assign next_generation=")
 f[p]=s
 p=paths[1];s=f[p]
 s=change(s,'output wire [5:0] observe_protection);','output wire [5:0] observe_protection,output wire next_config_change);')
 s=change(s,' wire [31:0] revision_increment='," assign next_config_change=rst_n && state==CFG_WAIT && !engine_active && cfg_revision!=32'hffffffff;\n wire [31:0] revision_increment=")
 f[p]=s
 p=paths[2];s=f[p]
 s=change(s,'output wire [5:0] completed_protection);','output wire [5:0] completed_protection,output wire next_reset,next_config_change);')
 s=change(s,'wire reset_commit;','wire next_config_change_raw;wire reset_commit;')
 s=change(s,'assign next_revision=',"assign next_config_change=collector_rst_n && !reset_commit && next_config_change_raw;\nassign next_revision=")
 s=change(s,'.next_revision(next_revision_raw),','.next_revision(next_revision_raw),.next_config_change(next_config_change_raw),')
 s=change(s,'.reset_commit(reset_commit),','.reset_commit(reset_commit),.next_reset(next_reset),')
 f[p]=s
 p=paths[3];s=f[p]
 s=change(s,'parameter FEEDBACK_PREDECODE=0','parameter FEEDBACK_PREDECODE=0,parameter LOOKAHEAD_CONTEXT=0')
 s=change(s,'input wire [5:0] feedback_predecoded\n','input wire [5:0] feedback_predecoded,\n input wire next_collector_reset,next_config_change,next_config_apply\n')
 s=change(s,'reg epoch_match_q;','reg epoch_match_q;reg active_context_q,off_context_q;')
 s=change(s,' wire [31:0] next_round_revision=restart ? collector_revision:round_revision;', ''' wire [31:0] next_round_revision=restart ? collector_revision:round_revision;
 wire next_epoch_match=next_generation==next_round_generation && next_revision==next_round_revision;''')
 s=change(s,'wire monitoring=poll_run && !poll_stop_commit && previous_run && !restart && !collector_reset;', '''wire monitoring=LOOKAHEAD_CONTEXT ? (poll_run && !poll_stop_commit && active_context_q):
   (poll_run && !poll_stop_commit && previous_run && !restart && !collector_reset);''')
 s=change(s,'(LOOKAHEAD_EPOCH ? (epoch_match_q && feedback_generation==collector_generation &&',
  "(LOOKAHEAD_EPOCH ? ((LOOKAHEAD_CONTEXT ? 1'b1:epoch_match_q) && feedback_generation==collector_generation &&")
 s=change(s,'!request_age[63] && !event_age[63] && round_valid && !restart && !collector_reset;', '''!request_age[63] && !event_age[63] && round_valid &&
   (LOOKAHEAD_CONTEXT ? (poll_run ? active_context_q:off_context_q):(!restart && !collector_reset));''')
 s=change(s,'   epoch_match_q<=1;', '   active_context_q<=0;off_context_q<=1;epoch_match_q<=1;')
 s=change(s,'   epoch_match_q<=next_generation==next_round_generation && next_revision==next_round_revision;', '''   epoch_match_q<=next_epoch_match;
   // Project complete NEXT source/round values, not delayed current flags.
   // At the current edge these equal the original expanded qualifications.
   off_context_q<=next_epoch_match && !next_collector_reset;
   active_context_q<=poll_run && next_epoch_match && !next_collector_reset &&
     !next_config_change && !next_config_apply;''')
 f[p]=s
 p=paths[4];s=f[p]
 s=change(s,'output reg [63:0] heartbeat_owner,heartbeat_sequence\n', 'output reg [63:0] heartbeat_owner,heartbeat_sequence,\n output wire next_config_apply\n')
 s=change(s,' assign owner_open=', ' assign next_config_apply=rst_n && config_commit;\n assign owner_open=')
 f[p]=s
 p=paths[5];s=f[p]
 s=change(s,'collector_next_generation,collector_next_revision,','collector_next_generation,collector_next_revision,\n input wire collector_next_reset,collector_next_config_change,')
 s=change(s,'wire owner_active,hb_qualified,fb_qualified,raw_permit,cfg_pending;', 'wire owner_active,hb_qualified,fb_qualified,raw_permit,cfg_pending,next_cfg_apply;')
 s=change(s,'.FEEDBACK_PREDECODE(1)) monitor(', '.FEEDBACK_PREDECODE(1),.LOOKAHEAD_CONTEXT(1)) monitor(.next_collector_reset(collector_next_reset),.next_config_change(collector_next_config_change),.next_config_apply(next_cfg_apply),')
 s=change(s,' safety_interlock_regs extension(', ' safety_interlock_regs extension(.next_config_apply(next_cfg_apply),')
 f[p]=s
 p=paths[6];s=f[p]
 s=change(s,'collector_next_generation,collector_next_revision,','collector_next_generation,collector_next_revision,\ninput wire collector_next_reset,collector_next_config_change,')
 s=change(s,"'.collector_generation(collector_generation)","'.collector_next_reset(collector_next_reset),.collector_next_config_change(collector_next_config_change),.collector_generation(collector_generation)")
 s=change(s,'wire [31:0] collector_next_generation,collector_next_revision;', 'wire collector_next_reset,collector_next_config_change;\\nwire [31:0] collector_next_generation,collector_next_revision;')
 s=change(s,"'.collector_generation(generation)","'.collector_next_reset(collector_next_reset),.collector_next_config_change(collector_next_config_change),.collector_generation(generation)")
 s=change(s,'.next_generation(collector_next_generation),.next_revision(collector_next_revision),', '.next_reset(collector_next_reset),.next_config_change(collector_next_config_change),.next_generation(collector_next_generation),.next_revision(collector_next_revision),')
 f[p]=s
 ns={'__name__':'candidate16','__file__':str(ROOT/p)};exec(compile(s,ns['__file__'],'exec'),ns)
 for name,data in ns['render']().items():
  if data.encode()!=(ROOT/'pl_safety/generated'/name).read_bytes():
   assert name in ['interlock_motion_dma_lite_top.v','interlock_rs485_shared_lite_top.v']
   f['pl_safety/generated/'+name]=data
 for p,data in f.items():
  dest=OUT/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data.encode())
 (OUT/'scope.json').write_text(json.dumps({'production_modified':False,'hashes_computed':False,'paths':list(f)},indent=2)+'\n')
 print('PASS isolated context projection prepared',len(f))
if __name__=='__main__':main()
