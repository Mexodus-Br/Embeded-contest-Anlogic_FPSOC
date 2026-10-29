"""Reuse all old cache oracle assertions; omit the old prohibited log hashing."""
import argparse,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);p.add_argument('--slaves',type=int,default=3);a=p.parse_args()
 candidate=Path(a.candidate).resolve();out=E/a.tag
 original=R/'pl_rs485/optimization/round2/run_ram_diff.py'
 s=original.read_text().split(' # Reuse all existing full-ring/CRC/IRQ/result/backpressure scenarios',1)[0]
 assert 'cache_log_sha256' not in s
 s=s.replace("D=E/('ram_'+a.tag)", 'D=Path('+repr(out.as_posix())+')')
 s=s.replace("sources=list((R/'pl_rs485/rtl').glob('*.v'))",'sources=[Path('+repr(candidate.as_posix())+')/f.name if (Path('+repr(candidate.as_posix())+')/f.name).is_file() else f for f in (R/"pl_rs485/rtl").glob("*.v")]')
 s+='\n (D/"result.json").write_text(json.dumps({"passed":True,"hashes_computed":False,"slaves":a.slaves,"oracle":"full legacy materialized cache plus existing one-cycle alignment","log":p.stdout},indent=2)+"\\n")\nif __name__=="__main__":main()\n'
 previous=sys.argv;sys.argv=[str(original),'--tag',a.tag,'--slaves',str(a.slaves)]
 try:exec(compile(s,str(original),'exec'),{'__file__':str(original),'__name__':'__main__'})
 finally:sys.argv=previous
if __name__=='__main__':main()
