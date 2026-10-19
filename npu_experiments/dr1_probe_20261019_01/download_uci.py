from pathlib import Path
import urllib.request
p=Path(r'D:\Works\Embedded_contest\dev\npu_experiments\dr1_probe_20261019_01\data');p.mkdir(exist_ok=True)
url='https://archive.ics.uci.edu/static/public/447/condition%2Bmonitoring%2Bof%2Bhydraulic%2Bsystems.zip'
with urllib.request.urlopen(url, timeout=60) as src, (p/'uci447.zip').open('wb') as dst:
 while chunk:=src.read(1024*1024): dst.write(chunk)
print('bytes',(p/'uci447.zip').stat().st_size)
