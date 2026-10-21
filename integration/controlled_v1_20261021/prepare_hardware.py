"""Complete functional candidate with fixed pins; production HOME prohibited.

This changes four pin constraints, requiring new full P&R. PROFILE2 is retained
ONLY as the original full resource/functional candidate, never approved for motion.
It preserves the frozen rtl_path38 snapshot and all original effective 10ns SDC.
"""
from pathlib import Path
import json
import re
import shutil

H=Path(__file__).resolve().parent
P=H/'hardware'
assert not P.exists(),'Refuse existing hardware candidate'
shutil.copytree(H/'frozen/pl',P)
wrapper=P/'system/hdl/system_wrapper.v'
assert wrapper.read_text().count('.CONFIG_PROFILE(2)')==1
adc=P/'gp/gp.adc'
pins={'safety_limit_n[0]':('V7',12),'safety_limit_n[1]':('U9',13),
      'safety_limit_n[2]':('U8',14),'safety_estop_n':('V11',15)}
original=adc.read_bytes()
with adc.open('ab') as f:
    f.write(b'\n# User-authorized 2026-10-21: unused J12 GPIO, external 3.3V pullup, active low.\n')
    for port,(ball,pin) in pins.items():
        f.write(f'# J12-{pin}\nset_pin_assignment {{ {port} }} {{ LOCATION = {ball}; IOSTANDARD = LVCMOS33; }}\n'.encode())
project=P/'system.al'
project.write_bytes(re.sub(r'(<Project [^>]*Path=")[^"]*',lambda m:m[1]+P.as_posix(),project.read_text(),count=1).encode())
script=(P/'run.tcl').read_text()
script=re.sub(r'^cd .*',lambda m:'cd '+P.as_posix(),script,count=1,flags=re.M)
(P/'run.tcl').write_bytes(script.encode())
assert (P/'gp/gp.sdc').read_bytes()==(H/'frozen/pl/gp/gp.sdc').read_bytes()
(H/'hardware-changes.json').write_text(json.dumps({'from':'rtl_path38 / rtl37_candidate_r5',
    'changes':['four explicit J12 input locations; original full CONFIG_PROFILE2 retained'],
    'pins':pins,'input_assertion':'external pullup to BANK11 3.3V; contact to GND asserts low',
    'external_pullup_value_ohms':None,'wiring_measured':False,
    'production_home_approved':False,'final_pnr_required':True,
    'resource_fixture_profile':2,'motion_authorized':False,
    'speed':'reference 2; physical part grade unconfirmed',
    'sdc_byte_unchanged':True,'threads':16,'bitgen_permitted':False},indent=2)+'\n')
print(P)
