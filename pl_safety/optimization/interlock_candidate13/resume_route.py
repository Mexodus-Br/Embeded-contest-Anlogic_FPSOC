"""Resume the preserved candidate13 placed DB; retain the interrupted attempt.

No source changes, no hashes, no bitstream. Final reports restore original SDC.
"""
from pathlib import Path
import json
import re
import subprocess
import traceback

ROOT = Path(__file__).resolve().parents[3]
B = ROOT / 'pl_safety/build/interlock_route13'
TD = 'D:/Anlogic/TD_Release_2026.1_SP2.200.067/bin/td_commands_prompt.exe'
threads = '''set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread
'''
original = '''clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
'''

def main():
    script = B / 'resume_route_r1.tcl'
    log = B / 'resume_route_r1.log'
    result_path = B / 'resume_route_r1_summary.json'
    assert not script.exists() and not log.exists() and not result_path.exists()
    assert (B / 'place.db').is_file() and not (B / 'route.db').exists()
    script.write_text(f'''cd {B.as_posix()}
{threads}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
import_db {(B / 'place.db').as_posix()}
{threads}
{original}
read_sdc route_budget.sdc
route
update_timing -mode final
report_timing_summary -file route_budget.timing -path_num 10
{original}
export_sdc -file nominal_route.sdc
update_timing -mode final
report_timing_summary -file route.timing -path_num 10
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
export_db route.db
puts INTERLOCK_RESUMED_ROUTE_COMPLETE
exit
''')
    result = dict(passed=False, signoff_pass=False, hashes_computed=False,
                  resumed_from='place.db', original_attempt='run.log')
    try:
        with log.open('w', encoding='utf-8') as stream:
            p = subprocess.run([TD, script.as_posix()], cwd=B, stdout=stream,
                               stderr=subprocess.STDOUT, timeout=28800)
        text = log.read_text(errors='replace')
        assert p.returncode == 0 and 'INTERLOCK_RESUMED_ROUTE_COMPLETE' in text
        assert not re.search(r'\bERROR:|TMR-250[79]', text)
        assert 'INTERLOCK_TD_THREADS 16' in text and 'Number of Thread = 16' in text
        stages = {}
        for stage in ['gate', 'place', 'route']:
            report = (B / (stage + '.timing')).read_text()
            stages[stage] = {k: float(re.search(pattern, report)[1]) for k, pattern in
                [('setup_ns', r'SWNS:\s*([-\d.]+)ns'), ('hold_ns', r'HWNS:\s*([-\d.]+)ns')]}
            if stage != 'gate':
                assert set(re.findall(r'sdc uncertainty\s*:?\s*([-\d.]+)', report)) <= {'0.000'}
        result.update(passed=True, threads=16, stages=stages,
                      timing_pass=stages['route']['setup_ns'] > 1 and stages['route']['hold_ns'] >= 0)
    except Exception:
        result['failure'] = traceback.format_exc()
        raise
    finally:
        result_path.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)

if __name__ == '__main__':
    main()
