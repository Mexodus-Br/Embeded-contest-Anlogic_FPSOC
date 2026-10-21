import subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];E=R/'bsp/evidence/telemetry-router-20261014a';E.mkdir(exist_ok=False)
for name,command in [('compile',['iverilog','-g2005','-I',str(R/'pl_interface'),'-s','tb_router','-o',str(E/'test.vvp'),str(R/'bsp/telemetry/tb_router.v'),str(R/'pl_dma/rtl/axi_lite_six_way.v')]),('run',['vvp',str(E/'test.vvp')])]:
 with (E/(name+'.log')).open('w',encoding='utf-8') as f:ret=subprocess.run(command,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 if ret.returncode:raise SystemExit('router '+name+' failed; raw log retained')
print((E/'run.log').read_text(encoding='utf-8'))
