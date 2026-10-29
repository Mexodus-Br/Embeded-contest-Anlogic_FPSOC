"""Run interlock/parser and ownership regression on the isolated frozen inputs."""
from pathlib import Path
import subprocess,sys
H=Path(__file__).resolve().parent;R=H.parents[1];G=H/'hardware/gp'
sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator
out=H/'artifacts/interlock';out.mkdir(exist_ok=False);sim=Simulator(out)
for name,files in [('tb_interlock',['safety_interlock','rs485_light_parse']),('tb_interlock_owner_projection',['safety_controller'])]:
    text=subprocess.check_output(['git','show','a21751d:pl_safety/tests/'+name+'.v'],cwd=R).decode()
    if name=='tb_interlock':
        old="32'd0,32'd0,6'd0,1'b0,1'b0,1'b0);";assert text.count(old)==1
        text=text.replace(old,"32'd0,32'd0,6'd0,1'b0,1'b0,1'b0,2'd0,,1'b1);")
    p=out/(name+'.v');p.write_text(text);exe=out/(name+'.vvp')
    (out/(name+'-compile.log')).write_text(sim.compile([G/(f+'.v') for f in files]+[p],name,exe,includes=[G,R/'pl_interface']))
    log=sim.simulate(exe,timeout=90);(out/(name+'.log')).write_text(log);assert 'PASS' in log;print(log)
