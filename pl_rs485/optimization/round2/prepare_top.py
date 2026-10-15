"""Preserve round1 preparation; extend only the round2 authorized RTL identity."""
import sys
from pathlib import Path
E=Path(__file__).resolve().parent;O=E.parent
source=(O/'prepare_top.py').read_text(encoding='utf-8')
source=source.replace("names=['pl_rs485/rtl/rs485_latest_cache.v','pl_rs485/rtl/rs485_telemetry.v']", "names=['pl_rs485/rtl/'+n+'.v' for n in ['rs485_latest_cache','rs485_telemetry','rs485_multirate','rs485_gp_regs','rs485_telem_regs']]")
source=source.replace("'baseline_commit':'7681c69','tag':a.tag", "'baseline_commit':'7681c69','optimization_round':2,'parent_candidate_commit':'49e8ac6','tag':a.tag")
if '--baseline' in sys.argv:raise SystemExit('Use preserved round1 --baseline replay; round2 inputs are a new candidate')
exec(compile(source,str(O/'prepare_top.py'),'exec'),{'__file__':str(O/'prepare_top.py'),'__name__':'__main__'})
