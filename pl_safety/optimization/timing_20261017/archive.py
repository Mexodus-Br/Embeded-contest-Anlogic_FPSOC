"""Use the original full-top archiver with explicitly named fresh test identities."""
import sys
from pathlib import Path
E=Path(__file__).resolve().parent;D=E.parents[1]
assert '--test-prefix' in sys.argv
ix=sys.argv.index('--test-prefix');prefix=sys.argv[ix+1];del sys.argv[ix:ix+2]
assert prefix.replace('_','').isalnum()
source=(D/'archive_reports.py').read_text()
source=source.replace("'parent_place_run.log','parent_full_run.tcl'","'nominal_place.sdc','nominal_route.sdc','parent_full_run.log','parent_full_inputs.json','optimization_margin.sdc','place_closure_margin.timing','parent_place_run.log','parent_full_run.tcl'")
replacements={n:prefix+'_'+suffix for n,suffix in [('predecode_units1','units1'),('predecode_phases1','phases1'),('overflow_frozen1','overflow1'),('predecode_real1','real1'),('timing_regress1','regress1'),('predecode_resource1','resource1')]}
if (D.parent/'pl_motion/rtl/motion_stream_rx.v').read_bytes().replace(b'\r\n',b'\n')!=(E/'baseline/motion_stream_rx.v').read_bytes().replace(b'\r\n',b'\n'):
 replacements['rxcarry_equivalence1']=prefix+'_equivalence1'
for old,new in replacements.items():source=source.replace(old,new)
exec(compile(source,str(D/'archive_reports.py'),'exec'),{'__file__':str(D/'archive_reports.py'),'__name__':'__main__'})
