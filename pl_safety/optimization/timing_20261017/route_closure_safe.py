"""Authenticated full-top reroute with an explicit, effective budget lifecycle.

All original route_closure assertions stay enabled. User SDC is rebuilt before
both optimization and final STA, avoiding file-order/cache ambiguity after P&R.
"""
import hashlib,json,sys
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2];D=R/'pl_safety'
sys.path.insert(0,str(D))

def main():
 proof=json.loads((E/'constraint_restore_validation1/result.json').read_text())
 assert proof['passed'] and proof['threads']==16 and proof['extra_setup_uncertainty_ns']==1.25
 for name,h in proof['source_sha256'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==h,('restoration proof changed',name)
 source=(D/'route_closure.py').read_text()
 old="import_db {(source/'place.db').as_posix()}"
 assert source.count(old)==1;source=source.replace(old,'{THREADS_TCL}\n'+old)
 old='{THREADS_TCL}\nread_adc -file gp/gp.adc'
 assert source.count(old)==1;source=source.replace(old,'{THREADS_TCL}\nclear_user_sdc\nread_adc -file gp/gp.adc')
 old='read_sdc restore_nominal.sdc'
 assert source.count(old)==1;source=source.replace(old,'clear_user_sdc\nread_sdc gp/gp.sdc\nread_sdc gp/ps-generated-properties.tcl\nexport_sdc -file nominal_route.sdc')
 exec(compile(source,str(D/'route_closure.py'),'exec'),{'__file__':str(D/'route_closure.py'),'__name__':'__main__'})
 tag=sys.argv[sys.argv.index('--tag')+1];b=D/'build'/tag
 commands=lambda p:[x.strip() for x in p.read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
 assert commands(b/'nominal_route.sdc')==commands(b/'gp/gp.sdc'),'Effective final SDC differs'
 print('PASS actual tightened route and exact original effective final SDC',tag)
if __name__=='__main__':main()
