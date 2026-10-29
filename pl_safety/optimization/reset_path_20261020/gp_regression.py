"""Run affected original GP regressions with every original assertion intact."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
if __name__=='__main__':
    path=ROOT/'pl_safety/tests/interlock_regressions.py'
    source=path.read_text()
    old='    try:\n        for index, (folder, top, params) in enumerate(cases):'
    assert source.count(old)==1
    new="    cases = [c for c in cases if c[1] in ['tb_gp_regs','tb_gp_stress','tb_gp_e2e']]\n"+old
    exec(compile(source.replace(old,new),str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
