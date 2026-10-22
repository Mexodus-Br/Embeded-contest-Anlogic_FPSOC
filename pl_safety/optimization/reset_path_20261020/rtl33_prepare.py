"""Alternative: same-edge logical invalidation with original show-ahead storage."""
import json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 out=E/'rtl33_candidate_r1';out.mkdir(exist_ok=False)
 for f in (E/'rtl32_candidate_r2').glob('*'):
  if f.is_file():shutil.copyfile(f,out/f.name)
 # This variant keeps the original asynchronous show-ahead read and physical
 # spare slot. RAM eligibility is left to the original consumer read register;
 # compare actual mapping against31 rather than assuming a block attribute wins.
 (out/'motion_fifo.v').write_bytes((E/'rtl30_candidate_r1/motion_fifo.v').read_bytes())
 s=(out/'continuous_motion.v').read_text()
 s=replace(s,'wire raw_ready,raw_valid,raw_pop;', 'wire raw_available,raw_ready,raw_valid,raw_pop;')
 s=replace(s,'.storage_out_ready(raw_storage_ready),.storage_valid());',
  '.storage_out_ready(raw_storage_ready),.storage_valid(raw_available));')
 s=replace(s,'.cancel(flush_all),.req_valid(raw_valid && session_valid && !flush_all),',
  '''.cancel(flush_all),.req_valid(raw_available && session_valid),''')
 # On a flush the original planner control owner still goes to IDLE. Only its
 # private data read may speculate. This removes flush from wide RAM read CE.
 (out/'continuous_motion.v').write_bytes(s.encode())
 (out/'async_storage_notes.json').write_text(json.dumps({'hashes_computed':False,'external_cycles_added':0,
  'logical_capacity':{'raw':64,'prepared':8},'physical_spare':{'raw':65,'prepared':9},
  'method':'same registered logical-invalidation marker and private producer/consumer cofactors; original show-ahead RAM read, private planner read may speculate on flush',
  'unchanged':'public ready/valid/count, accepted/stale/error statistics, direct cancel of planner control and executor',
  'why_compare':'31 clocked read may add forwarding FF/ERAM; select from measured top reports, not assumptions',
  'status':'isolated module validation pending'},indent=2)+'\n')
 print('Prepared isolated RTL33 alternative storage mapping; product remains29')
if __name__=='__main__':main()
