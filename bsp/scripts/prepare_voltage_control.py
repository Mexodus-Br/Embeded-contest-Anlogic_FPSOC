from pathlib import Path
import shutil
root = Path(__file__).resolve().parents[1] / 'work'
src = root / 'soc_prj'
dst = root / 'voltage-control'
dst.mkdir(exist_ok=True)
shutil.copytree(src / 'system', dst / 'system', dirs_exist_ok=True)
shutil.copy2(src / 'system.bit', dst / 'system.bit')
for p in (dst / 'system').rglob('*.xml'):
    s = p.read_text(encoding='utf-8')
    s = s.replace('referenceId="DDRC_IO_VOL">1.35<', 'referenceId="DDRC_IO_VOL">1.5<')
    p.write_text(s, encoding='utf-8')
print('1.5V counterfactual for generated register comparison only; never deploy')
