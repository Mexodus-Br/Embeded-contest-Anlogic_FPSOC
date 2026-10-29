# Candidate36 independent complete P&R

Requested 2026-10-20. Run: `pl_safety/build/rtl_path36`; isolated RTL:
`pl_safety/optimization/reset_path_20261020/rtl36_candidate_r1`.
Prepared before launch, copied override sources compared directly by bytes.
Original actual system_wrapper, safety/GPIO/RS485/dual HP, device
DR1M90GEG400, reference speed2 and 100MHz retained. No protected IP edits,
deployment image, BSP or board access. No hashes calculated.

Before launch: candidate36 original375-case safety suite and65,536 modulo-time
producer differential vectors PASS. Builder also requires the unchanged module
regressions listed in rtl_candidate_build.py and checks shared source bytes.
This is permission to evaluate a candidate, not functional or production signoff.
Candidate36 real-IP system regression and final CDC/net/reset audit remain due.

The complete flow explicitly sets flow thread16 and reads get_num_thread at
synthesis/place/route boundaries. Existing1.25ns internal optimization budget
is retained for comparability; final reports clear the budget and reread original
10ns constraints. Intermediate log slack does not establish final WNS.
Acceptance remains final nominal setup strictly>1ns, hold>=0.

One-shot Windows Task Scheduler task `Codex-PL36-PnR-20261020-R1`, zero triggers,
normal current user, hidden pythonw worker, independently survives the chat turn.
The worker invokes the prepared flow once; no automatic retry. Definition is
removed on completion; logs and evidence remain. Existing tags are never reused.

PowerShell query (append -Watch for repeated read-only queries):

```powershell
& 'D:\Works\Embedded_contest\dev\pl_safety\optimization\reset_path_20261020\pnr36_r1\status.ps1' -Watch
```

Ctrl+C stops only the query. State/result live beside this README; TD reports and
run.log are in the build directory. A completed flow can still fail timing.

Launch confirmed23:48:47+08:00: task state4, worker8896 (parent2508),
builder25408, TD11300, explicit16-thread readback true; elaboration running.
Candidate29 earlier full P&R is preserved separately: route setup−1.459ns,
hold+0.020ns, Slice37309, FF37488+PAD9, LUT29308, ERAM69/DSP6. It fails timing.
No production release approval is implied; SYN-5066/electrical/board/BSP gates
remain independent. Main product RTL remains29;36 is an isolated candidate.
