"""Functional-port OOC gate export; separate from common scan resource matrix."""
import argparse,re
from experiment import E,run_td

def main(tag,source):
    b=E/'build'/tag;b.mkdir(parents=True,exist_ok=False)
    s=(E/'build'/source/'run.tcl').read_text()
    s=re.sub(r'^cd .*',f'cd {{{b.as_posix()}}}',s,count=1,flags=re.M)
    s=s.replace('get_num_thread\n','get_num_thread\nset_param flow ooc_flow on\n',1)
    s=s.replace('elaborate -top telem_probe','elaborate -top telemetry_dma_lite_top')
    s=s.replace('read_sdc clock.sdc','create_clock -name telem_clk -period 10 [get_ports clk_100m]')
    assert run_td(b,s)==0
    log=(b/'run.log').read_text();assert 'EXPERIMENT_COMPLETE' in log and ' ERROR:' not in log
    print('FUNCTIONAL_GATE_EXPORTED',tag)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('tag');ap.add_argument('source');a=ap.parse_args();main(a.tag,a.source)
