"""Promote only the explicit, unit-proven candidate sources; retain byte backup."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def main():
 assert json.loads((HERE/'unit_r2/result.json').read_text())['passed']
 assert json.loads((ROOT/'pl_safety/optimization/interlock_candidate14/counter_probe_r1/result.json').read_text())['passed']
 src=HERE/'sources_r2';paths=json.loads((src/'scope.json').read_text())['paths']
 backup=HERE/'before';backup.mkdir(exist_ok=False)
 for logical in paths:
  target=backup/logical;target.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(ROOT/logical,target)
 for logical in paths:shutil.copyfile(src/logical,ROOT/logical)
 print('PASS promoted explicit candidate15 sources',len(paths),'no hashes')
if __name__=='__main__':main()
