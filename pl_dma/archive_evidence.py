"""Package exact original report bytes, without normalizing warnings/whitespace."""
import hashlib,json,zipfile
from pathlib import Path
from prepare_ip import ROOT
files=[]
for folder in ['td_shared','soc_reference']:
 for p in (ROOT/'build'/folder).iterdir():
  if p.suffix in ['.timing','.area','.check'] or p.name in ['gate.log','physical.log','run.log','gate.tcl','physical.tcl','run.tcl','ps-properties.tcl','clock.sdc','clock.adc','dma.sdc']:files.append(p)
for folder in ['questa','questa_shared','regressions','ps']:
 files += list((ROOT/'build'/folder).glob('*.log'))
out=ROOT/'reports';out.mkdir(exist_ok=True);index={}
with zipfile.ZipFile(out/'evidence.zip','w',zipfile.ZIP_DEFLATED) as archive:
 for p in sorted(set(files)):
  name=p.relative_to(ROOT/'build').as_posix();data=p.read_bytes();archive.writestr(name,data)
  index[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
(out/'index.json').write_text(json.dumps({'archive_sha256':hashlib.sha256((out/'evidence.zip').read_bytes()).hexdigest(),'files':index},indent=2)+'\n')
print('Packaged',len(index),'exact report/log files, bytes=',(out/'evidence.zip').stat().st_size)
