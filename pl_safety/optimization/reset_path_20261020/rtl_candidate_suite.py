"""Original complete safety assertions with explicit new internal port wiring."""
import argparse,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
 source=Path(a.candidate).resolve();out=E/a.tag;out.mkdir(exist_ok=False)
 s=(R/'pl_safety/tests/interlock_motion_fixture.py').read_text()
 s=s.replace('ROOT = Path(__file__).resolve().parents[2]','ROOT = Path('+repr(R.as_posix())+')')
 if '.collector_config_stored_pending(' not in s:
  s=s.replace(".collector_config_pending(1'b0),",".collector_config_pending(1'b0),.collector_config_stored_pending(1'b0),")
 if (source/'fresh_time_notes.json').exists():
  s=s.replace('wire interlock_idle,interlock_idle_off;', '''wire [63:0] fixture_request_age=feedback_raw[175:112]-dut.interlocks.monitor.round_start;
wire [63:0] fixture_event_age=feedback_raw[111:48]-dut.interlocks.monitor.round_start;
wire [1:0] fixture_time_valid={!fixture_event_age[63],!fixture_request_age[63]};
wire interlock_idle,interlock_idle_off;''')
  s=s.replace('.feedback_commit(feedback_commit),.feedback_raw(feedback_raw),',
   '.feedback_time_valid(fixture_time_valid),.feedback_round_reference(),.feedback_commit(feedback_commit),.feedback_raw(feedback_raw),')
 if (source/'local_stop_notes.json').exists():
  s=s.replace('.collector_periods({32\'d1000000,128\'d0}),', '.collector_query_ok(1\'b1),.collector_periods({32\'d1000000,128\'d0}),')
 (out/'rtl26_motion_fixture.py').write_text(s)
 s=(R/'pl_safety/tests/interlocks.py').read_text()
 s=s.replace('ROOT = Path(__file__).resolve().parents[2]','ROOT = Path('+repr(R.as_posix())+')\nimport sys\nsys.path.insert(0,str(ROOT / "pl_safety/tests"))\nsys.path.insert(0,str(Path(__file__).resolve().parent))')
 s=s.replace('from interlock_motion_fixture import render','from rtl26_motion_fixture import render')
 s=s.replace('*[str(ROOT / x) for x in sources]','*[str(Path('+repr(source.as_posix())+')/Path(x).name) if (Path('+repr(source.as_posix())+')/Path(x).name).is_file() else str(Path('+repr(source.as_posix())+')/"tests"/Path(x).name) if (Path('+repr(source.as_posix())+')/"tests"/Path(x).name).is_file() else str(ROOT/x) for x in sources]')
 (out/'interlocks.py').write_text(s)
 s=(R/'pl_safety/tests/interlock_suite.py').read_text().replace('ROOT = Path(__file__).resolve().parents[2]','ROOT = Path('+repr(R.as_posix())+')')
 s=s.replace("str(ROOT / 'pl_safety/tests/interlocks.py')",repr((out/'interlocks.py').as_posix()))
 (out/'suite.py').write_text(s)
 with (out/'run.log').open('w') as log:proc=subprocess.run([sys.executable,str(out/'suite.py'),'--tag',a.tag],stdout=log,stderr=subprocess.STDOUT,cwd=R)
 result=json.loads((R/'pl_safety/evidence'/('interlock_suite_'+a.tag)/'result.json').read_text())
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');assert proc.returncode==0 and result['passed'];print('PASS unchanged safety suite',len(result['cases']))
if __name__=='__main__':main()
