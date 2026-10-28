"""Build and run the actual hardware backend against an in-memory fake board."""
import sys, os, subprocess, json, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from partner_support import ROOT,KIT,OUT,compiler,compile_sources
out=OUT/'hardware';out.mkdir(parents=True,exist_ok=True)
objects=[]
for name in ['rs485_gp','rs485_telem']:
    obj=out/(name+'.o');compile_sources([KIT/'pl_rs485/software'/(name+'.c')],obj,compiler(),cxx=False,extra=['-c']);objects.append(obj)
exe=out/('ps_hardware.exe' if os.name=='nt' else 'ps_hardware')
compile_sources([ROOT/'src/ps_core.cpp',KIT/'golden_model/src/model.cpp',*objects,*[ROOT/'src'/f for f in ['ps_backend.cpp','ps_hardware_backend.cpp','ps_linux_board.cpp','ps_runtime.cpp','ps_service.cpp']],ROOT/'tests/ps_hardware.cpp'],exe,compiler(),includes=[ROOT/'src',ROOT/'third_party',KIT],libraries=['-lbcrypt'] if os.name=='nt' else ['-pthread'])
from ps_calibration import parameters
calibration=parameters();calibration['fixture'].update(joint_min_deg=[3]*3,joint_max_deg=[86]*3)
fixture=out/'synthetic-calibration.json';fixture.write_text(json.dumps(calibration))
result=subprocess.run([str(exe),str(ROOT),str(out/('data-'+str(time.time_ns()))),str(fixture)],capture_output=True,text=True,timeout=40)
(out/'result.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
print(result.stdout+result.stderr)
if result.returncode==0:
    from jsonschema import Draft202012Validator
    schema=json.loads((ROOT/'docs/ps-api.schema.json').read_text(encoding='utf-8'))
    for line in result.stdout.splitlines():
        if line.startswith('{'):
            row=json.loads(line);name='state' if 'boot_id' in row else 'telemetry'
            Draft202012Validator({**schema,'$ref':'#/$defs/'+name}).validate(row)
    print('PASS hardware state/telemetry schema validation')
(OUT/'hardware_report.json').write_text(json.dumps({'passed':result.returncode==0,'exit_code':result.returncode,'scope':'fake_board_no_device','output':result.stdout+result.stderr},indent=2),encoding='utf-8')
raise SystemExit(result.returncode)
