"""Fail-fast GP profile simulation. Independent component first, then integration."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sim_tools import Simulator
from prepare_gp_ip import prepare

def main():
    b=ROOT/'build/gp_sim';sim=Simulator(b)
    sources=[ROOT/'rtl/gp_control_regs.v',ROOT/'tb/tb_gp_control_regs.v']
    image=b/'regs.vvp'
    sim.compile(sources,'tb_gp_control_regs',image,includes=[ROOT.parent/'pl_interface'])
    log=sim.simulate(image)
    (b/'regs.log').write_text(log)
    if 'PASS gp_control_regs checks=' not in log:raise RuntimeError('GP component did not pass')
    print(log.strip())
    adapter_sources=[ROOT/'rtl/gp_ps_write_adapter.v',ROOT/'tb/tb_gp_ps_write_adapter.v']
    adapter_image=b/'adapter.vvp'
    sim.compile(adapter_sources,'tb_gp_ps_write_adapter',adapter_image)
    adapter_log=sim.simulate(adapter_image);(b/'adapter.log').write_text(adapter_log)
    if 'PASS gp_ps_write_adapter checks=' not in adapter_log:raise RuntimeError('PS write owner adapter did not pass')
    print(adapter_log.strip())
    vendor,manifest=prepare()
    integrated=[vendor,ROOT/'rtl/gp_control_regs.v',ROOT/'rtl/gp_control_top.v',ROOT/'rtl/gp_ps_write_adapter.v',
                ROOT/'rtl/gp_ps_control_top.v',ROOT/'tb/tb_gp_control_top.v',ROOT/'tb/tb_gp_ps_control_top.v']
    # Icarus cannot execute IEEE protected TD IP. This is a separate required
    # real-IP test using installed Questa, not a fallback behavioral model.
    vlog=shutil.which('vlog');vsim=shutil.which('vsim')
    if not vlog or not vsim:raise RuntimeError('Questa vlog/vsim required for protected real-IP integration')
    qb=ROOT/'build/gp_questa';qb.mkdir(parents=True,exist_ok=True)
    commands=[['vlib',str(qb/'work')],
              [vlog,'-work',str(qb/'work'),'+incdir+'+str(ROOT.parent/'pl_interface'),'+incdir+'+str(ROOT/'tb')]+[str(p) for p in integrated],
              [vsim,'-batch','work.tb_gp_control_top','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],
              [vsim,'-batch','work.tb_gp_ps_control_top','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0']]
    logs=[]
    for n,args in enumerate(commands):
        if n==0:args[0]=str(Path(vlog).parent/'vlib.exe')
        r=subprocess.run(args,cwd=qb,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
        (qb/('verified_'+str(n)+'.log')).write_text(r.stdout)
        logs.append(r.stdout)
        if r.returncode or re.search(r'\*\* (Error|Fatal)',r.stdout):
            raise RuntimeError('Questa real-IP step failed: '+str(qb/('verified_'+str(n)+'.log')))
    top_log=logs[2];ps_log=logs[3]
    if 'PASS gp_control_top checks=' not in top_log:raise RuntimeError('GP integration did not pass')
    print(next(x.strip() for x in top_log.splitlines() if 'PASS gp_control_top checks=' in x))
    if 'PASS gp_ps_control_top checks=' not in ps_log:raise RuntimeError('Actual PS boundary did not pass')
    print(next(x.strip() for x in ps_log.splitlines() if 'PASS gp_ps_control_top checks=' in x))
    result={'date':'2026-10-12','status':'PASS','profile':'gp_control_probe_v1','component':'PASS','log':log.strip(),
            'schema_sha256':hashlib.sha256((ROOT.parent/'pl_interface/schema.json').read_bytes()).hexdigest(),
            'source_sha256_lf':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_text().encode()).hexdigest() for p in sources},
            'integration':'PASS','integration_log':next(x.strip() for x in top_log.splitlines() if 'PASS gp_control_top checks=' in x),
            'integration_simulator':str(vsim),'integration_reports':str(qb/'verified_2.log'),
            'ps_write_adapter':'PASS','ps_write_adapter_log':adapter_log.strip(),
            'ps_boundary':'PASS','ps_boundary_log':next(x.strip() for x in ps_log.splitlines() if 'PASS gp_ps_control_top checks=' in x),
            'ps_boundary_reports':str(qb/'verified_3.log'),
            'converter':manifest,'hardware_verified':False}
    result['source_sha256_lf'].update({str(p.relative_to(ROOT)):hashlib.sha256(p.read_text().encode()).hexdigest() for p in integrated[1:]})
    result['source_sha256_lf'].update({str(p.relative_to(ROOT)):hashlib.sha256(p.read_text().encode()).hexdigest() for p in adapter_sources})
    (ROOT/'GP_SIM_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    try:main()
    except Exception as e:
        (ROOT/'GP_SIM_RESULTS.json').write_text(json.dumps({'status':'FAILED','error':str(e),'hardware_verified':False},indent=2)+'\n')
        raise
