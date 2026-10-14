"""Run existing real dual-controller scenarios with the actual GPIO parameters.

The installed protected DMA/converters and every production RTL are unchanged.
Only the test's motion vectors use mask7/M4 target0 and the 500-cycle/100kHz
scope settings that are already frozen in the board wrapper.
"""
import argparse,json
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'pl_rs485/optimization'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args()
 source=(R/'pl_dma/tests/run_telemetry_system.py').read_text(encoding='utf-8')
 old="params=','.join('.'+n+'({4{64\\'d'+str(x)+'}})' for n,x in [('STEP_HIGH_CYCLES',3),('STEP_LOW_CYCLES',2),('DIR_SETUP_CYCLES',4),('DIR_HOLD_CYCLES',7),('EN_SETUP_CYCLES',5),('EN_DISABLE_CYCLES',3),('MAX_STEP_HZ',10000000)])"
 assert old in source
 new="params=','.join('.'+n+\"({64'd0,{3{64'd\"+str(x)+\"}}})\" for n,x in [('STEP_HIGH_CYCLES',500),('STEP_LOW_CYCLES',500),('DIR_SETUP_CYCLES',500),('DIR_HOLD_CYCLES',500),('EN_SETUP_CYCLES',500),('EN_DISABLE_CYCLES',500),('MAX_STEP_HZ',100000)])"
 source=source.replace(old,new)
 old="helpers=(R/'pl_dma/tb/motion_dma_scenarios.vh').read_text().split('initial begin',1)[0]"
 assert old in source
 source=source.replace(old,old+"\n helpers=helpers.replace('r[176+:16]=15','r[176+:16]=7').replace('r[448+:64]=-target','r[448+:64]=0')")
 old="(R/'pl_dma/tb/telemetry_system_scenarios.vh').read_text()"
 assert old in source
 source=source.replace(old,old+".replace('motion_command(`PLI_CMD_REBASE,15)','motion_command(`PLI_CMD_REBASE,7)').replace('motion_command(`PLI_CMD_ENABLE,15)','motion_command(`PLI_CMD_ENABLE,7)')")
 # Keep the existing runner's root calculation, imports, assertions and IP paths.
 source=source.replace("R=Path(__file__).resolve().parents[2]","R=Path("+repr(str(R))+")")
 E=O/('actual_system_'+a.tag);E.mkdir(exist_ok=False)
 (E/'runner.py').write_text(source,encoding='utf-8')
 import subprocess,sys
 p=subprocess.run([sys.executable,str(E/'runner.py'),'--tag',a.tag],cwd=R,capture_output=True,text=True,timeout=900)
 (E/'run.log').write_text('EXIT '+str(p.returncode)+'\n'+p.stdout+p.stderr,encoding='utf-8');print(p.stdout+p.stderr)
 assert p.returncode==0,'Actual GPIO parameter system test failed'
 (E/'result.json').write_text(json.dumps({'passed':True,'actual_scope_parameters':{'guards_cycles':500,'max_step_hz':100000,'axis_mask':7,'M4_disabled':True},'real_ip_report':'pl_dma/reports/telemetry_system_'+a.tag+'/result.json'},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
