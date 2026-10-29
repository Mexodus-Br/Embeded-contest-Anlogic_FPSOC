"""Synthesize a module-tested isolated candidate in the complete real top.

Use the original complete project builder, replace explicitly named task RTL
copies only, then stop after gate reports/DB. No board or constraint changes.
"""
import argparse,importlib.util,json,re,shutil,subprocess,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--source-directory',required=True);a=p.parse_args()
 assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
 source=Path(a.source_directory).resolve();assert source.is_relative_to(HERE)
 files=list(source.glob('*.v'));assert {f.name for f in files}<={'motion_fifo.v','motion_planner.v','continuous_motion.v','motion_service.v','motion_stream_rx.v'} and files
 spec=importlib.util.spec_from_file_location('real_builder',ROOT/'pl_safety/build_interlock.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
 sys.argv=[str(ROOT/'pl_safety/build_interlock.py'),'--tag',a.tag,'--prepare-only'];builder.main()
 out=ROOT/'pl_safety/build'/a.tag
 for f in files:
  shutil.copyfile(f,out/'gp'/f.name);assert f.read_bytes()==(out/'gp'/f.name).read_bytes()
 metadata=json.loads((out/'inputs.json').read_text());metadata['isolated_overrides']=[f.relative_to(ROOT).as_posix() for f in files]
 (out/'inputs.json').write_text(json.dumps(metadata,indent=2)+'\n')
 script=(out/'run.tcl').read_text().split('export_db gate.db',1)[0]+'export_db gate.db\nputs ISOLATED_GATE_COMPLETE\nexit\n'
 (out/'run.tcl').write_text(script)
 result={'passed':False,'hashes_computed':False,'build':a.tag,'gate_only':True,'signoff_pass':False}
 try:
  with (out/'run.log').open('w') as log:proc=subprocess.run([shutil.which('td_commands_prompt'),(out/'run.tcl').as_posix()],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=2400)
  text=(out/'run.log').read_text(errors='replace')
  assert proc.returncode==0 and 'ISOLATED_GATE_COMPLETE' in text and not re.search(r'\bERROR:|TMR-250[79]',text)
  assert 'INTERLOCK_TD_THREADS 16' in text and 'Number of Thread = 16' in text
  timing=(out/'gate.timing').read_text();area=(out/'gate.area').read_text()
  result.update(passed=True,threads=16,setup_ns=float(re.search(r'SWNS:\s*([-\d.]+)ns',timing)[1]),
   lut6_equivalent=int(re.search(r'^#unit lut\*\s+(\d+)',area,re.M)[1]),slice_ff=int(re.search(r'^  #slice reg\s+(\d+)',area,re.M)[1]),
   eram=int(re.search(r'^#eram\s+(\d+)',area,re.M)[1]),dsp=int(re.search(r'^#dsp\s+(\d+)',area,re.M)[1]))
  print(result)
 except Exception:result['failure']=traceback.format_exc();raise
 finally:(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
