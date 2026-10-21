"""Isolate the board-tested GPIO baseline; never import dirty working RTL."""
from pathlib import Path
import json, subprocess, shutil
R=Path(__file__).resolve().parents[2]
D=R/'bsp/motor_test'; W=R/'bsp/work/motor3125_soc_prj'
BASE='df17b4ebd6e358d6626a227b5c0c152c1f6cb9ed'
S=R/'bsp/work/scope_soc_prj'
def blob(commit,name):
    return subprocess.check_output(['git','show',commit+':'+name],cwd=R).decode('utf-8').replace('\r\n','\n')
cfg={'clock_hz':100000000,'step_high_cycles':3125,'step_low_cycles':3125,
     'dir_setup_cycles':500,'dir_hold_cycles':500,'en_setup_cycles':500,
     'en_disable_cycles':500,'max_step_hz':16000,'axis_mask':7,'m4_enabled':False,
     'baseline_gpio_commit':BASE,'purpose':'explicit motor bench pulse-width comparison; not calibrated mechanics'}
(D/'CONFIG.json').write_text(json.dumps(cfg,indent=2)+'\n')
if W.exists(): raise SystemExit('Candidate already exists: preserve previous attempt')
W.mkdir()
for n in ['system','uisrc','gp']: shutil.copytree(S/n,W/n)
(W/'system.al').write_text((S/'system.al').read_text().replace(S.as_posix(),W.as_posix()))
# Compare the actual compiled source, not logs or historical evidence hashes.
header=blob(BASE,'pl_interface/generated/interface_defs.vh')
names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'pl_dma/rtl','pl_motion/rtl'],cwd=R).decode().splitlines()
for n in names:
    if not n.endswith('.v'):continue
    expected=blob(BASE,n).replace('`include "generated/interface_defs.vh"',header)
    p=W/'gp'/Path(n).name
    assert p.read_text().replace('\r\n','\n')==expected,n
wrapper=W/'system/hdl/system_wrapper.v'
t=wrapper.read_text()
for name in ['STEP_HIGH_CYCLES','STEP_LOW_CYCLES']:
    old='.'+name+"({64'd0,{3{64'd500}}})"
    assert t.count(old)==1
    t=t.replace(old,'.'+name+"({64'd0,{3{64'd3125}}})")
assert t.count(".MAX_STEP_HZ({64'd0,{3{64'd100000}}})")==1
t=t.replace(".MAX_STEP_HZ({64'd0,{3{64'd100000}}})",".MAX_STEP_HZ({64'd0,{3{64'd16000}}})")
wrapper.write_text(t)
app=blob('db5f75c','bsp/scope/delta_scope.cpp')
app=app.replace('// No-motor coordinate test.','// Explicit motor bench pulse-width comparison.')
app=app.replace('--no-motor-test','--motor-bench-test').replace('root/no-motor','root/motor-bench')
app=app.replace('explicit no-motor scope session','explicit motor-bench session')
app=app.replace('// Frozen planner: guard=Q+S+2=1002; tail=H+max(L,hold)=1000; ceil(100MHz/100kHz)=1000.',
                '// Profile: guard=max(Q+S,E,L)+2=3127; H+L=6250; min period=6250.')
assert app.count('(cycles-1002)/master>=1000')==1
app=app.replace('master==0||(cycles>1002&&(cycles-1002)/master>=1000)','bench_feasible(cycles,master)').replace('5us/100kHz scope limits','31.25us high/low and 16kHz bench limits')
app=app.replace('static int device=', 'static bool bench_feasible(uint64_t cycles,uint64_t master){return master==0||(cycles>3127&&(cycles-3127)/master>=6250);}\nstatic int device=')
app=app.replace('SCOPE_SERVER_READY no automatic','MOTOR3125_PROFILE H=3125 L=3125 MAX_HZ=16000; SCOPE_SERVER_READY no automatic')
(D/'delta_scope.cpp').write_text(app)
print('PASS frozen-source comparison; independent candidate',W)
