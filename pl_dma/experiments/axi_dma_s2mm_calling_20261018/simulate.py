"""Serial real-vendor RTL test using existing self-checking receive scenarios."""
import argparse,json,re,shutil,subprocess
from experiment import E,R,IP,TD

def main(tag,source_tag,gate=None):
    b=E/'build'/tag;b.mkdir(parents=True,exist_ok=False)
    src=E/'build'/source_tag
    head=(src/'telemetry_dma_lite_top.v').read_text().split('module telemetry_dma_lite_top(',1)[1].split(');',1)[0]
    ports={}
    for m in re.finditer(r'\b(input|output)\s+(?:wire|reg)\s*(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)',head,re.S):
        d,w,names=m.groups()
        for n in names.split(','):
            if n.strip():ports[n.strip()]=(d,int(w)+1 if w else 1)
    decl=[];bind=[];wire_inputs={'hp_arready','hp_awready','hp_wready','hp_bresp','hp_rresp'}
    for n,(d,w) in ports.items():
        decl.append(('wire' if d=='output' or n in wire_inputs else 'reg')+' '+(f'[{w-1}:0] ' if w>1 else '')+n+';');bind.append('.'+n+'('+n+')')
    (b/'dut_bindings.vh').write_text('\n'.join(decl)+'\nwire [31:0] loop_occupancy=0;\ntelemetry_dma_lite_top dut('+','.join(bind)+');\n')
    tb=(R/'pl_dma/tb/tb_dma.v').read_text().split('task transfer;',1)[0].replace('module tb_dma;','module tb_s2mm_real;').replace("33'h080500000","33'h080900000")
    tb+=(R/'pl_dma/tb/telemetry_ip_scenarios.vh').read_text()+'\nendmodule\n'
    # Existing harness only printed these two outcomes. Add assertions here.
    tb=tb.replace('  reset_rx;\n end\nendtask', '''  if(!exact && size>btt && last_flag) begin
   check((sr & 32'h4012)==32'h4012,"oversize error status");
   check(actual==btt,"oversize length bounded");
  end
  if(!exact && !last_flag) begin
   check(!sr[12] && (sr & 32'h770)==0,"missing TLAST not complete");
  end
  reset_rx;
 end
endtask''')
    if gate:
        # Gate optimization removes unused MM2S debug wires and bridge high bits.
        # Retain every public-port protocol/data check; drop two structural probes.
        tb=re.sub(r'\s*check\(dut\.bridge_(?:ar|aw)size\[2\].*?;', '',tb)
        tb=tb.replace('module tb_s2mm_real;','module tb_s2mm_real;\nwire [63:0] gate_unused_mm2s=0;')
        tb=re.sub(r'dut\.d_m_axis_mm2s_\w+','gate_unused_mm2s',tb)
    (b/'tb.v').write_text(tb)
    files=[p for p in json.loads((src/'sources.json').read_text()) if __import__('pathlib').Path(p).name!='top.v']+[(b/'tb.v').as_posix()]
    if gate:
        files=[p.as_posix() for d in ['common','dr1'] for p in sorted((TD/'sim_release'/d).glob('*.v'))]+[(E/'build'/gate/'gate.v').as_posix(),(b/'tb.v').as_posix()]
    def run(name,args):
        with (b/(name+'.log')).open('w') as f:p=subprocess.run(args,cwd=b,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        out=(b/(name+'.log')).read_text();assert p.returncode==0 and not re.search(r'\*\* (Error|Fatal)',out),name
        return out
    run('library',[shutil.which('vlib'),'work'])
    run('compile',[shutil.which('vlog'),'-work','work','+incdir+'+src.as_posix(),'+incdir+'+b.as_posix(),'+incdir+'+IP.as_posix(),*files])
    out=run('simulation',[shutil.which('vsim'),'-batch','work.tb_s2mm_real',*(['work.DR1_PHY_GSR'] if gate else []),'-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'])
    assert 'PASS telemetry_real_s2mm' in out
    result={'source_tag':source_tag,'status':'GATE_FUNCTION_PASS' if gate else 'RTL_PASS','gate_build':gate,'checks':[x for x in out.splitlines() if 'PROBE' in x or 'PASS telemetry' in x]}
    (b/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('tag');ap.add_argument('source_tag');ap.add_argument('--gate');a=ap.parse_args();main(a.tag,a.source_tag,a.gate)
