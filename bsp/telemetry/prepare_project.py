"""Clone only the scope board's project/PS configuration; keep prior release."""
from pathlib import Path
import shutil
R=Path(__file__).resolve().parents[2];old=R/'bsp/work/scope_soc_prj';new=R/'bsp/work/telemetry_soc_prj'
assert not new.exists(),'Never overwrite previous attempts'
new.mkdir();shutil.copytree(old/'system',new/'system');shutil.copyfile(old/'system.al',new/'system.al')
print('Separate actual BSP project prepared:',new)
