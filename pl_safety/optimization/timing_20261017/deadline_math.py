"""Unsigned circular timeout identity: exhaustive small domains and u64 edges."""
import argparse,json,random
from pathlib import Path
E=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();o=E/a.tag;o.mkdir(exist_ok=False);checks=0
 def equal(now,start,delta,mask):
  end=(start+delta)&mask;wrap=(start+delta)>mask
  return (((now-start)&mask)>=delta)==((now>=end and now<start) if wrap else (now>=end or now<start))
 for bits in range(2,7):
  mask=(1<<bits)-1
  for start in range(1<<bits):
   for delta in range(1<<bits):
    for now in range(1<<bits):assert equal(now,start,delta,mask);checks+=1
 for bits in range(2,9):
  mask=(1<<bits)-1
  for start in range(1<<bits):
   for delta in range(1<<bits):
    end=(start+delta)&mask
    for now in [0,mask,start,(start-1)&mask,end,(end-1)&mask,(end+1)&mask]:assert equal(now,start,delta,mask);checks+=1
 mask=(1<<64)-1;rng=random.Random(20261017)
 for i in range(200000):assert equal(rng.getrandbits(64),rng.getrandbits(64),rng.getrandbits(64),mask);checks+=1
 (o/'result.json').write_text(json.dumps({'passed':True,'checks':checks,'seed':20261017,'exhaustive_bits':[2,3,4,5,6],'boundary_bits':[2,3,4,5,6,7,8],'u64_random':200000},indent=2)+'\n');print('PASS unsigned timeout identity',checks)
if __name__=='__main__':main()
