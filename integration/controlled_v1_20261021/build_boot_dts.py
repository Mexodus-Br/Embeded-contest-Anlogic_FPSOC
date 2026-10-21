"""New HPF-generated PS header and frozen seven-window disabled control DT."""
from pathlib import Path
import subprocess,re,json
H=Path(__file__).resolve().parent
T=H.parent/'boot_candidate_v1'
W=Path.home()/'embedded-bsp-wifi-20261018'; B=Path.home()/'embedded-bsp'
K=W/'vendor/sources/linux'; D=T/'output/dts'; O=T/'output/boot'
D.mkdir(parents=True,exist_ok=False); O.mkdir(parents=True,exist_ok=True)
import shutil
for pattern in ('*.dts','*.dtsi','*.h'):
    for p in (K/'arch/arm64/boot/dts/anlogic').glob(pattern):shutil.copyfile(p,D/p.name)
subprocess.check_call(['python3',str(T/'bsp/scripts/dts_from_hpf.py'),str(T/'system.hpf'),str(D/'anlogic-dr1m90-hpf.h')])
source=(T/'bsp/configs/kernel.dts').read_text()
source+='\n&usb_otg0 { status = "okay"; };\n'
source+='\n'+(H/'frozen/software/bsp/gp/generated/gp-candidate.dtsi').read_text()
motion=(H/'frozen/software/bsp/motion/motion-control.dtsi').read_text()
motion=motion.replace('status = "okay"','status = "disabled"')
source+='\n'+motion+'\n'+(H/'board-disabled.dtsi').read_text()
(D/'integration.dts').write_text(source)
expanded=T/'output/debug/integration.expanded.dts';expanded.parent.mkdir(exist_ok=True)
with expanded.open('w') as f:
    subprocess.check_call([str(B/'vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-gcc'),'-E','-P','-x','assembler-with-cpp','-nostdinc','-undef','-D__DTS__','-I',str(D),'-I',str(K/'include'),'-I',str(K/'arch/arm64/boot/dts'),str(D/'integration.dts')],stdout=f)
dtb=O/'system.dtb'
subprocess.check_call([str(W/'output/kernel/scripts/dtc/dtc'),'-I','dts','-O','dtb','-o',str(dtb),str(expanded)])
# Use the same translated-resource walker as the reviewed disabled preview.
aud=(T.parent/'build/dts-preview/audit.py').read_text();(D/'audit.py').write_text(aud)
subprocess.check_call(['python3',str(D/'audit.py'),str(dtb),str(T/'output/debug/dt-audit.json')])
nodes=['/soc/gp-control@80400000','/soc/dma@80500000','/soc/motion-control@80600000','/soc/rs485-control@80700000','/soc/dma@80900000','/soc/safety@80a00000']
for node in nodes:
    assert subprocess.check_output(['fdtget','-t','s',str(dtb),node,'status']).decode().strip()=='disabled',node
assert subprocess.check_output(['fdtget','-t','x',str(dtb),'/memory','reg']).decode().split()==['0','0','0','40000000']
# Reuse U-Boot only if all boot-critical generated values remain equal.
keys=['AL_PROCESSOR_CORE0_CLOCK','AL_PROCESSOR_CORE1_CLOCK','AL_UART_CLOCK','AL_MMC0_PS_MAX_FREQ','AL_MMC1_PS_MAX_FREQ','AL_DDRC_CAPACITY']
def values(p):
    text=p.read_text();return {k:re.findall(r'^#define\s+'+k+r'\s+([^\n]+)',text,re.M)[-1].strip() for k in keys}
assert values(D/'anlogic-dr1m90-hpf.h')==values(B/'output/hpf-dts.h'),'U-Boot rebuild required'
(T/'output/debug/dt-origin.json').write_text(json.dumps({'header_from_new_hpf':True,'all_control_nodes_disabled':True,'boot_critical_macros_unchanged':values(D/'anlogic-dr1m90-hpf.h'),'old_scope_boot_used':False},indent=2)+'\n')
print('PASS new HPF header, seven windows/eight SPIs, 1GiB and disabled controls')
