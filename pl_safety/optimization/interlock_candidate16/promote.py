"""Promote only the nine isolated and unit-proven candidate16 files."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
def main():
 assert json.loads((HERE/'unit_r1/result.json').read_text())['passed']
 paths=json.loads((HERE/'sources_r1/scope.json').read_text())['paths']
 out=HERE/'before';out.mkdir(exist_ok=False)
 for p in paths:
  target=out/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,target)
 for p in paths:shutil.copyfile(HERE/'sources_r1'/p,ROOT/p)
 print('PASS promoted candidate16',len(paths),'no hashes')
if __name__=='__main__':main()
