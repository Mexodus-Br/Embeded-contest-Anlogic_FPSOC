"""Stage untouched current TD protected IP, recording its exact identity."""
import argparse, hashlib, json, re, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TD=Path('D:/Anlogic/TD_Release_2026.1_SP2.200.067')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def profile():return json.loads((ROOT.parent/'pl_interface/schema.json').read_text(encoding='utf-8'))['dma_loopback_profiles']['dma_loopback_v1']
def dma_ports():
    src=TD/'ip/depot/AXI_DMA_1.0/AXI_DMA/RTL/axi_dma.v'
    head=src.read_text(encoding='utf-8').split('`pragma protect')[0]
    q=profile()['parameters'];ports={}
    for d,w,n in re.findall(r'^\s*(input|output)\s*(?:\[([^]]+)\])?\s*(\w+)\s*,?',head,re.M):
        if w:
            hi,lo=w.split(':')
            for key,value in q.items():hi=hi.replace(key,str(value));lo=lo.replace(key,str(value))
            if re.search(r'[^0-9+*/() -]',hi+lo):raise ValueError('unsupported vendor width')
            width=int(eval(hi,{'__builtins__':{}}))-int(eval(lo,{'__builtins__':{}}))+1
        else:width=1
        ports[n]=(d,width)
    if len(ports)!=115:raise ValueError('vendor DMA port inventory changed')
    return ports
def prepare():
    b=ROOT/'build/ip';b.mkdir(parents=True,exist_ok=True)
    libs={'dma':TD/'ip/depot/AXI_DMA_1.0/AXI_DMA/RTL/axi_dma.v',
          'converter':TD/'ip/depot/AXI_Protocol_Converter_1.0/AXI_MM/RTL/axi_protocol_converter_merge.v'}
    manifest={'td_root':str(TD),'schema_sha256':digest(ROOT.parent/'pl_interface/schema.json'),
              'generation':'unmodified installed vendor RTL, directly parameterized; not copied example IP',
              'parameters':profile()['parameters'],'dma_ports':{n:list(v) for n,v in dma_ports().items()},'libraries':{}}
    for n,p in libs.items():
        dest=b/p.name;shutil.copyfile(p,dest)
        manifest['libraries'][n]={'source':str(p),'staged':str(dest),'sha256':digest(p)}
    for n in ['AXI_DMA_1.0','AXI_Protocol_Converter_1.0']:
        manifest[n+'_component_sha256']=digest(TD/'ip/depot'/n/'Component.xml')
    manifest['headers']={}
    for name in ['axi_dma_func_pkg.vh','axi_dma_param_pkg.vh']:
        source=TD/'ip/depot/AXI_DMA_1.0/AXI_DMA/RTL'/name
        shutil.copyfile(source,b/name)
        manifest['headers'][name]={'sha256':digest(source),'source':str(source)}
    (b/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest
if __name__=='__main__':print(json.dumps(prepare(),indent=2))
