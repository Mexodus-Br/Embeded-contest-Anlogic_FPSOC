"""Connect the validated PS-boundary profile to actual generated PS ports."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'bsp/work/gp_soc_prj'
PL = ROOT / 'pl_motion'
sim = json.loads((PL / 'GP_SIM_RESULTS.json').read_text(encoding='utf-8'))
if sim.get('integration') != 'PASS' or sim.get('ps_boundary') != 'PASS':
    raise SystemExit('Real converter and actual PS boundary simulations required')
names = ['gp_control_regs.v', 'gp_control_top.v', 'gp_ps_write_adapter.v', 'gp_ps_control_top.v']
expected = {k.replace('\\', '/'): v for k, v in sim['source_sha256_lf'].items()}
header = (ROOT / 'pl_interface/generated/interface_defs.vh').read_text(encoding='utf-8')
directory = WORK / 'gp'
directory.mkdir(exist_ok=True)
for name in names:
    source = PL / 'rtl' / name
    text = source.read_text(encoding='utf-8')
    if hashlib.sha256(text.encode()).hexdigest() != expected['rtl/' + name]:
        raise SystemExit('PL source changed after simulation: ' + name)
    (directory / name).write_text(text.replace('`include "generated/interface_defs.vh"', header), encoding='utf-8')
vendor = PL / 'build/gp_ip/axi_protocol_converter_merge.v'
manifest = json.loads((PL / 'build/gp_ip/manifest.json').read_text(encoding='utf-8'))
if hashlib.sha256(vendor.read_bytes()).hexdigest() != manifest['library_sha256']:
    raise SystemExit('Vendor converter differs from validated installed source')
shutil.copy2(vendor, directory / vendor.name)
psdir = WORK / 'system/ip/system_ARM_Processor_System_0'
psfile = psdir / 'RTL/ARM_Processor_System_f6ddd1d59490.v'
raw = psfile.read_text(encoding='utf-8')
ports = {}
for m in re.finditer(r'^\s*(input|output)\s+(?:wire\s+)?(?:\[(\d+):0\]\s*)?(\w+)\s*[,)]?\s*$', raw.split(');', 1)[0], re.M):
    direction, width, name = m.groups()
    ports[name] = (direction, int(width)+1 if width else 1)
for name, width in {'awaddr':33, 'araddr':33, 'awid':12, 'bid':12, 'arid':12, 'rid':12,
                    'wdata':32, 'rdata':32, 'awlock':1, 'arlock':1, 'awsize':2, 'arsize':2}.items():
    if ports['master_gp0_axi_' + name][1] != width:
        raise SystemExit('Actual PS width incompatible with validated boundary: ' + name)
if 'master_gp0_axi_wid' in ports or ports.get('f2p_irq') != ('input',16) or ports.get('p2f_rst0_n') != ('output',1):
    raise SystemExit('PS WID/IRQ/reset boundary changed')
signals = {n[len('master_gp0_axi_'):]: w for n, (_, w) in ports.items() if n.startswith('master_gp0_axi_') and not n.endswith('_aclk')}
lines = ['// Generated connection only; validated PL logic is imported unchanged.',
         'module system_wrapper(input wire clk_100m);',
         'wire gp0_aclk, control_rst_n, ps_rst_n, unused_p2f_clk0;', 'wire [15:0] f2p_irq;']
for name, width in signals.items():
    lines.append('wire ' + (f'[{width-1}:0] ' if width != 1 else '') + 'gp_' + name + ';')
custom = (psdir / 'system_ARM_Processor_System_0.v').read_text(encoding='utf-8')
properties = (psdir / 'system_ARM_Processor_System_0.tcl').read_text(encoding='utf-8')
# Instantiating the raw PS bypasses the custom-wrapper IP-scoped constraint
# loader. Retain the generated properties, mapping only the instance path.
old_instance = 'ARM_Processor_System_f6ddd1d59490_Inst/DR1_PHY_PROCESSOR_SYSTEM_Inst'
if properties.count(old_instance) != 4:
    raise SystemExit('Generated PS property payload changed; review before integration')
(directory / 'ps-generated-properties.tcl').write_text(
    properties.replace(old_instance, 'ps/DR1_PHY_PROCESSOR_SYSTEM_Inst'), encoding='utf-8')
params = re.search(r'ARM_Processor_System_f6ddd1d59490\s*#\((.*?)\)\s*ARM_Processor_System', custom, re.S)
if not params:
    raise SystemExit('Generated PS parameter payload not found')
lines.append('ARM_Processor_System_f6ddd1d59490 #(' + params[1] + ') ps (')
ps_connections = ['.master_gp0_axi_aclk(gp0_aclk)', '.f2p_irq(f2p_irq)', '.p2f_rst0_n(ps_rst_n)', '.p2f_clk0(unused_p2f_clk0)']
ps_connections += ['.master_gp0_axi_' + name + '(gp_' + name + ')' for name in signals]
lines.append(',\n'.join(ps_connections) + ');')
lines.append('gp_ps_control_top control (.clk_100m(clk_100m), .arst_n(ps_rst_n), .gp0_aclk(gp0_aclk), .control_rst_n(control_rst_n), .f2p_irq(f2p_irq),')
lines.append(',\n'.join('.gp_' + name + '(gp_' + name + ')' for name in signals) + ');\nendmodule\n')
(WORK / 'system/hdl/system_wrapper.v').write_text('\n'.join(lines), encoding='utf-8')
(directory / 'gp.adc').write_text('set_pin_assignment { clk_100m } { LOCATION = H16; IOSTANDARD = LVCMOS33; }\n', encoding='utf-8')
(directory / 'gp.sdc').write_text('create_clock -name gp_clk -period 10.000 [get_ports clk_100m]\n', encoding='utf-8')
# .al is an ordinary project file; PS IP XML namespace prefixes are preserved.
project_text = (WORK / 'system.al').read_text(encoding='utf-8')
project = ET.ElementTree(ET.fromstring(project_text.replace('UsedInP&R', 'UsedInP&amp;R')))
source_files = project.getroot().find('Source_Files')
vlog = source_files.find('Verilog')
existing = {n.get('Path') for n in vlog.findall('File')}
for name in names + [vendor.name]:
    path = 'gp/' + name
    if path not in existing:
        f = ET.SubElement(vlog, 'File', {'Path': path})
        info = ET.SubElement(f, 'FileInfo')
        for key, value in [('UsedInSyn','true'), ('UsedInP&R','true'), ('BelongTo','design_1'), ('CompileOrder','3')]:
            ET.SubElement(info, 'Attr', {'Name':key,'Val':value})
source_files.find('ADC_FILE/File').set('Path','gp/gp.adc')
if source_files.find('SDC_FILE') is None:
    sdc = ET.SubElement(source_files,'SDC_FILE')
    f = ET.SubElement(sdc,'File',{'Path':'gp/gp.sdc'})
    info = ET.SubElement(f,'FileInfo')
    for key,value in [('UsedInSyn','true'),('UsedInP&R','true'),('BelongTo','constraint_1'),('CompileOrder','1')]:
        ET.SubElement(info,'Attr',{'Name':key,'Val':value})
(WORK / 'system.al').write_bytes(ET.tostring(project.getroot(), encoding='utf-8', xml_declaration=True).replace(b'UsedInP&amp;R', b'UsedInP&R'))
proof = {'status':'CONNECTED_NOT_YET_BUILT', 'ps_ports': ports, 'ps_raw_sha256':hashlib.sha256(psfile.read_bytes()).hexdigest(),
         'PL_sources_sha256_lf':{n:expected['rtl/'+n] for n in names}, 'converter_sha256':manifest['library_sha256'],
         'clock_pin':'H16', 'clock_hz':100000000, 'reset':'p2f_rst0_n -> two-stage common release',
         'motor_outputs':'not exported','dma':'not connected'}
(WORK / 'connections.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print(json.dumps(proof,indent=2))
