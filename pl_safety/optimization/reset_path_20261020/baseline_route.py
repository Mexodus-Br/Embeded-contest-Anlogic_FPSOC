"""Complete an independent route of the preserved pre-change gate checkpoint.

The 44 staged RTL/header files must equal Git 07745a8 (line-ending normalized).
Only named source directories, original constraints and gate reports/DB are
copied. No old project, log, intermediate database or working RTL is modified.
"""
import argparse,json,re,shutil,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);a=p.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
    src=ROOT/'pl_safety/build/interlock_route16';out=ROOT/'pl_safety/build'/a.tag
    out.mkdir(exist_ok=False)
    checks=[]
    for folder in ['pl_motion/rtl','pl_rs485/rtl','pl_safety/rtl','pl_safety/generated']:
        for source in (ROOT/folder).glob('*.v*'):
            name=source.relative_to(ROOT).as_posix()
            ref=subprocess.check_output(['git','show','07745a8:'+name],cwd=ROOT)
            assert ref.replace(b'\r\n',b'\n')==(src/'gp'/source.name).read_bytes().replace(b'\r\n',b'\n'),name
            checks.append(name)
    for name in ['gp','system']:shutil.copytree(src/name,out/name)
    for name in ['system.al','gate.area','gate.timing','gate.db','place_budget.sdc','route_budget.sdc']:
        shutil.copyfile(src/name,out/name);assert (out/name).read_bytes()==(src/name).read_bytes(),name
    for name in ['gp/gp.sdc','gp/gp.adc','gp/ps-generated-properties.tcl','gp/axi_dma.v','gp/axi_protocol_converter_merge.v','gp/axi_dma_func_pkg.vh','gp/axi_dma_param_pkg.vh']:
        assert (out/name).read_bytes()==(ROOT/'pl_safety/build/closure_cofactor_route5'/name).read_bytes(),name
    project=(out/'system.al').read_text();project=project.replace(src.as_posix(),out.as_posix())
    (out/'system.al').write_text(project)
    threads='''set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread
'''
    tail=(src/'run.tcl').read_text().split('export_db gate.db',1)[1]
    script=f'''cd {out.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
{threads}
import_db {(out/'gate.db').as_posix()}
{threads}
clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
set_param place hfn_opt_effort high
set_param place max_fanout 128
set_param place opt_timing high
set_param place logic_level_opt on
report_param -all -file effective_parameters.tcl
'''+tail
    (out/'run.tcl').write_text(script)
    metadata={'baseline_commit':'07745a8','preserved_gate_source':'interlock_route16','direct_source_checks':checks,'hashes_computed':False,'no_bitgen':True}
    (out/'inputs.json').write_text(json.dumps(metadata,indent=2)+'\n')
    result={'passed':False,'signoff_pass':False,'hashes_computed':False,'resumed_from':'preserved baseline gate.db'}
    try:
        with (out/'run.log').open('w') as log:
            proc=subprocess.run([shutil.which('td_commands_prompt'),(out/'run.tcl').as_posix()],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=14400)
        text=(out/'run.log').read_text(errors='replace')
        assert proc.returncode==0 and 'INTERLOCK_FULL_TOP_COMPLETE' in text and not re.search(r'\bERROR:|TMR-250[79]',text)
        assert 'INTERLOCK_TD_THREADS 16' in text and 'Number of Thread = 16' in text
        assert not re.search(r'Global iterations in (?!16\b)\d+ thread',text)
        stages={}
        for stage in ['gate','place','route']:
            report=(out/(stage+'.timing')).read_text()
            stages[stage]={k:float(re.search(v,report)[1]) for k,v in [('setup_ns',r'SWNS:\s*([-\d.]+)ns'),('hold_ns',r'HWNS:\s*([-\d.]+)ns')]}
            assert set(re.findall(r'sdc uncertainty\s*:?\s*([-\d.]+)',report))<={'0.000'}
        for name in ['gp/gp.sdc','gp/gp.adc','gp/ps-generated-properties.tcl','gate.db']:
            assert (out/name).read_bytes()==(src/name).read_bytes(),name
        result.update(passed=True,threads=16,stages=stages,timing_pass=stages['route']['setup_ns']>1 and stages['route']['hold_ns']>=0)
        print(result)
    except Exception:result['failure']=traceback.format_exc();raise
    finally:(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
