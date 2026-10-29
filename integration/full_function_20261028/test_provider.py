"""Reuse actual provider-function checks, suppress nonessential source hashing."""
from pathlib import Path
import re,sys
H=Path(__file__).resolve().parent;R=H.parents[1]
p=R/'bsp/telemetry/test_provider.py'
s=p.read_text()
old="D=R/'bsp/telemetry'";assert s.count(old)==1
s=s.replace(old,"D=R/'integration/controlled_v1_20261021/frozen/software/bsp/telemetry'")
s=s.replace("E=R/('bsp/evidence/telemetry-provider-'+a.tag)","E=H/'artifacts'/('provider-'+a.tag)")
s,n=re.subn(r"'provider_sources':\{n:hashlib.sha256.*?\},","'hashes_computed':False,",s,count=1)
assert n==1 and 'hashlib.sha256' not in s
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__','H':H})
