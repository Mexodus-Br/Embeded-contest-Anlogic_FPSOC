"""Check every imported module CRC against the SAME kernel/provider symbols."""
import json
from pathlib import Path
import subprocess

H=Path(__file__).resolve().parent
T=H.parent
W=Path.home()/'embedded-bsp-wifi-20261018'
O=W/'output/kernel'
S=H/'frozen/software'
symbols={}
for source in [O/'Module.symvers',S/'bsp/telemetry/provider/Module.symvers',T/'build/aic8800/Module.symvers']:
    for line in source.read_text().splitlines():
        v=line.split();symbols[v[1]]=int(v[0],16)
modules=list((T/'build/modules').glob('*.ko'))
modules += [T/'build/aic8800'/n/(n+'.ko') for n in ['aic_load_fw','aic8800_fdrv']]
result={'kernelrelease':(O/'include/config/kernel.release').read_text().strip(),
        'source':str(W/'vendor/sources/linux'),'output':str(O),'modules':{},'hashes_computed':False}
for path in modules:
    vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(path)]).decode().strip()
    assert vermagic.startswith(result['kernelrelease']+' '),(path,vermagic)
    lines=subprocess.check_output(['modprobe','--dump-modversions',str(path)]).decode().splitlines()
    for line in lines:
        crc,name=line.split();assert symbols.get(name)==int(crc,16),(path,name)
    result['modules'][path.name]={'vermagic':vermagic,'imports_crc_matched':len(lines)}
assert len(result['modules'])==7
assert (O/'.config').read_bytes()==(T/'build/kernel.config').read_bytes()
assert (O/'Module.symvers').read_bytes()==(T/'build/Module.symvers').read_bytes()
result['kernel_config_and_symbols_unchanged']=True
(T/'build/software-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS all seven modules: wifi1 vermagic and every imported symbol CRC')
