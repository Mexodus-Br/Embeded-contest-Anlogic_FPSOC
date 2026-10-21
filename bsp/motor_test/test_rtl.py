from pathlib import Path
import subprocess
R=Path(__file__).resolve().parents[2];D=R/'bsp/motor_test';W=R/'bsp/work/motor3125_soc_prj';E=W/'simulation'
E.mkdir(exist_ok=True)
sources=[W/'gp'/n for n in ['motion_fifo.v','motion_planner.v','motion_executor.v','continuous_motion.v']]
for name,args in [('compile',['iverilog','-g2012','-s','tb_motor','-o','test.vvp',*map(str,sources),str(D/'tb_motor.v')]),('run',['vvp','test.vvp'])]:
    log=E/(name+'.log')
    if log.exists():
        from datetime import datetime
        (E/(name+'_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.log')).write_bytes(log.read_bytes())
    p=subprocess.run(args,cwd=E,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
    log.write_text('EXIT_CODE='+str(p.returncode)+'\n'+p.stdout)
    print(p.stdout)
    assert p.returncode==0,name
assert 'PASS MOTOR3125' in p.stdout
