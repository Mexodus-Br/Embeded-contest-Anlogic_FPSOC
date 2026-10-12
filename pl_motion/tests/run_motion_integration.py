"""Questa self-checks, logs, source identity. No protected-IP replacement."""
import json,hashlib,shutil,subprocess,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BUILD=ROOT/'pl_motion/build/motion_integration'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,name,timeout=240):
    p=subprocess.run([str(x) for x in args],cwd=BUILD,capture_output=True,text=True,timeout=timeout)
    log=p.stdout+p.stderr;(BUILD/(name+'.log')).write_text(log,encoding='utf-8')
    if p.returncode or re.search(r'\*\* (Error|Fatal)',log):raise RuntimeError(name+' failed\n'+log[-4000:])
    return log
def main():
    BUILD.mkdir(parents=True,exist_ok=True)
    vlog=shutil.which('vlog');vsim=shutil.which('vsim')
    if not vlog or not vsim:raise RuntimeError('Questa required')
    run([Path(vlog).parent/'vlib.exe','work'],'library')
    rtl=[ROOT/'pl_motion/rtl'/n for n in ['motion_fifo.v','motion_planner.v','motion_executor.v','continuous_motion.v','motion_stream_rx.v','motion_service.v']]
    tb=ROOT/'pl_motion/tests/tb_motion_service.v';rxtb=ROOT/'pl_motion/tests/tb_motion_stream_rx.v'
    run([vlog,'-work','work','+incdir+'+str(ROOT/'pl_interface'),*rtl,tb,rxtb],'compile')
    rxlog=run([vsim,'-batch','work.tb_motion_stream_rx','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],'receiver')
    rxmarker=next((x for x in rxlog.splitlines() if 'PASS motion_stream_rx' in x),None)
    if not rxmarker:raise RuntimeError('receiver self-check incomplete')
    log=run([vsim,'-batch','work.tb_motion_service','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],'service')
    marker=next((x for x in log.splitlines() if 'PASS motion_service' in x),None)
    if not marker:raise RuntimeError('self-check completion missing')
    result={'status':'PASS','simulator':vsim,'result':marker,'receiver':rxmarker,'sources':{str(p.relative_to(ROOT)):digest(p) for p in rtl+[tb,rxtb,ROOT/'pl_interface/schema.json']},'logs':{p.name:digest(p) for p in BUILD.glob('*.log')}}
    (ROOT/'pl_motion/MOTION_SIM_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(marker)
if __name__=='__main__':main()
