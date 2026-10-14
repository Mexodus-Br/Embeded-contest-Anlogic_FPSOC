"""Import sealed PL DMA delivery and connect the final generated PS exactly."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];W=ROOT/'bsp/work/telemetry_soc_prj';PL=ROOT/'pl_dma';D=W/'gp'
subprocess.run([sys.executable,str(ROOT/'bsp/telemetry/verify_input.py')],check=True,cwd=ROOT)
release=json.loads((ROOT/'pl_rs485/evidence/identity_telemetry.json').read_text())
D.mkdir(exist_ok=True)
header=(ROOT/'pl_interface/generated/interface_defs.vh').read_text(encoding='utf-8')
sources=list(sorted((PL/'rtl').glob('*.v')))+list(sorted((ROOT/'pl_motion/rtl').glob('*.v')))+list(sorted((ROOT/'pl_rs485/rtl').glob('*.v')))
names=[]
for src in sources:
    text=src.read_text(encoding='utf-8');key=src.relative_to(ROOT).as_posix()
    if key in release['source_sha256']:
        assert hashlib.sha256(src.read_bytes()).hexdigest()==release['source_sha256'][key],key
    else:
        gpio=json.loads((ROOT/'pl_motion/GPIO_RELEASE.json').read_text(encoding='utf-8'))
        assert hashlib.sha256(src.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==gpio['source_sha256_lf'][key],key
    text=text.replace('`include "generated/interface_defs.vh"',header)
    text=re.sub(r'`include "([^"]+)"',lambda m:(ROOT/'pl_rs485/generated'/m[1]).read_text(encoding='utf-8'),text)
    (D/src.name).write_text(text,encoding='utf-8');names.append(src.name)
ip=json.loads((PL/'build/ip/manifest.json').read_text())
for record in list(ip['libraries'].values()):
    src=Path(record['staged']);assert hashlib.sha256(src.read_bytes()).hexdigest()==record['sha256']
    shutil.copyfile(src,D/src.name);names.append(src.name)
for name,record in ip['headers'].items():
    src=PL/'build/ip'/name;assert hashlib.sha256(src.read_bytes()).hexdigest()==record['sha256']
    shutil.copyfile(src,D/name)
ps=W/'system/ip/system_ARM_Processor_System_0';rawfile=ps/'RTL/ARM_Processor_System_f6ddd1d59490.v'
raw=rawfile.read_text();params=dict(re.findall(r'parameter\s+(\w+)\s*=\s*(\d+)',raw));ports={}
for direction,expr,name in re.findall(r'^\s*(input|output)\s+(?:\[([^]]+):0\]\s*)?(\w+)\s*[,)]',raw,re.M):
    for key,value in params.items():expr=expr.replace(key,value)
    assert not re.search(r'[^0-9+*/() -]',expr),expr
    ports[name]=(direction,int(eval(expr,{'__builtins__':{}}))+1 if expr else 1)
hp_audit=json.loads((PL/'HP0_PORTS.json').read_text())['ports']
for name,record in hp_audit.items():assert ports[name]==(record['direction'],record['width']),name
for name,record in hp_audit.items():
    assert ports[name.replace('hp0','hp1')]==(record['direction'],record['width']),name
assert 'master_gp0_axi_wid' not in ports and 'slave_hp0_axi_wid' not in ports and 'slave_hp1_axi_wid' not in ports
assert ports['f2p_irq']==('input',16) and ports['p2f_rst0_n']==('output',1)
cfg=json.loads((ROOT/'pl_motion/scope_test/CONFIG.json').read_text(encoding='utf-8'))
lines=['// Final BSP actual PS + sealed GP/DMA shared control and HP0.',
       'module system_wrapper(input wire clk_100m,rs485_rx, output wire rs485_tx,rs485_de, a0_step,a0_dir,a0_en,a1_step,a1_dir,a1_en,a2_step,a2_dir,a2_en);','wire [3:0] motion_step,motion_dir,motion_en;wire gp0_aclk,hp0_aclk,hp1_aclk,ps_rst_n,control_rst_n,unused_p2f_clk0; wire [15:0] f2p_irq;']
pscon=['.f2p_irq(f2p_irq)','.p2f_rst0_n(ps_rst_n)','.p2f_clk0(unused_p2f_clk0)']
plcon=['.rs485_rx(rs485_rx)','.rs485_tx(rs485_tx)','.rs485_de(rs485_de)','.hp1_aclk(hp1_aclk)','.motion_step(motion_step)','.motion_dir(motion_dir)','.motion_en(motion_en)','.clk_100m(clk_100m)','.arst_n(ps_rst_n)','.gp0_aclk(gp0_aclk)','.hp0_aclk(hp0_aclk)','.control_rst_n(control_rst_n)','.f2p_irq(f2p_irq)']
for prefix,kind in [('master_gp0_axi_','gp'),('slave_hp0_axi_','hp'),('slave_hp1_axi_','hp1')]:
    for name,(direction,width) in ports.items():
        if not name.startswith(prefix):continue
        tail=name[len(prefix):]
        if tail=='aclk':pscon.append(f'.{name}('+('hp1_aclk' if kind=='hp1' else kind+'0_aclk')+')');continue
        signal=kind+'_'+tail
        lines.append('wire '+(f'[{width-1}:0] ' if width>1 else '')+signal+';')
        pscon.append(f'.{name}({signal})');plcon.append(f'.{signal}({signal})')
custom=(ps/'system_ARM_Processor_System_0.v').read_text()
param_payload=re.search(r'ARM_Processor_System_f6ddd1d59490\s*#\((.*?)\)\s*ARM_Processor_System',custom,re.S)
assert param_payload
for p in cfg['pins']:
    axis=int(p['port'][1]);signal=p['port'].split('_')[1];lines.append('assign '+p['port']+'=motion_'+signal+'['+str(axis)+'];')
timing=','.join('.'+n+"({64'd0,{3{64'd500}}})" for n in ['STEP_HIGH_CYCLES','STEP_LOW_CYCLES','DIR_SETUP_CYCLES','DIR_HOLD_CYCLES','EN_SETUP_CYCLES','EN_DISABLE_CYCLES'])
timing+=",.MAX_STEP_HZ({64'd0,{3{64'd100000}}}),.EN_ACTIVE_LEVEL(4'd15),.FIFO_DEPTH(64),.PLAN_DEPTH(8),.START_MIN_POINTS(32)"
lines+=['ARM_Processor_System_f6ddd1d59490 #('+param_payload[1]+') ps(\n'+',\n'.join(pscon)+');',
        'rs485_gp_ps_top #('+timing+') control(\n'+',\n'.join(plcon)+');','endmodule']
(W/'system/hdl/system_wrapper.v').write_text('\n'.join(lines)+'\n')
properties=(ps/'system_ARM_Processor_System_0.tcl').read_text();old='ARM_Processor_System_f6ddd1d59490_Inst/DR1_PHY_PROCESSOR_SYSTEM_Inst'
assert properties.count(old)==4
(D/'ps-generated-properties.tcl').write_text(properties.replace(old,'ps/DR1_PHY_PROCESSOR_SYSTEM_Inst'))
(D/'gp.adc').write_bytes((ROOT/'pl_motion/scope_test/generated/pins.adc').read_bytes()+b'\n# Board RS485 pins: hardware manual, explicitly accepted 2026-10-14.\nset_pin_assignment { rs485_tx } { LOCATION = L17; IOSTANDARD = LVCMOS33; }\nset_pin_assignment { rs485_rx } { LOCATION = N16; IOSTANDARD = LVCMOS33; }\nset_pin_assignment { rs485_de } { LOCATION = N15; IOSTANDARD = LVCMOS33; }\n')
(D/'gp.sdc').write_bytes((ROOT/'pl_motion/scope_test/generated/timing.sdc').read_bytes())
project=(W/'system.al').read_text();tree=ET.fromstring(project.replace('UsedInP&R','UsedInP&amp;R'));vlog=tree.find('Source_Files/Verilog')
for f in list(vlog):
    if f.get('Path','').startswith('gp/'):vlog.remove(f)
for name in names:
    f=ET.SubElement(vlog,'File',{'Path':'gp/'+name});info=ET.SubElement(f,'FileInfo')
    for key,value in [('UsedInSyn','true'),('UsedInP&R','true'),('BelongTo','design_1'),('CompileOrder','3')]:ET.SubElement(info,'Attr',{'Name':key,'Val':value})
(W/'system.al').write_bytes(ET.tostring(tree,encoding='utf-8',xml_declaration=True).replace(b'UsedInP&amp;R',b'UsedInP&R'))
proof={'status':'SIX_WINDOW_GPIO_TELEMETRY_CONNECTED_NOT_YET_BUILT','source_commit':'f447116','schema_sha256':hashlib.sha256((ROOT/'pl_interface/schema.json').read_bytes()).hexdigest(),'ps_ports':ports,'raw_ps_sha256':hashlib.sha256(rawfile.read_bytes()).hexdigest(),'gp_window':'0x80400000/4KiB','dma_window':'0x80500000/4KiB','irq':'bit0..6 SPI82..88 level-high','clock':'H16 100MHz GP0/HP0/HP1/PL common; native PS properties mapped','reset':'startup p2f_rst0_n; DMA-only soft reset preserves GP epoch','ip':ip,'motor':'scope only; GPIO test 500-cycle guards 100kHz M4 disabled raw64/prepared8/START32; not product parameters','motion_window':'0x80600000/4KiB','rs485_window':'0x80700000/4KiB','cache_window':'0x80800000/4KiB','independent_s2mm_window':'0x80900000/4KiB','rs485_pins':'TX L17 / RX N16 / DE+RE_N N15, BANK33 LVCMOS33, hardware manual accepted 2026-10-14; slave/electrical timing pending','not_deployable':True}
(W/'connections.json').write_text(json.dumps(proof,indent=2)+'\n');print('Final GP/DMA PS connections audited:',W)
