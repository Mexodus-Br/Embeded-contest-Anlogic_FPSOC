"""Independent board candidate; do not overwrite board-tested projects."""
from pathlib import Path
import shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];src=ROOT/'bsp/work/gp_soc_prj';dst=ROOT/'bsp/work/scope_soc_prj'
subprocess.run([sys.executable,str(ROOT/'bsp/scope/verify_input.py')],check=True)
if dst.exists():raise SystemExit('scope_soc_prj exists; inspect before reusing')
dst.mkdir()
for n in ['system','uisrc']:shutil.copytree(src/n,dst/n)
(dst/'system.al').write_text((src/'system.al').read_text(encoding='utf-8').replace(src.as_posix(),dst.as_posix()),encoding='utf-8')
print('Independent scope candidate prepared')
