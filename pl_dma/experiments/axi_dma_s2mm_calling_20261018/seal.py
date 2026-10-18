"""Collect small support attachments. Hash only explicit delivery/source allowlist."""
import csv,hashlib,json,re,shutil,subprocess,collections
from pathlib import Path
from experiment import E,R,TD,IP

def main():
    out=E/'evidence';out.mkdir(exist_ok=True)
    key=[]
    for idx in [0,1]:
        name=f'AXI_DMA_{idx}';src=E/'build/al_ip'/name;dst=out/name;dst.mkdir(exist_ok=True)
        for f in ['Design.xml','DesignConfiguration.xml',name+'.xml',name+'.v','.m_params_'+name+'.txt','.ports_'+name+'.txt','.params_'+name+'.txt']:
            shutil.copyfile(src/f,dst/f);key.append(dst/f)
        key.append(src/'RTL'/f'axi_dma_{name}.v')
    shutil.copyfile(E/'build/log/ipgen.log',out/'official_DRE1_gui_steps.log')
    q=json.loads((R/'pl_rs485/evidence/identity_telemetry.json').read_text())['effective_s2mm_parameters']
    current_header=(R/'pl_interface/generated/interface_defs.vh').read_text()
    for k,v in q.items():
        m=re.search(r'^`define\s+PLI_TELEM_DMA_'+k+r"\s+32'h([0-9A-Fa-f]+)\s*$",current_header,re.M)
        assert m and int(m[1],16)==v, 'Current parameter/header differs from recorded baseline: '+k
    head=(IP/'axi_dma.v').read_text().split('`pragma protect')[0]
    defaults={k:int(v.replace('_','')) for k,v in re.findall(r'parameter\s+(AL_\w+)\s*=\s*([\d_]+)',head)}
    raw=(out/'AXI_DMA_1/AXI_DMA_1.v').read_text()
    passed={k:int(v) for k,v in re.findall(r'\.(AL_\w+)\((\d+)\)',raw)}
    with (out/'parameters.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['parameter','A_explicit','official_B_explicit_or_omitted','bottom_default','B_effective','effective_equal'])
        for k,v in q.items():w.writerow([k,v,passed.get(k,'OMITTED'),defaults[k],passed.get(k,defaults[k]),v==passed.get(k,defaults[k])])
    ap=re.findall(r'^\s*(input|output)\s*(?:\[([^]]+)\])?\s*(\w+)\s*[,\r\n]',head,re.M)
    bp=set(re.findall(r'^\s*(?:input|output)\s+(?:\[[^]]+\]\s*)?(\w+)\s*[,\n]',raw,re.M))
    prod=(R/'pl_dma/rtl/telemetry_dma_lite_top.v').read_text()
    assignments=dict(re.findall(r'assign\s+d_(\w+)\s*=\s*([^;]+)',prod))
    read_ties={'m_axi_mm2s_araddr','m_axi_mm2s_arlen','m_axi_mm2s_arsize','m_axi_mm2s_arburst','m_axi_mm2s_arprot','m_axi_mm2s_arcache','m_axi_mm2s_arvalid','m_axi_mm2s_rready'}
    with (out/'ports.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['port','direction','bottom_range','A_connection','B_IP_connection','B_peripheral_adapter'])
        for d,width,n in ap:
            w.writerow([n,d,width,'d_'+n+'; '+assignments.get(n,'peripheral/bus or unused output'), 'd_'+n if n in bp else 'OMITTED (unconnected at bottom)', 'external read-bus constant 0' if n in read_ties else 'same peripheral'])
    results=[]
    for p in sorted((E/'build').glob('*/result.json')):
        v=json.loads(p.read_text());results.append(v)
    # A2 predates common matrix runner, recover directly from original artifacts.
    log=(E/'build/A2/run.log').read_text();area=(E/'build/A2/gate.area').read_text()
    results.insert(0,{'tag':'A2','kind':'baseline','complete':'EXPERIMENT_COMPLETE' in log,'threads':re.findall(r'Number of Thread = (\d+)',log),'diagnostics':[x for x in log.splitlines() if re.search(r' (?:CRITICAL-WARNING|WARNING|ERROR):',x)],'resources':{k:int(re.search(re.escape(k)+r'\s+(\d+)',area)[1]) for k in ['#unit lut*','#slice reg','#eram','#dsp','#lut']}})
    (out/'results.json').write_text(json.dumps(results,indent=2))
    with (out/'matrix.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['tag','change','complete','threads_readback','SYN5066_count','LUT6_equivalent','registers','ERAM','DSP'])
        for v in results:
            if 'complete' not in v:continue
            a=v.get('resources',{});w.writerow([v['tag'],v['kind'],v['complete'],','.join(v['threads']),sum('SYN-5066' in x for x in v['diagnostics']),*[a.get(k,'N/A') for k in ['#unit lut*','#slice reg','#eram','#dsp']]])
    with (out/'warnings.md').open('w') as f:
        f.write('# Raw synthesis diagnostics and counts\n\nFull text for every run is in results.json and build/<tag>/run.log. No diagnostics were suppressed by experiment scripts.\n\n')
        for v in results:
            if 'diagnostics' not in v:continue
            codes=collections.Counter(re.search(r'(\w+-\d+) ',x)[1] for x in v['diagnostics'])
            f.write(f"## {v['tag']}\n\n{dict(codes)}\n\n")
            for x in v['diagnostics']:
                if 'SYN-5066' in x:f.write('```text\n'+x+'\n```\n\n')
    key += [IP/'axi_dma.v',IP/'axi_dma_func_pkg.vh',IP/'axi_dma_param_pkg.vh',TD/'ip/depot/AXI_DMA_1.0/Component.xml',TD/'ip/depot/AXI_DMA_1.0/Dependency.tcl',TD/'ip/depot/AXI_DMA_1.0/Layout.tcl',TD/'ip/depot/AXI_Protocol_Converter_1.0/AXI_MM/RTL/axi_protocol_converter_merge.v']
    key += [R/p for p in ['pl_dma/rtl/telemetry_dma_lite_top.v','pl_dma/rtl/telemetry_dma_guard.v','pl_interface/generated/interface_defs.vh','pl_dma/tb/tb_dma.v','pl_dma/tb/telemetry_ip_scenarios.vh']]
    key += [E/p for p in ['experiment.py','matrix.py','simulate.py','generate_official.py','replay_official.py','seal.py','build_functional.py']]
    key += [E/'build/A_repeat/telemetry_dma_lite_top.v',E/'build/B2/telemetry_dma_lite_top.v',E/'build/A2/top.v']
    manifest={'baseline_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'tool':'TD 2026.1 SP2 6.2.2.200067','device':'DR1M90GEG400','reference_speed':2,'physical_speed_verified':False,'actual_clock_Hz':100000000,'hash_policy':'Only explicit key handoff files and directly corresponding source; no logs, databases, gate netlists, intermediate products or historical evidence hashed.','sha256':{p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in key},'official_overrides':passed,'bottom_defaults':defaults,'all_A_explicit_parameters':q,'A_port_count':len(ap),'official_port_count':len(bp),'generated_protected_RTL':'Tool output ciphertext differs from depot; no decrypted or modified protected source, no inferred byte equivalence.'}
    (out/'identity.json').write_text(json.dumps(manifest,indent=2))
    # Bounded list of retained originals, not a hash inventory.
    with (out/'artifact_index.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['path_relative_to_experiment','bytes'])
        for pattern in ['*/run.log','*/run.tcl','*/gate.area','*/gate.v','*/gate.db','*/sources.json','*/result.json','*/compile.log','*/simulation.log','*/launch.log','*/command.json']:
            for p in sorted((E/'build').glob(pattern)):w.writerow([p.relative_to(E).as_posix(),p.stat().st_size])
    print('sealed',len(key),'explicit source/delivery hashes; ports',len(ap),len(bp))

if __name__=='__main__':main()
