"""Seal only GPIO evidence; do not overwrite the earlier internal delivery."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'pl_motion/scope_test/evidence'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy_dir(source,target,names=None):
 target.mkdir(parents=True,exist_ok=True)
 for p in sorted(source.iterdir()):
  if p.is_file() and (names is None or p.name in names):shutil.copyfile(p,target/p.name)
def main():
 sim=ROOT/'pl_motion/build/scope_dma';sta=json.loads((ROOT/'pl_motion/scope_test/STA_RESULTS.json').read_text())
 assert sta['timing_pass'];s=Path(sta['build_directory']);OUT.mkdir(exist_ok=True)
 for n in ['scope_outputs.vcd','observed_edges.csv','simulation.log','compile.log','dut_bindings.vh','tb_scope_dma.v']:
  shutil.copyfile(sim/n,OUT/n)
 hw_names=['run.log','run.tcl','top.v','clock.adc','clock.sdc','ps-properties.tcl','gate.timing','place.timing','route.timing','route.check','route.area','route.qor','summary.json']
 copy_dir(s,OUT/'final_gpio_sta',hw_names)
 for tag in ['motion_soc_gpio_scope','motion_soc_gpio_scope_ioreg']:
  copy_dir(ROOT/'pl_dma/build'/tag,OUT/('failed_'+tag),hw_names+['run-failed-01.log'])
 for name in ['incomplete-01','incomplete-02','failed-assert-03']:copy_dir(sim/name,OUT/name)
 shutil.copyfile(sim/'compile-failed-01.log',OUT/'compile-failed-01.log')
 copy_dir(ROOT/'pl_motion/build/gpio_regressions',OUT/'regressions')
 copy_dir(ROOT/'pl_motion/build/scope_default',OUT/'default',names=['compile.log','simulation.log'])
 index={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='index.json'}
 (OUT/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
 print('GPIO evidence sealed',len(index),'files; old evidence untouched')
if __name__=='__main__':main()
