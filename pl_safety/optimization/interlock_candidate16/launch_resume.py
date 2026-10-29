"""One-shot hidden independent Windows launch of the user-requested TD job."""
import ctypes,json,subprocess,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
def main():
 out=HERE/'launch_r2';out.mkdir(exist_ok=False)
 assert not (ROOT/'pl_safety/build/interlock_route16/resume_pnr_r1_summary.json').exists()
 kernel=ctypes.windll.kernel32
 kernel.GetCurrentProcess.restype=ctypes.c_void_p
 kernel.IsProcessInJob.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_int)]
 in_job=ctypes.c_int();assert kernel.IsProcessInJob(kernel.GetCurrentProcess(),None,ctypes.byref(in_job))
 flags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB
 with (out/'orchestrator.log').open('w') as log,(out/'orchestrator.err').open('w') as err:
  p=subprocess.Popen([sys.executable,'-u',str(HERE/'resume_pnr.py')],cwd=ROOT,stdout=log,stderr=err,
    stdin=subprocess.DEVNULL,creationflags=flags,close_fds=True)
 meta={'process_id':p.pid,'launched_at_taipei':datetime.now(timezone(timedelta(hours=8))).isoformat(),
       'launcher_in_windows_job':bool(in_job.value),'requested_breakaway':True,'hashes_computed':False}
 (out/'process.json').write_text(json.dumps(meta,indent=2)+'\n')
 print('Hidden independent resume process launched',p.pid,flush=True)
if __name__=='__main__':main()
