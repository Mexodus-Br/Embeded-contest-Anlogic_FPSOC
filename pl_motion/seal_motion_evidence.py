"""Package raw evidence bytes; no generated databases or protected IP."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'pl_dma/reports/motion_20261013';OUT.mkdir(parents=True,exist_ok=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[]
for folder,patterns in [('pl_dma/build/motion_soc_final',['run.log','gate.timing','place.timing','route.timing','route.area','route.check','clock.sdc','clock.adc','ps-properties.tcl','top.v','run.tcl','summary.json']),
 ('pl_dma/build/questa_motion',['*.log','tb_motion_dma.v','dut_bindings.vh','tb_gp_motion_probe.v']),
 ('pl_motion/build/motion_integration',['*.log']),('pl_motion/build/motion_regressions',['*.log'])]:
 for pattern in patterns:files.extend((ROOT/folder).glob(pattern))
files.extend(p for p in OUT.glob('failure_r*/*') if p.is_file())
for name in ['pl_motion/MOTION_SIM_RESULTS.json','pl_motion/MOTION_REGRESSION_RESULTS.json','pl_dma/MOTION_DMA_SIM_RESULTS.json','pl_dma/MOTION_SOC_RESULTS.json','pl_dma/MOTION_ADDRESS_MAP.json']:files.append(ROOT/name)
entries={p.relative_to(ROOT).as_posix():{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(set(files))}
with zipfile.ZipFile(OUT/'evidence.zip','w',zipfile.ZIP_DEFLATED) as archive:
 for name in entries:archive.write(ROOT/name,name)
index={'status':'RAW_BYTES_ARCHIVED','archive_sha256':digest(OUT/'evidence.zip'),'files':entries,'limits':'Build databases and protected vendor libraries are reproducible local outputs, not archived. No board validation is claimed.'}
(OUT/'index.json').write_text(json.dumps(index,indent=2)+'\n');print('sealed',len(entries),'evidence items')
