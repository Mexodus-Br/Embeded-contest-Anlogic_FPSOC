"""Import sealed PL DMA delivery and connect the final generated PS exactly."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];W=ROOT/'bsp/work/dma_soc_prj';PL=ROOT/'pl_dma';D=W/'gp'
subprocess.run([sys.executable,str(PL/'verify_delivery.py')],check=True,cwd=ROOT)
release=json.loads((PL/'RELEASE.json').read_text())
D.mkdir(exist_ok=True)
header=(ROOT/'pl_interface/generated/interface_defs.vh').read_text(encoding='utf-8')
sources=list(sorted((PL/'rtl').glob('*.v')))+[ROOT/'pl_motion/rtl/gp_control_regs.v',ROOT/'pl_motion/rtl/gp_ps_write_adapter.v']
names=[]
for src in sources:
    text=src.read_text(encoding='utf-8');key=src.relative_to(ROOT).as_posix()
    assert hashlib.sha256(text.encode()).hexdigest()==release['source_sha256_lf'][key],key
    (D/src.name).write_text(text.replace('`include "generated/interface_defs.vh"',header),encoding='utf-8');names.append(src.name)
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
assert 'master_gp0_axi_wid' not in ports and 'slave_hp0_axi_wid' not in ports
assert ports['f2p_irq']==('input',16) and ports['p2f_rst0_n']==('output',1)
lines=['// Final BSP actual PS + sealed GP/DMA shared control and HP0.',
       'module system_wrapper(input wire clk_100m);','wire gp0_aclk,hp0_aclk,ps_rst_n,control_rst_n,unused_p2f_clk0; wire [15:0] f2p_irq;']
pscon=['.f2p_irq(f2p_irq)','.p2f_rst0_n(ps_rst_n)','.p2f_clk0(unused_p2f_clk0)']
plcon=['.clk_100m(clk_100m)','.arst_n(ps_rst_n)','.gp0_aclk(gp0_aclk)','.hp0_aclk(hp0_aclk)','.control_rst_n(control_rst_n)','.f2p_irq(f2p_irq)']
for prefix,kind in [('master_gp0_axi_','gp'),('slave_hp0_axi_','hp')]:
    for name,(direction,width) in ports.items():
        if not name.startswith(prefix):continue
        tail=name[len(prefix):]
        if tail=='aclk':pscon.append(f'.{name}({kind}0_aclk)');continue
        signal=kind+'_'+tail
        lines.append('wire '+(f'[{width-1}:0] ' if width>1 else '')+signal+';')
        pscon.append(f'.{name}({signal})');plcon.append(f'.{signal}({signal})')
custom=(ps/'system_ARM_Processor_System_0.v').read_text()
param_payload=re.search(r'ARM_Processor_System_f6ddd1d59490\s*#\((.*?)\)\s*ARM_Processor_System',custom,re.S)
assert param_payload
lines+=['ARM_Processor_System_f6ddd1d59490 #('+param_payload[1]+') ps(\n'+',\n'.join(pscon)+');',
        'dma_gp_ps_top control(\n'+',\n'.join(plcon)+');','endmodule']
(W/'system/hdl/system_wrapper.v').write_text('\n'.join(lines)+'\n')
properties=(ps/'system_ARM_Processor_System_0.tcl').read_text();old='ARM_Processor_System_f6ddd1d59490_Inst/DR1_PHY_PROCESSOR_SYSTEM_Inst'
assert properties.count(old)==4
(D/'ps-generated-properties.tcl').write_text(properties.replace(old,'ps/DR1_PHY_PROCESSOR_SYSTEM_Inst'))
(D/'gp.adc').write_text('set_pin_assignment { clk_100m } { LOCATION = H16; IOSTANDARD = LVCMOS33; }\n')
(D/'gp.sdc').write_text('create_clock -name gp_clk -period 10.000 [get_ports clk_100m]\n')
project=(W/'system.al').read_text();tree=ET.fromstring(project.replace('UsedInP&R','UsedInP&amp;R'));vlog=tree.find('Source_Files/Verilog')
for f in list(vlog):
    if f.get('Path','').startswith('gp/'):vlog.remove(f)
for name in names:
    f=ET.SubElement(vlog,'File',{'Path':'gp/'+name});info=ET.SubElement(f,'FileInfo')
    for key,value in [('UsedInSyn','true'),('UsedInP&R','true'),('BelongTo','design_1'),('CompileOrder','3')]:ET.SubElement(info,'Attr',{'Name':key,'Val':value})
(W/'system.al').write_bytes(ET.tostring(tree,encoding='utf-8',xml_declaration=True).replace(b'UsedInP&amp;R',b'UsedInP&R'))
proof={'status':'SEALED_GP_DMA_CONNECTED_NOT_YET_BUILT','source_commit':release['source_commit'],'schema_sha256':hashlib.sha256((ROOT/'pl_interface/schema.json').read_bytes()).hexdigest(),'ps_ports':ports,'raw_ps_sha256':hashlib.sha256(rawfile.read_bytes()).hexdigest(),'gp_window':'0x80400000/4KiB','dma_window':'0x80500000/4KiB','irq':'bit0/1/2 SPI82/83/84 level-high','clock':'H16 100MHz GP0/HP0/PL common; native PS properties mapped','reset':'startup p2f_rst0_n; DMA-only soft reset preserves GP epoch','ip':ip,'motor':'not connected'}
(W/'connections.json').write_text(json.dumps(proof,indent=2)+'\n');print('Final GP/DMA PS connections audited:',W)
