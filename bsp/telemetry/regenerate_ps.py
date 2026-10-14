"""Regenerate actual PS ports, synchronize XML, and export the matched HPF.

Run before integrate_gp_hardware.py/build_gp_hardware.py; use --export-hpf
after bitgen. Vendor installation and reference projects remain read-only.
"""
import argparse
from pathlib import Path
import re
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--export-hpf',action='store_true')
p.add_argument('--work-dir',default='telemetry_soc_prj')
p.add_argument('--hp0',action='store_true')
a=p.parse_args()
BSP=Path(__file__).resolve().parents[1]
W=(BSP/'work'/a.work_dir).resolve()
assert W.parent == (BSP/'work').resolve(), 'Work project must be directly inside bsp/work'
TD=Path('D:/Anlogic/TD_Release_2026.1_SP2.200.067')
IP=TD/'ip/depot/ARM_Processor_System_F9F0D0P0_1.0'
PS=W/'system/ip/system_ARM_Processor_System_0'
def run(exe,args,log):
    with (W/log).open('w',encoding='utf-8') as f:
        subprocess.run([str(exe),*map(str,args)],cwd=W,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
if a.export_hpf:
    import json
    review=json.loads((BSP/'telemetry/hardware-review.json').read_text(encoding='utf-8'))
    assert review['signoff_pass'] and review['diagnostics_closed'], 'No HPF/boot release before final hardware gates'
    assert (W/'system.bit').is_file()
    run(TD/'bin/hpfTool.exe',['-batch','-prj_path',W,'-prj_name','system',
        '-ps_path',PS,'-design_path',W/'system','-bitstream_path',W/'system.bit',
        '-bitstream_status','latest','-ip_catalog',TD/'ip/depot',
        '-tcl',BSP/'scripts/export_motion_hpf.tcl'],'hpf-final.log')
    import zipfile
    with zipfile.ZipFile(W/'system.hpf') as z:
        assert z.read('HPFs/system.bit')==(W/'system.bit').read_bytes()
else:
    run(TD/'bin/alps.exe',['-batch','-tcl',BSP/'scripts'/('../telemetry/ps_regen.tcl'),
        '-component','system_ARM_Processor_System_0','-in_path',IP,
        '-out_path',W/'system/ip','-device','DR1M90GEG400','-speed','-2'],'ps-gp-regenerate.log')
    text=(PS/'DesignTmp.xml').read_text(encoding='utf-8')
    # Preserve the vendor-sensitive ipxact namespace prefix verbatim.
    (PS/'Design.xml').write_text(text,encoding='utf-8')
    pat=r'<ipxact:configurableElementValues>.*?</ipxact:configurableElementValues>'
    payload=re.search(pat,text,re.S).group()
    design=W/'system/Design.xml'
    updated,n=re.subn(pat,lambda _:payload,design.read_text(encoding='utf-8'),count=1,flags=re.S)
    assert n==1
    design.write_text(updated,encoding='utf-8')
    script=f'''cd {W.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
xmlipgen -usernamed_file {PS.as_posix()}/system_ARM_Processor_System_0.xml -design_file {PS.as_posix()}/Design.xml -designConfig_file {PS.as_posix()}/DesignConfiguration.xml -component_file {IP.as_posix()}/Component.xml -mode behavior -package DR1M90GEG400
exit
'''
    (W/'generate_ps.tcl').write_text(script,encoding='utf-8')
    run(TD/'bin/td_commands_prompt.exe',[(W/'generate_ps.tcl').as_posix()],'actual-ps-ipgen.log')
    raw=(PS/'RTL/ARM_Processor_System_f6ddd1d59490.v').read_text()
    for port in ['master_gp0_axi_aclk','master_gp0_axi_awaddr','f2p_irq','p2f_rst0_n']:
        assert re.search(r'^\s*(input|output)\s+(?:\[[^\]]+\]\s*)?'+port+r'\s*[,)]',raw,re.M),port
    if a.hp0:
        for port in ['slave_hp0_axi_aclk','slave_hp0_axi_awaddr','slave_hp0_axi_rdata']:
            assert re.search(r'^\s*(input|output)\s+(?:\[[^\]]+\]\s*)?'+port+r'\s*[,)]',raw,re.M),port
print('PS/HPF regeneration completed; full system timing and clock-warning review remain required')
