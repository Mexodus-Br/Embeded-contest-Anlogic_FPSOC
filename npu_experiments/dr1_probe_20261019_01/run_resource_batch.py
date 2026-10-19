from pathlib import Path
import time
from run_resources import ROOT, synth
for _ in range(120):
 if 'NPU_SYNTH_DONE' in (ROOT/'native_full/synth.log').read_text(errors='replace'):break
 time.sleep(5)
else:raise RuntimeError('Reference native synthesis not complete; no other TD job launched')
for name in ['whole_no_video','tiny_no_video','mbface_no_video','v3_no_video']:
 print('START',name,flush=True)
 synth(ROOT/('ip_'+name))
 print('DONE',name,flush=True)
