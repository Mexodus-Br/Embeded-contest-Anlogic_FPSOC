"""Drop reset from immutable cache metadata, guarded by since-reset written bits."""
import json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 out=E/'rtl27_candidate_r1';out.mkdir(exist_ok=False)
 for f in (E/'rtl26_candidate_r1').glob('*'):
  if f.is_file():shutil.copyfile(f,out/f.name)
 (out/'before').mkdir()
 p=R/'pl_rs485/rtl/rs485_latest_cache.v';shutil.copyfile(p,out/'before'/p.name);s=p.read_text()
 s=replace(s,'good_gen[i]<=0;good_rev[i]<=0;last_gen[i]<=0;last_rev[i]<=0;','')
 s=replace(s,'last_gen[task_index]<=event_generation;last_rev[task_index]<=event_revision;','')
 s=replace(s,'good_gen[task_index]<=event_generation;good_rev[task_index]<=event_revision;','')
 s=replace(s,'{flags,updates[i],last_rev[i],last_gen[i],good_rev[i],good_gen[i],last_written[i],good_written[i],last_pointer[i],good_pointer[i]}',
  "{flags,updates[i],(last_written[i] ? last_rev[i]:32'd0),(last_written[i] ? last_gen[i]:32'd0),(good_written[i] ? good_rev[i]:32'd0),(good_written[i] ? good_gen[i]:32'd0),last_written[i],good_written[i],last_pointer[i],good_pointer[i]}")
 extra='''
// Immutable identity payload has the same lifetime as its corresponding RAM
// record. Since-reset written bits remain async-reset and mask every frozen
// generation/revision before the first write. Generation changes deliberately
// preserve old raw/identity, exactly as before; seen validity is independent.
always @(posedge clk)if(write_record)begin
 last_gen[task_index]<=event_generation;last_rev[task_index]<=event_revision;
 if(valid)begin good_gen[task_index]<=event_generation;good_rev[task_index]<=event_revision;end
end
'''
 (out/p.name).write_text(s.replace('endmodule',extra+'endmodule'))
 (out/'cache_notes.json').write_text(json.dumps({'hashes_computed':False,'removed_async_source_bits':1920,
  'unchanged':'same-edge atomic metadata/raw snapshot; immutable generation/revision; failed events never overwrite good record',
  'before_first_write':'written=0 forces identity fields to original zero; flags and pointers retain async reset',
  'status':'module validation pending'},indent=2)+'\n')
 print('Prepared RTL27 metadata reset removal')
if __name__=='__main__':main()
