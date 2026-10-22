"""Real-IP integration preparation using explicit, isolated RTL substitutions.

Production candidate13 stays unchanged. Every substituted file and its intended
logical path are recorded. This is functional evidence only, not TD signoff.
"""
import importlib.util,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OVERLAY=HERE/'integrated_sources_r1'

def change(s,old,new):
 assert s.count(old)==1,old
 return s.replace(old,new)

def prepare():
 OVERLAY.mkdir(exist_ok=False)
 files={}
 for name in ['rs485_gp_regs.v','rs485_multirate.v','rs485_gp_bridge.v']:
  files['pl_rs485/rtl/'+name]=(HERE/'counter_probe_r1'/name).read_bytes()
 core=(HERE/'probe_r1/monitor.v').read_text()
 files['pl_safety/rtl/safety_interlock.v']=change(core,'module safety_interlock_lookahead #','module safety_interlock #').encode()
 service=(ROOT/'pl_safety/rtl/safety_motion_service.v').read_text()
 service=change(service,'input wire [31:0] collector_generation,collector_revision,',
  'input wire [31:0] collector_generation,collector_revision,collector_next_generation,collector_next_revision,')
 service=change(service,' safety_interlock monitor(',
  ' safety_interlock #(.LOOKAHEAD_EPOCH(1)) monitor(.next_generation(collector_next_generation),.next_revision(collector_next_revision),')
 files['pl_safety/rtl/safety_motion_service.v']=service.encode()
 generator=(ROOT/'pl_safety/generate_top.py').read_text()
 generator=change(generator,'input wire [31:0] collector_generation,collector_revision,',
  'input wire [31:0] collector_generation,collector_revision,collector_next_generation,collector_next_revision,')
 generator=change(generator,'.collector_generation(collector_generation),.collector_revision(collector_revision),',
  '.collector_generation(collector_generation),.collector_revision(collector_revision),.collector_next_generation(collector_next_generation),.collector_next_revision(collector_next_revision),')
 generator=change(generator,"events+'\\nwire [230:0] m_awaddr;')",
  "events+'\\nwire [31:0] collector_next_generation,collector_next_revision;\\nwire [230:0] m_awaddr;')")
 generator=change(generator,'.collector_generation(generation),.collector_revision(revision),',
  '.collector_generation(generation),.collector_revision(revision),.collector_next_generation(collector_next_generation),.collector_next_revision(collector_next_revision),')
 generator=change(generator,'.interlock_run(collector_run),.interlock_stop_commit(collector_stop_commit),.interlock_reset(collector_reset),',
  '.interlock_run(collector_run),.interlock_stop_commit(collector_stop_commit),.interlock_reset(collector_reset),.next_generation(collector_next_generation),.next_revision(collector_next_revision),')
 files['pl_safety/generate_top.py']=generator.encode()
 namespace={'__name__':'prototype_top_generator','__file__':str(ROOT/'pl_safety/generate_top.py')}
 exec(compile(generator,namespace['__file__'],'exec'),namespace)
 for name,text in namespace['render']().items():
  current=(ROOT/'pl_safety/generated'/name).read_bytes()
  if current!=text.encode():
   assert name in ['interlock_motion_dma_lite_top.v','interlock_rs485_shared_lite_top.v'],name
   files['pl_safety/generated/'+name]=text.encode()
 for logical,data in files.items():
  target=OVERLAY/logical;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 (OVERLAY/'scope.json').write_text(json.dumps({'experimental_only':True,'production_modified':False,
   'logical_source_paths':list(files),'hashes_computed':False},indent=2)+'\n')
 return {str((ROOT/k).resolve()):OVERLAY/k for k in files if k.endswith('.v')}

def main():
 overrides=prepare()
 path=ROOT/'pl_safety/tests/interlock_real_system.py'
 spec=importlib.util.spec_from_file_location('real_probe',path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 old_stage,old_adapt=module.stage_sources,module.adapt
 def stage(sources,out):
  staged=old_stage(sources,out)
  inventory=json.loads((out/'compiled_sources.json').read_text())
  for entry in inventory['direct_byte_verified_source_copies']:
   logical=Path(entry['source']);substitute=overrides.get(str(logical.resolve()))
   if substitute:
    target=Path(entry['compiled_copy']);shutil.copyfile(substitute,target)
    assert substitute.read_bytes()==target.read_bytes()
    entry['logical_source']=str(logical)
    entry['source']=str(substitute)
  inventory['experimental_substitution']=True
  inventory['production_modified']=False
  (out/'compiled_sources.json').write_text(json.dumps(inventory,indent=2)+'\n')
  return staged
 def adapt(tb,scenario,accepted_overlap):
  tb=old_adapt(tb,scenario,accepted_overlap)
  tb=change(tb,'reg [3:0] preceding_step;', 'reg [31:0] predicted_generation,predicted_revision;\nreg [3:0] preceding_step;')
  tb=change(tb,' preceding_step=motion_step;detecting=`SAFETY.il_detect;', ''' predicted_generation=`SAFETY.collector_next_generation;
 predicted_revision=`SAFETY.collector_next_revision;
 preceding_step=motion_step;detecting=`SAFETY.il_detect;''')
  tb=change(tb,' #1;\n if(`SAFETY.owner', ''' #1;
 if(`SAFETY.collector_generation!==predicted_generation || `SAFETY.collector_revision!==predicted_revision)
  $fatal(1,"real complete source next-value prediction differs from actual registers");
 if(`SAFETY.interlocks.monitor.epoch_match_q!==
    ((`SAFETY.collector_generation==`SAFETY.interlocks.monitor.round_generation) &&
     (`SAFETY.collector_revision==`SAFETY.interlocks.monitor.round_revision)))
  $fatal(1,"real cached full-u32 comparison differs on current edge");
 if(`SAFETY.owner''')
  return tb
 module.stage_sources, module.adapt=stage,adapt
 module.main()

if __name__=='__main__':main()
