"""Compile and walk seven-window disabled preview; never a final HPF DTB."""
import json
from pathlib import Path
import subprocess
H=Path(__file__).resolve().parent
T=H.parent
W=Path.home()/'embedded-bsp-wifi-20261018'
out=T/'build/dts-preview'
out.mkdir(exist_ok=False)
source=(W/'output/debug/wifi-board.expanded.dts').read_text()
for label in ['bsp_gp','pl_dma_loop','motion_control']:
    assert label+':' in source,label
    source+='\n&'+label+' { status = "disabled"; };\n'
source+=(H/'board-disabled.dtsi').read_text()
(out/'preview.dts').write_text(source)
dtb=out/'preview.dtb'
subprocess.check_call([str(W/'output/kernel/scripts/dtc/dtc'),'-I','dts','-O','dtb','-o',str(dtb),str(out/'preview.dts')])
audit=(H/'frozen/software/bsp/telemetry/audit_dtb.py').read_text()
schema=json.loads((H/'frozen/software/pl_interface/schema.json').read_text())
s=schema['safety_profiles']['gp_safety_home_v1']
node='/soc/safety@'+format(s['base'],'x')
old="0x80900000:'/soc/dma@80900000'}"
assert audit.count(old)==1
audit=audit.replace(old,"0x80900000:'/soc/dma@80900000',"+str(s['base'])+":"+repr(node)+"}")
old="88:'/soc/dma@80900000/dma-channel@30'}"
assert audit.count(old)==1
audit=audit.replace(old,"88:'/soc/dma@80900000/dma-channel@30',"+str(s['irq_spi'])+":"+repr(node)+"}")
audit=audit.replace('six translated CPU windows and seven level-high GIC SPIs','seven translated CPU windows and eight level-high GIC SPIs')
(out/'audit.py').write_text(audit)
subprocess.check_call(['python3',str(out/'audit.py'),str(dtb),str(out/'audit.json')])
for node in ['/soc/gp-control@80400000','/soc/dma@80500000','/soc/motion-control@80600000',
             '/soc/rs485-control@80700000','/soc/dma@80900000','/soc/safety@80a00000']:
    assert subprocess.check_output(['fdtget','-t','s',str(dtb),node,'status']).decode().strip()=='disabled',node
result=json.loads((out/'audit.json').read_text())
result.update(all_control_nodes_disabled=True,windows=7,gic_spis=8,
    source_header='Accepted scope/Wi-Fi expanded header for preview only. Final HPF not available.',
    final_hpf_matched=False)
(out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS disabled seven-window DT/GIC preview; NOT FINAL HPF OR BOOT CHAIN')
