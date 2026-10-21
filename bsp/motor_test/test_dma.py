"""Real protected MM2S/GP test: frozen scope bench, 10ms duration, new pulse profile."""
from pathlib import Path
import subprocess,json
R=Path(__file__).resolve().parents[2];W=R/'bsp/work/motor3125_soc_prj'
import sys
tag=sys.argv[1] if len(sys.argv)>1 else 'real_dma'
assert tag.replace('_','').isalnum()
E=W/tag;E.mkdir(exist_ok=False)
def frozen(n):return subprocess.check_output(['git','show','df17b4e:'+n],cwd=R).decode()
scenario=frozen('pl_motion/tests/scope_dma_scenarios.vh')
scenario=scenario.replace('50000000','1000000').replace('1002+(motion_slot_id*49998998)/124','3127+(motion_slot_id*996873)/124')
scenario=scenario.replace('>=500,','>=3125,').replace('==500,','==3125,').replace('5us','31.25us').replace('500000 ticks','10000 ticks')
scenario=scenario.replace('repeat(600)','repeat(4000)')
(E/'scope_dma_scenarios.vh').write_text(scenario)
script=(R/'pl_motion/tests/run_scope_dma.py').read_text()
script=script.replace('from prepare_ip import prepare,digest','')
script=script.replace("common.BUILD=ROOT/'pl_motion/build/scope_dma';b=common.BUILD;b.mkdir(parents=True,exist_ok=True);ip=prepare()",
    "common.BUILD=ROOT/'bsp/work/motor3125_soc_prj/real_dma';b=common.BUILD;b.mkdir(parents=True,exist_ok=True);ip=json.loads((ROOT/'pl_dma/build/ip/manifest.json').read_text())")
script=script.replace("params=','.join('.'+n+'(`SCOPE_TIMING)' for n in ['STEP_HIGH_CYCLES','STEP_LOW_CYCLES','DIR_SETUP_CYCLES','DIR_HOLD_CYCLES','EN_SETUP_CYCLES','EN_DISABLE_CYCLES'])",
    "params=','.join('.'+n+\"({64'd0,{3{64'd%d}}})\"%(3125 if n in ['STEP_HIGH_CYCLES','STEP_LOW_CYCLES'] else 500) for n in ['STEP_HIGH_CYCLES','STEP_LOW_CYCLES','DIR_SETUP_CYCLES','DIR_HOLD_CYCLES','EN_SETUP_CYCLES','EN_DISABLE_CYCLES'])")
script=script.replace("params+=',.MAX_STEP_HZ(`SCOPE_RATE),.EN_ACTIVE_LEVEL(`SCOPE_EN_ACTIVE)'", "params+=\",.MAX_STEP_HZ({64'd0,{3{64'd16000}}}),.EN_ACTIVE_LEVEL(4'd15)\"")
script=script.replace("'`include \"params.vh\"\\n'+",'')
script=script.replace("'110000000'","'3000000'")
script=script.replace("for p in (ROOT/'pl_motion/scope_test/generated').glob('*.hex'):shutil.copyfile(p,b/p.name)",'''for p in (ROOT/'pl_motion/scope_test/generated').glob('*.hex'):
  import struct,zlib
  data=bytearray.fromhex(p.read_text());struct.pack_into('<Q',data,24,10000);struct.pack_into('<I',data,68,zlib.crc32(data[:68]));(b/p.name).write_text(data.hex(' '))''')
names=subprocess.check_output(['git','ls-tree','-r','--name-only','df17b4e','pl_dma/rtl','pl_motion/rtl'],cwd=R).decode().splitlines()
replacement="rtl=[ROOT/'bsp/work/motor3125_soc_prj/gp'/n for n in "+repr([Path(n).name for n in names if n.endswith('.v')])+"]"
script=script.replace("rtl=sorted((ROOT/'pl_dma/rtl').glob('*.v'))+sorted((ROOT/'pl_motion/rtl').glob('*.v'))",replacement)
script=script[:script.index(" result={'status':'PASS'")]+" print(marker)\nif __name__=='__main__':main()\n"
# Keep ROOT anchored to this repository despite storing the adapted runner in work.
script=script.replace('ROOT=Path(__file__).resolve().parents[2]', 'ROOT=Path('+repr(str(R))+')')
script=script.replace("common.BUILD=ROOT/'bsp/work/motor3125_soc_prj/real_dma'", "common.BUILD=ROOT/"+repr('bsp/work/motor3125_soc_prj/'+tag))
(E/'run.py').write_text(script)
subprocess.run(['python',str(E/'run.py')],cwd=R,check=True)
