"""Original C decoders and telemetry IRQ/result fixtures in independent evidence.

Reuse original fixture literals and assertions. No source/log/vector hashes.
No BSP, device, serial-port or board operation is performed.
"""
import argparse,ast,json,re,shutil,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent

def literals(path):
    result={}
    for n in ast.parse(path.read_text()).body:
        if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):
            for t in n.targets:
                if isinstance(t,ast.Name):result[t.id]=n.value.value
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--regressions',required=True);a=p.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
    out=HERE/a.tag;out.mkdir(exist_ok=False)
    result={'passed':False,'hashes_computed':False,'cases':[]}
    def run(label,commands):
        dest=out/label;dest.mkdir()
        for i,cmd in enumerate(commands):
            with (dest/(str(i)+'.log')).open('w') as log:proc=subprocess.run(cmd,cwd=dest,stdout=log,stderr=subprocess.STDOUT,timeout=240)
            assert proc.returncode==0,(label,i)
        log=(dest/(str(len(commands)-1)+'.log')).read_text();assert 'PASS' in log,label
        result['cases'].append({'case':label,'passed':True,'output':log.strip()})
        print('PASS',label,flush=True)
    try:
        regress=ROOT/'pl_safety/evidence'/a.regressions
        assert json.loads((regress/'result.json').read_text())['passed']
        vectors=regress/'32_tb_telemetry/frames.hex';assert vectors.is_file()
        for label,sources,args in [
          ('gp_software',['software/rs485_gp.c','software/example.c','tests/test_gp_software.c'],[]),
          ('telemetry_software',['software/rs485_gp.c','software/rs485_telem.c','tests/test_telem_software.c'],[str(vectors)])]:
            exe=out/label/'test.exe'
            run(label,[[shutil.which('gcc'),'-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O2',*[str(ROOT/'pl_rs485'/s) for s in sources],'-o',str(exe)],[str(exe),*args]])
        original=(ROOT/'pl_rs485/tests/tb_telemetry.v').read_text()
        irq=literals(ROOT/'pl_rs485/tests/run_telem_irq.py')
        results=literals(ROOT/'pl_rs485/tests/run_telem_results.py')
        for label,tb in [
            ('telemetry_irq',original.replace('  arm_packet(id,1,1024);',irq['ready']+'  arm_packet(id,1,1024);').replace('  $display("PASS telemetry unit',irq['race']+'  $display("PASS telemetry IRQ unit')),
            ('telemetry_results',original.replace('  $display("PASS telemetry unit',results['extra']+'  $display("PASS telemetry result unit'))]:
            bench=out/(label+'.v');bench.write_text(tb);exe=out/label/'test.vvp'
            run(label,[[shutil.which('iverilog'),'-g2005','-I',str(ROOT/'pl_rs485/generated'),'-I',str(ROOT/'pl_rs485/tests'),'-s','tb_telemetry','-o',str(exe),*[str(s) for s in (ROOT/'pl_rs485/rtl').glob('*.v')],str(bench)],
                       [shutil.which('vvp'),str(exe)]])
        run('abi',[[shutil.which('python'),str(ROOT/'pl_safety/verify_interlock.py')]])
        result['passed']=True
    except Exception:result['failure']=traceback.format_exc();raise
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
