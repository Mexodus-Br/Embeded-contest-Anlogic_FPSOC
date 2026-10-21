"""Review matched HPF and publish only the isolated motor bench packaging gate."""
from pathlib import Path
import zipfile,re,json,hashlib
R=Path(__file__).resolve().parents[2];W=R/'bsp/work/motor3125_soc_prj';D=R/'bsp/motor_test'
review=json.loads((W/'review.json').read_text())
assert review['timing_pass'] and not review['critical']
check=(W/'route.check').read_text()
issues=dict((name,int(count)) for name,count in re.findall(r'\d+\. checking ([^\n(]+)\((\d+)\)',check))
assert len(issues)>=14,'Unrecognized check_timing report'
assert all(count==0 for name,count in issues.items() if name!='dummy node'),issues
assert issues.get('dummy node')==2,issues
assert set(re.findall(r'DummyNode in Model:\s*(\S+)',check))=={'DR1_PHY_ERAM','DR1_PHY_LSLICE'}
# Verify protected IP directly corresponding to the compiled candidate.
ip=json.loads((R/'pl_dma/build/ip/manifest.json').read_text())
for record in ip['libraries'].values():
    p=W/'gp'/Path(record['staged']).name
    assert hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256'],p.name
assert 'PASS MOTOR3125' in (W/'simulation/run.log').read_text()
assert 'PASS scope_gpio' in (W/'real_dma_attempt2/simulation.log').read_text()
def macros(t):return dict(re.findall(r'^#define\s+(\w+)\s+(.+)$',t,re.M))
with zipfile.ZipFile(W/'system.hpf') as z:
    assert z.read('HPFs/system.bit')==(W/'system.bit').read_bytes()
    h=z.read('HPFs/soc_plat.h').decode();new=macros(h)
with zipfile.ZipFile(R/'bsp/work/scope_soc_prj/system.hpf') as z:old=macros(z.read('HPFs/soc_plat.h').decode())
assert re.search(r'DDRC_IO_VOL\s+1.35',h)
metadata={'BITSTREAM_GENERATE_TIME','HPF_EXPORT_TIME'}
assert {k:v for k,v in old.items() if k not in metadata}=={k:v for k,v in new.items() if k not in metadata},'PS DDR/storage/clocks/pinmux property drift'
assert (W/'gp/ps-generated-properties.tcl').read_bytes()==(R/'bsp/work/scope_soc_prj/gp/ps-generated-properties.tcl').read_bytes()
cfg=json.loads((D/'CONFIG.json').read_text())
result=dict(review,status='REVIEWED_FOR_ISOLATED_MOTION_BUILD',check_timing=issues,
 hpf_sha256=hashlib.sha256((W/'system.hpf').read_bytes()).hexdigest(),
 bitstream_sha256=hashlib.sha256((W/'system.bit').read_bytes()).hexdigest(),
 kernel_config_sha256='81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1',
 profile=cfg,ps_macros_unchanged=True,excluded_timestamp_macros={k:new[k].strip() for k in sorted(metadata)},pl_gpio_source='df17b4e',bsp_source='db5f75c',
 physical_speed_confirmed=False,driver_timing_validated=False,sd_written=False,
 board_motion_executed=False,scope='minimal HP0/MOT2/J12 motor pulse comparison; excludes independent HP1/RS485/safety HOME',
 io_constraint='original asynchronous GPIO 20ns budget; not receiver synchronization qualification')
(D/'integration.review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
