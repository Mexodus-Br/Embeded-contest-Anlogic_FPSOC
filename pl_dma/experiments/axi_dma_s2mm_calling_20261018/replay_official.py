"""Replay captured official GUI configuration via installed TD xmlipgen."""
import argparse,shutil,re
from experiment import E,TD,run_td

def main(tag,index):
    name=f'AXI_DMA_{index}'
    source=E/'evidence'/name
    if not source.exists():source=E/'build/al_ip'/name
    b=E/'build'/tag;b.mkdir(parents=True,exist_ok=False)
    for f in ['Design.xml','DesignConfiguration.xml',name+'.xml','.m_params_'+name+'.txt','.ports_'+name+'.txt','.params_'+name+'.txt']:
        shutil.copyfile(source/f,b/f)
    script=f'''cd {{{b.as_posix()}}}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
set_param flow thread 16
get_num_thread
xmlipgen -usernamed_file {{{(b/(name+'.xml')).as_posix()}}} -design_file {{{(b/'Design.xml').as_posix()}}} -designConfig_file {{{(b/'DesignConfiguration.xml').as_posix()}}} -component_file {{{(TD/'ip/depot/AXI_DMA_1.0/Component.xml').as_posix()}}} -mode behavior -package DR1M90GEG400
puts OFFICIAL_REPLAY_COMPLETE
exit
'''
    assert run_td(b,script)==0
    log=(b/'run.log').read_text();assert 'OFFICIAL_REPLAY_COMPLETE' in log and ' ERROR:' not in log
    params=lambda p:dict(re.findall(r'\.(AL_\w+)\((\d+)\)',p.read_text()))
    assert params(b/(name+'.v'))==params(source/(name+'.v'))
    print('OFFICIAL_REPLAY_PARAMETER_MATCH',tag)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('tag');ap.add_argument('--index',type=int,default=1);a=ap.parse_args();main(a.tag,a.index)
