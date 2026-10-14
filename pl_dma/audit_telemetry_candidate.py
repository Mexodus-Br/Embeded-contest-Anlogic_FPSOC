"""Pre-contract HP1/resource audit. Isolated PS copy; BSP and old audits untouched."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
from prepare_ip import ROOT,TD,digest

def ports(text):
    params=dict(re.findall(r'parameter\s+(\w+)\s*=\s*(\d+)',text));out={}
    for d,w,n in re.findall(r'^\s*(input|output)\s+(?:\[([^]]+):0\]\s*)?(\w+)\s*[,)]',text,re.M):
        expr=w
        for key,value in params.items():expr=expr.replace(key,value)
        if re.search(r'[^0-9+*/() -]',expr):raise RuntimeError('unknown width '+expr)
        out[n]={'direction':d,'width':int(eval(expr,{'__builtins__':{}}))+1 if expr else 1}
    return out

def resources():
    result=[]
    candidates=[(0x80800000,4096,5,87),(0x80900000,4096,6,88)]
    for p in sorted((ROOT.parent/'bsp/artifacts').glob('*/debug/*expanded.dts')):
        t=p.read_text(encoding='utf-8');ranges=[];irq=[]
        for m in re.finditer(r'\breg\s*=\s*([^;]+);',t):
            v=[int(x,0) for x in re.findall(r'\b(?:0[xX][0-9a-fA-F]+|[0-9]+)\b',m[1])]
            if len(v)%4:continue
            for k in range(0,len(v),4):
                a=v[k]<<32|v[k+1];n=v[k+2]<<32|v[k+3]
                if a>=0x60000000 and n:ranges.append((a,n))
        for m in re.finditer(r'\binterrupts\s*=\s*([^;]+);',t):
            v=[int(x,0) for x in re.findall(r'\b(?:0[xX][0-9a-fA-F]+|[0-9]+)\b',m[1])]
            for i in range(0,len(v)-2,3):
                if v[i]==0 and v[i+1] in [87,88]:irq.append(v[i:i+3])
        overlap=[{'base':b,'conflicts':[(a,n) for a,n in ranges if max(a,b)<min(a+n,b+s)]} for b,s,_,_ in candidates]
        if irq or any(x['conflicts'] for x in overlap):raise RuntimeError('candidate conflicts '+str(p))
        result.append({'source':str(p.relative_to(ROOT.parent)),'sha256':digest(p),'overlaps':overlap,'spi_87_88_matches':irq,'numeric_cpu_ranges':len(ranges)})
    if not result:raise RuntimeError('no current expanded DTS sources')
    return {'candidates':[{'base':b,'size':s,'irq_line':line,'spi':spi,'intid':spi+32} for b,s,line,spi in candidates],
      'sources':result,'limits':'Numeric four-cell CPU ranges including disabled resources, and direct three-cell SPI matching only. Final HPF/DT/bus translations/GIC routing still require BSP audit.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',default='');a=ap.parse_args()
    if a.tag and not re.fullmatch('[A-Za-z0-9_-]+',a.tag):raise ValueError('invalid audit tag')
    suffix='_'+a.tag if a.tag else ''
    source=ROOT.parent/'bsp/work/gp_soc_prj/system/ip/system_ARM_Processor_System_0'
    b=ROOT/('build/ps_telemetry_candidate'+suffix)
    e=ROOT/('reports/telemetry_candidate'+suffix)
    if b.exists() or e.exists():raise RuntimeError('audit destination exists; choose a new --tag')
    b.mkdir(parents=True);e.mkdir(parents=True)
    names=['Design.xml','DesignConfiguration.xml','system_ARM_Processor_System_0.xml','.m_params_system_ARM_Processor_System_0.txt','.ports_system_ARM_Processor_System_0.txt']
    before={n:digest(source/n) for n in names}
    for n in names:shutil.copyfile(source/n,b/n)
    p=b/'Design.xml';original=p.read_text(encoding='utf-8');text=original
    for index in [0,1]:
        text,count=re.subn(r'(referenceId="Slave_AXI_HP'+str(index)+r'_Interface">)[01](<)',r'\g<1>1\2',text)
        if count!=1:raise RuntimeError('HP configuration not unique')
    p.write_text(text,encoding='utf-8')
    script=f'''cd {{{b.as_posix()}}}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
xmlipgen -usernamed_file {{{(b/'system_ARM_Processor_System_0.xml').as_posix()}}} -design_file {{{p.as_posix()}}} -designConfig_file {{{(b/'DesignConfiguration.xml').as_posix()}}} -component_file {{{(TD/'ip/depot/ARM_Processor_System_F9F0D0P0_1.0/Component.xml').as_posix()}}} -mode behavior -package DR1M90GEG400
puts TELEMETRY_HP1_AUDIT_COMPLETE
exit
'''
    (b/'generate.tcl').write_text(script)
    r=subprocess.run([str(TD/'bin/td_commands_prompt.exe'),(b/'generate.tcl').as_posix()],cwd=b,capture_output=True,text=True,timeout=120)
    log=r.stdout+r.stderr;(e/'generate.log').write_text(log,encoding='utf-8')
    if r.returncode or 'TELEMETRY_HP1_AUDIT_COMPLETE' not in log or 'ERROR:' in log:raise RuntimeError('vendor PS generation failed; log retained')
    raw=list((b/'RTL').glob('ARM_Processor_System_*.v'))
    if len(raw)!=1:raise RuntimeError('PS raw source not unique')
    parsed=ports(raw[0].read_text(encoding='utf-8'));hp={}
    widths={'araddr':33,'awaddr':33,'arid':6,'awid':6,'bid':6,'rid':6,'arlen':4,'awlen':4,'arsize':2,'awsize':2,'arlock':1,'awlock':1,'wdata':64,'rdata':64,'wstrb':8,'aclk':1}
    for index in [0,1]:
        hp[str(index)]={n:v for n,v in parsed.items() if n.startswith('slave_hp'+str(index)+'_axi_')}
        for suffix,w in widths.items():
            if hp[str(index)].get('slave_hp'+str(index)+'_axi_'+suffix,{}).get('width')!=w:raise RuntimeError('actual HP width mismatch')
    old=json.loads((ROOT/'HP0_PORTS.json').read_text())['ports']
    if {n:{k:v[k] for k in ['direction','width']} for n,v in old.items()}!=hp['0']:raise RuntimeError('HP0 port interface changed')
    if parsed.get('master_gp0_axi_awaddr',{}).get('width')!=33 or parsed.get('f2p_irq',{}).get('width')!=16:raise RuntimeError('GP/IRQ interface changed')
    if before!={n:digest(source/n) for n in names}:raise RuntimeError('BSP modified')
    q=json.loads((ROOT.parent/'pl_interface/schema.json').read_text(encoding='utf-8'))['dma_loopback_profiles']['dma_loopback_v1']['parameters'].copy()
    q['AL_INCLUDE_MM2S']=0;q['AL_INCLUDE_S2MM']=1
    result={'status':'ACTUAL_GENERATED_HP0_HP1_PORTS_AUDITED','board_verified':False,'contract_confirmed':False,
      'source_files_sha256':before,'generation':'vendor xmlipgen in isolated copy, HP0+HP1 only; existing PS source/property values preserved',
      'generated_raw':str(raw[0]),'raw_sha256':digest(raw[0]),'configuration_sha256':digest(p),'ports':hp,
      'hp0_interface_preserved':True,'gp0_a33_preserved':True,'irq_width':16,
      'wid_present':{n:any(k.endswith('_wid') for k in v) for n,v in hp.items()},
      'public_hp_reset_ports':[n for n in parsed if 'hp' in n and ('reset' in n or 'rst' in n)],
      'proposed_dma_parameters':q,'vendor_dma_sha256':digest(TD/'ip/depot/AXI_DMA_1.0/AXI_DMA/RTL/axi_dma.v'),
      'vendor_component_sha256':digest(TD/'ip/depot/AXI_DMA_1.0/Component.xml'),
      'resource_audit':resources(),'clock_proposal':'H16 100MHz shared source for GP, both HP ports and both controllers; ASYNC=0. Must verify GEN_PL_HP1 clock in actual final STA.',
      'limits':'Port/configuration audit only; not HP1 DDR, S2MM-only IP, reset isolation or timing verification. Independent HP ports still share PS/DDR fabric. No arbitration between PL masters because one per HP.'}
    (e/'audit.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    for n in ['generate.tcl','Design.xml','DesignConfiguration.xml']:shutil.copyfile(b/n,e/n)
    print(json.dumps({'status':result['status'],'hp_ports':{k:len(v) for k,v in hp.items()},'hp0_preserved':True,'dts_sources_audited':len(result['resource_audit']['sources']),'bsp_sources_unchanged':True,'raw_sha256':digest(raw[0])},indent=2))
if __name__=='__main__':main()
