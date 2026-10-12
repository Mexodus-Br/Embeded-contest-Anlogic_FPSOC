"""Single-variable clock-alias diagnosis in a disposable, isolated copy.

This never changes the release project and never produces a deployable bitstream.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

BASE = Path(__file__).resolve().parents[1] / 'work/gp_soc_prj'
DEST = BASE.parent / 'gp_clock_diagnostic'
if DEST.exists():
    raise SystemExit('Refusing to overwrite previous clock diagnosis')
DEST.mkdir()
for name in ['system', 'gp']:
    shutil.copytree(BASE / name, DEST / name)
shutil.copy2(BASE / 'system.al', DEST / 'system.al')
for p in DEST.rglob('*'):
    if p.is_file() and p.suffix in {'.xml', '.al'}:
        t = p.read_text(encoding='utf-8')
        p.write_text(t.replace(BASE.as_posix(), DEST.as_posix()), encoding='utf-8')
raw = DEST / 'system/ip/system_ARM_Processor_System_0/RTL/ARM_Processor_System_f6ddd1d59490.v'
original = raw.read_bytes()
assert original.count(b".slave_gp0_axi_aclk(1'b0)") == 1
raw.write_bytes(original.replace(b".slave_gp0_axi_aclk(1'b0)",
                                 b'.slave_gp0_axi_aclk(master_gp0_axi_aclk)'))
script = f'''cd {DEST.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project system.al
elaborate -top system_wrapper
read_adc -file gp/gp.adc
read_sdc gp/gp.sdc
optimize_rtl
optimize_gate
report_timing_summary -file diagnostic.timing -path_num 1
write_verilog diagnostic.v -constnet
puts BSP_CLOCK_DIAGNOSTIC_COMPLETE
exit
'''
(DEST/'diagnostic.tcl').write_text(script, encoding='utf-8')
td = 'D:/Anlogic/TD_Release_2026.1_SP2.200.067/bin/td_commands_prompt.exe'
with (DEST/'diagnostic.log').open('w') as log:
    r = subprocess.run([td, (DEST/'diagnostic.tcl').as_posix()], cwd=DEST,
                       stdout=log, stderr=subprocess.STDOUT, timeout=300)
t = (DEST/'diagnostic.log').read_text(errors='replace')
result = {'returncode':r.returncode, 'complete':'BSP_CLOCK_DIAGNOSTIC_COMPLETE' in t,
          'gen_pl_gp0s_warning':'GEN_PL_GP0S' in t,
          'original_ps_sha256':hashlib.sha256(original).hexdigest(),
          'diagnostic_ps_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
          'deployable':False,
          'change':"Only slave_gp0_axi_aclk: 1'b0 -> master_gp0_axi_aclk"}
(DEST/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
