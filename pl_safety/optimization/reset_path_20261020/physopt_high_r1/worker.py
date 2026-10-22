"""One requested post-route HIGH run; independent input and output databases.

Started by a one-shot, triggerless Windows task so the run survives this chat
turn. No synthesis, RTL edits, bit generation, board access or file hashes.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import traceback
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'pl_safety/build/reset_path21'
BUILD = ROOT / 'pl_safety/build/reset21_physopt_high_r1'
TD = Path('D:/Anlogic/TD_Release_2026.1_SP2.200.067/bin/td_commands_prompt.exe')
CONSTRAINTS = ['gp/gp.sdc', 'gp/gp.adc', 'gp/ps-generated-properties.tcl']
TASK_NAME = 'Codex-PL21-PhysOptHigh-20261020-R1'


def stamp():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    for attempt in range(5):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(.1)


def timing(name):
    text = (BUILD / name).read_text()
    return {key: float(re.search(pattern, text)[1]) for key, pattern in [
        ('setup_ns', r'SWNS:\s*([-\d.]+)ns'),
        ('hold_ns', r'HWNS:\s*([-\d.]+)ns')]}


def resources(name):
    text = (BUILD / name).read_text()
    fields = {'lut6': r'^#lut6\s+', 'slice': r'^#slice\s+',
              'slice_reg': r'^  #slice reg\s+', 'pad_reg': r'^  #pad reg\s+',
              'eram': r'^#eram\s+', 'dsp': r'^#dsp\s+', 'io': r'^#IO\s+'}
    return {key: int(re.search(pattern + r'(\d+)', text, re.M)[1])
            for key, pattern in fields.items()}


def prepare():
    assert TD.is_file(), TD
    summary = json.loads((SOURCE / 'summary.json').read_text())
    assert summary['passed'] and summary['threads'] == 16
    assert summary['stages']['route'] == {'setup_ns': -1.339, 'hold_ns': .020}
    BUILD.mkdir(exist_ok=False)
    for name in CONSTRAINTS:
        target = BUILD / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / name, target)
        assert target.read_bytes() == (SOURCE / name).read_bytes(), name
    shutil.copyfile(SOURCE / 'route.db', BUILD / 'route_input.db')
    assert (SOURCE / 'route.db').read_bytes() == (BUILD / 'route_input.db').read_bytes()
    shutil.copyfile(SOURCE / 'route.area', BUILD / 'source_route.area')
    threads = '''set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "PHYSOPT_HIGH_THREADS [get_param flow thread]"
get_num_thread
'''
    nominal = '''clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
'''
    script = f'''cd {BUILD.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
{threads}
import_db {(BUILD / 'route_input.db').as_posix()}
{threads}
{nominal}
update_timing -mode final
report_timing_summary -file before.timing -path_num 10
puts PHYSOPT_HIGH_BEGIN
phys_opt -post_route -effort high
puts PHYSOPT_HIGH_END
{threads}
{nominal}
update_timing -mode final
report_timing_summary -file route.timing -path_num 10
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
export_sdc -file nominal_route.sdc
export_db route.db
puts PHYSOPT_HIGH_COMPLETE
exit
'''
    (BUILD / 'run.tcl').write_text(script, encoding='utf-8')
    write_json(BUILD / 'inputs.json', {
        'source_build': 'reset_path21', 'source_database': str(SOURCE / 'route.db'),
        'input_database_copy': str(BUILD / 'route_input.db'),
        'command': 'phys_opt -post_route -effort high', 'threads': 16,
        'device': 'DR1M90GEG400', 'reference_speed': 2, 'clock_period_ns': 10,
        'constraints_direct_byte_equal': CONSTRAINTS, 'hashes_computed': False,
        'no_bitgen': True, 'no_board_access': True, 'prepared_at': stamp()})
    write_json(BUILD / 'state.json', {'phase': 'prepared', 'updated_at': stamp(),
                                    'hashes_computed': False})
    print('Prepared independent HIGH post-route project:', BUILD)


def run(task_name):
    assert task_name == TASK_NAME
    assert BUILD.is_dir() and not (BUILD / 'result.json').exists()
    assert not (BUILD / 'run.log').exists(), 'Do not restart/overwrite this attempt'
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.IsProcessInJob.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    in_job = ctypes.c_int()
    assert kernel.IsProcessInJob(kernel.GetCurrentProcess(), None, ctypes.byref(in_job))
    state = {'phase': 'starting_td', 'worker_pid': os.getpid(),
             'worker_parent_pid': os.getppid(), 'worker_in_windows_job': bool(in_job.value),
             'origin': 'Windows Task Scheduler; one-shot, zero triggers',
             'task_name': task_name, 'started_at': stamp(), 'updated_at': stamp(),
             'hashes_computed': False}
    write_json(BUILD / 'state.json', state)
    result = {'flow_completed': False, 'signoff_pass': False, 'hashes_computed': False,
              'source_build': 'reset_path21', 'command': 'phys_opt -post_route -effort high',
              'started_at': state['started_at']}
    try:
        with (BUILD / 'run.log').open('w', encoding='utf-8') as log:
            child = subprocess.Popen([str(TD), (BUILD / 'run.tcl').as_posix()],
                                     cwd=BUILD, stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            state.update(phase='td_running', td_pid=child.pid,
                         td_started_at_utc=datetime.now(timezone.utc).isoformat(), updated_at=stamp())
            write_json(BUILD / 'state.json', state)
            try:
                code = child.wait(timeout=28800)
            except subprocess.TimeoutExpired:
                # This is the exact child this worker launched, never another TD.
                child.terminate()
                child.wait(timeout=30)
                raise
        log_text = (BUILD / 'run.log').read_text(errors='replace')
        assert code == 0 and 'PHYSOPT_HIGH_COMPLETE' in log_text, code
        assert not re.search(r'\bERROR:|TMR-250[79]', log_text)
        assert 'PHYSOPT_HIGH_THREADS 16' in log_text and 'Number of Thread = 16' in log_text
        assert 'start command "phys_opt -post_route -effort high"' in log_text
        before, after = timing('before.timing'), timing('route.timing')
        assert before == {'setup_ns': -1.339, 'hold_ns': .020}, before
        for filename in ['before.timing', 'route.timing']:
            text = (BUILD / filename).read_text()
            assert set(re.findall(r'sdc uncertainty\s*:?\s*([-\d.]+)', text)) <= {'0.000'}
        for name in CONSTRAINTS:
            assert (SOURCE / name).read_bytes() == (BUILD / name).read_bytes(), name
        assert (SOURCE / 'route.db').read_bytes() == (BUILD / 'route_input.db').read_bytes()
        resource_before, resource_after = resources('source_route.area'), resources('route.area')
        result.update(flow_completed=True, threads=16, before=before, after=after,
                      setup_delta_ns=round(after['setup_ns'] - before['setup_ns'], 3),
                      timing_target_met=after['setup_ns'] > 1 and after['hold_ns'] >= 0,
                      resources_before=resource_before, resources_after=resource_after,
                      resource_delta={key: resource_after[key] - value for key, value in resource_before.items()},
                      original_database_and_constraints_unchanged=True)
    except BaseException:
        result['failure'] = traceback.format_exc()
    finally:
        result['completed_at'] = stamp()
        write_json(BUILD / 'result.json', result)
        state.update(phase='completed' if result['flow_completed'] else 'failed', updated_at=stamp())
        write_json(BUILD / 'state.json', state)
        # Remove only this run's triggerless task definition after all work exits.
        cleanup = "$s=New-Object -ComObject Schedule.Service; $s.Connect(); $s.GetFolder('\\').DeleteTask('" + task_name + "',0)"
        try:
            proc = subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
                '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command', cleanup],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW)
            write_json(BUILD / 'task_cleanup.json', {'task_name': task_name,
                       'definition_removed': proc.returncode == 0, 'output': proc.stdout,
                       'hashes_computed': False})
        except BaseException:
            write_json(BUILD / 'task_cleanup.json', {'task_name': task_name,
                       'definition_removed': False, 'failure': traceback.format_exc(),
                       'hashes_computed': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--task-name')
    args = parser.parse_args()
    if args.prepare_only:
        prepare()
    else:
        run(args.task_name)
