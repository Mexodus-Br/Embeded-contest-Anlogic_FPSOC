"""Run unchanged original regression cases against explicitly selected RTL."""
import argparse,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
 c=Path(a.candidate).resolve();original=R/'pl_safety/tests/interlock_regressions.py';s=original.read_text()
 old="source = list((ROOT / 'pl_motion/rtl').glob('*.v')) + list((ROOT / 'pl_rs485/rtl').glob('*.v'))"
 assert s.count(old)==1;s=s.replace(old,old+'\n    source = [Path('+repr(c.as_posix())+')/f.name if (Path('+repr(c.as_posix())+')/f.name).is_file() else f for f in source]')
 previous=sys.argv;sys.argv=[str(original),'--tag',a.tag]
 try:exec(compile(s,str(original),'exec'),{'__file__':str(original),'__name__':'__main__'})
 finally:sys.argv=previous
if __name__=='__main__':main()
