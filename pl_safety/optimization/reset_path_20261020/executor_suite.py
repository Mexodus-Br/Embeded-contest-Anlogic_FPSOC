"""Run the unmodified safety assertions with an isolated executor source.

Only source selection and the helper script location change; original tests,
phase counts, expected values and pass/fail assertions are kept verbatim.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True)
    p.add_argument('--candidate');p.add_argument('--source-directory');a=p.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
    assert bool(a.candidate) != bool(a.source_directory)
    candidate=Path(a.candidate or a.source_directory).resolve();assert candidate.exists()
    out=HERE/a.tag;out.mkdir(exist_ok=False)
    helper=(ROOT/'pl_safety/tests/interlocks.py').read_text()
    rootline='ROOT = Path(__file__).resolve().parents[2]'
    assert helper.count(rootline)==1
    helper=helper.replace(rootline,'ROOT = Path('+repr(ROOT.as_posix())+')\nimport sys\nsys.path.insert(0,str(ROOT / "pl_safety/tests"))')
    select='*[str(ROOT / x) for x in sources]'
    assert helper.count(select)==1
    if a.candidate:
        replacement='*['+repr(candidate.as_posix())+' if x=="pl_motion/rtl/motion_executor.v" else str(ROOT / x) for x in sources]'
    else:
        replacement='*[str(Path('+repr(candidate.as_posix())+') / Path(x).name) if (Path('+repr(candidate.as_posix())+') / Path(x).name).is_file() else str(ROOT / x) for x in sources]'
    helper=helper.replace(select,replacement)
    (out/'interlocks.py').write_text(helper)
    suite=(ROOT/'pl_safety/tests/interlock_suite.py').read_text()
    assert suite.count(rootline)==1
    suite=suite.replace(rootline,'ROOT = Path('+repr(ROOT.as_posix())+')')
    old="str(ROOT / 'pl_safety/tests/interlocks.py')"
    assert suite.count(old)==1
    suite=suite.replace(old,repr((out/'interlocks.py').as_posix()))
    (out/'suite.py').write_text(suite)
    with (out/'run.log').open('w') as log:
        proc=subprocess.run([sys.executable,str(out/'suite.py'),'--tag',a.tag],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    result=json.loads((ROOT/'pl_safety/evidence'/('interlock_suite_'+a.tag)/'result.json').read_text())
    result['candidate']=candidate.relative_to(ROOT).as_posix()
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    assert proc.returncode==0 and result['passed']
    print('PASS isolated executor suite',len(result['cases']))

if __name__=='__main__':main()
