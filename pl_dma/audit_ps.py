"""Generate HP0-enabled actual PS RTL in pl_dma/build only; BSP is read-only."""
import hashlib,json,re,shutil,subprocess
from pathlib import Path
from prepare_ip import ROOT,TD,digest
def main():
    source=ROOT.parent/'bsp/work/gp_soc_prj/system/ip/system_ARM_Processor_System_0'
    b=ROOT/'build/ps';b.mkdir(parents=True,exist_ok=True)
    for n in ['Design.xml','DesignConfiguration.xml','system_ARM_Processor_System_0.xml','.m_params_system_ARM_Processor_System_0.txt','.ports_system_ARM_Processor_System_0.txt']:
        shutil.copyfile(source/n,b/n)
    p=b/'Design.xml';t=p.read_text(encoding='utf-8')
    t,count=re.subn(r'(referenceId="Slave_AXI_HP0_Interface">)0(<)',r'\g<1>1\2',t)
    if count!=1:raise RuntimeError('HP0 source configuration changed')
    p.write_text(t,encoding='utf-8')
    script=f'''cd {{{b.as_posix()}}}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
xmlipgen -usernamed_file {{{(b/'system_ARM_Processor_System_0.xml').as_posix()}}} -design_file {{{p.as_posix()}}} -designConfig_file {{{(b/'DesignConfiguration.xml').as_posix()}}} -component_file {{{(TD/'ip/depot/ARM_Processor_System_F9F0D0P0_1.0/Component.xml').as_posix()}}} -mode behavior -package DR1M90GEG400
puts DMA_PS_GENERATION_COMPLETE
exit
'''
    (b/'generate.tcl').write_text(script)
    r=subprocess.run([str(TD/'bin/td_commands_prompt.exe'),(b/'generate.tcl').as_posix()],cwd=b,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
    (b/'generate.log').write_text(r.stdout)
    if r.returncode or 'DMA_PS_GENERATION_COMPLETE' not in r.stdout or 'ERROR:' in r.stdout:raise RuntimeError('actual PS generation failed')
    raw=list((b/'RTL').glob('ARM_Processor_System_*.v'))
    if len(raw)!=1:raise RuntimeError('expected unique regenerated PS')
    text=raw[0].read_text(encoding='utf-8');ports={}
    parameters=dict(re.findall(r'parameter\s+(\w+)\s*=\s*(\d+)',text))
    for d,w,n in re.findall(r'^\s*(input|output)\s+(?:\[([^]]+):0\]\s*)?(\w+)\s*[,)]',text,re.M):
        expr=w
        for key,value in parameters.items():expr=expr.replace(key,value)
        if re.search(r'[^0-9+*/() -]',expr):raise RuntimeError('unresolved PS width '+expr)
        ports[n]={'direction':d,'width':int(eval(expr,{'__builtins__':{}}))+1 if expr else 1,'expression':w}
    hp={n:v for n,v in ports.items() if n.startswith('slave_hp0_axi_')}
    if not hp:raise RuntimeError('HP0 was not regenerated')
    for suffix,width in {'araddr':33,'awaddr':33,'arid':6,'awid':6,'bid':6,'rid':6,'arlen':4,'awlen':4,'arsize':2,'awsize':2,'arlock':1,'awlock':1,'wdata':64,'rdata':64,'aclk':1}.items():
        if hp.get('slave_hp0_axi_'+suffix,{}).get('width')!=width:raise RuntimeError('HP0 width differs '+suffix)
    result={'status':'ACTUAL_GENERATED_HP0_PORTS_AUDITED','board_verified':False,'source_configuration':str(source/'Design.xml'),
            'source_configuration_sha256':digest(source/'Design.xml'),'generation':'vendor xmlipgen, HP0 enable only in isolated PL build copy',
            'generated_raw':str(raw[0]),'raw_sha256':digest(raw[0]),'ports':hp,
            'wid_present':'slave_hp0_axi_wid' in hp,'gp0_preserved':ports.get('master_gp0_axi_awaddr',{}).get('width')==33,
            'reset_port':ports.get('p2f_rst0_n'),'configuration_sha256':digest(p)}
    (ROOT/'HP0_PORTS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
