"""One user-requested complete candidate36 P&R, independent of the chat turn."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BUILD = ROOT / 'pl_safety/build/rtl_path36'
TASK = 'Codex-PL36-PnR-20261020-R1'


def save(name, value):
    temp = HERE / (name + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    for attempt in range(10):
        try:
            temp.replace(HERE / name)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(.1)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def main():
    assert not (HERE / 'state.json').exists(), 'Refuse duplicate worker'
    assert (BUILD / 'run.tcl').is_file()
    assert not (BUILD / 'run.log').exists(), 'Refuse existing run'
    state = dict(phase='starting_builder', worker_pid=os.getpid(),
                 worker_parent_pid=os.getppid(), task_name=TASK,
                 origin='Windows Task Scheduler; one-shot; zero triggers',
                 started_at=stamp(), hashes_computed=False)
    save('state.json', state)
    result = dict(flow_completed=False, signoff_pass=False, hashes_computed=False)
    try:
        python = Path(sys.executable).with_name('python.exe')
        command = [str(python), '-u', str(HERE.parent / 'rtl_candidate_build.py'),
                   '--candidate', str(HERE.parent / 'rtl36_candidate_r1'),
                   '--tag', 'rtl_path36', '--run-prepared']
        with (HERE / 'builder.log').open('x') as log:
            child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            state.update(phase='full_flow_running', builder_pid=child.pid,
                         builder_started_at_utc=stamp())
            save('state.json', state)
            code = child.wait()
        summary = BUILD / 'route_summary.json'
        if summary.exists():
            result.update(json.loads(summary.read_text()))
        result.update(builder_exit_code=code, completed_at=stamp())
        assert code == 0 and result['flow_completed'], 'Inspect builder.log and run.log'
    except BaseException:
        result.update(failure=traceback.format_exc(), completed_at=stamp())
    finally:
        save('result.json', result)
        state.update(phase='completed' if result['flow_completed'] else 'failed', updated_at=stamp())
        save('state.json', state)
        # Remove only this run's triggerless task after all children have exited.
        cleanup = "$s=New-Object -ComObject Schedule.Service; $s.Connect(); $s.GetFolder('\\').DeleteTask('" + TASK + "',0)"
        try:
            proc = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                                   '-WindowStyle', 'Hidden', '-Command', cleanup],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            save('task_cleanup.json', dict(task_name=TASK, definition_removed=proc.returncode == 0,
                                          output=proc.stdout, hashes_computed=False))
        except BaseException:
            save('task_cleanup.json', dict(task_name=TASK, failure=traceback.format_exc()))


if __name__ == '__main__':
    main()
