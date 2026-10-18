"""Isolated synthesis experiment; never writes production or vendor files."""
import argparse, json, re, shutil, subprocess
from pathlib import Path
E=Path(__file__).resolve().parent
R=E.parents[2]
TD=Path('D:/Anlogic/TD_Release_2026.1_SP2.200.067')
IP=TD/'ip/depot/AXI_DMA_1.0/AXI_DMA/RTL'

def run_td(b,script):
    (b/'run.tcl').write_text(script,encoding='utf-8')
    with (b/'run.log').open('w') as f:
        p=subprocess.run([str(TD/'bin/td_commands_prompt.exe'),(b/'run.tcl').as_posix()],cwd=b,stdout=f,stderr=subprocess.STDOUT)
    return p.returncode

def baseline(tag):
    b=E/'build'/tag;b.mkdir(parents=True,exist_ok=False)
    # Same scan fixture as the historical independent component, current RTL.
    shutil.copyfile(R/'pl_dma/reports/telem_dma_r1/top.v',b/'top.v')
    header=(R/'pl_interface/generated/interface_defs.vh').read_text()
    files=[IP/'axi_dma.v',TD/'ip/depot/AXI_Protocol_Converter_1.0/AXI_MM/RTL/axi_protocol_converter_merge.v']
    for name in ['telemetry_dma_lite_top.v','telemetry_dma_guard.v']:
        p=R/'pl_dma/rtl'/name
        (b/name).write_text(p.read_text().replace('`include "generated/interface_defs.vh"',header))
        files.append(b/name)
    for name in ['axi_dma_func_pkg.vh','axi_dma_param_pkg.vh']:
        shutil.copyfile(IP/name,b/name)
    files.append(b/'top.v')
    (b/'sources.json').write_text(json.dumps([str(p) for p in files],indent=2))
    (b/'clock.sdc').write_text('create_clock -name telem_clk -period 10 [get_ports clk]\n')
    script=f'cd {{{b.as_posix()}}}\nimport_device dr1_90.db -package DR1M90GEG400 -speed 2\nset_param flow thread 16\nget_num_thread\n'
    script+=''.join(f'analyze -file {{{p.as_posix()}}}\n' for p in files)
    script+='elaborate -top telem_probe\noptimize_rtl\nread_sdc clock.sdc\noptimize_gate -maparea gate.area\nexport_db gate.db\nwrite_verilog gate.v\nget_num_thread\nputs EXPERIMENT_COMPLETE\nexit\n'
    run_td(b,script)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('tag');a=ap.parse_args();baseline(a.tag)
