"""Generate official Video_NPU 1.1 variants and synthesize open-interface IPs.

No protected RTL edits, pin tie-offs, bitstream generation or file hashing.
Run variants sequentially; do not use while another TD job is running.
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
TD = Path(r'D:\Anlogic\TD_Release_2026.1_SP2.200.067')
BIN = TD / 'bin/td_commands_prompt.exe'
DEPOT = TD / 'ip/depot/Video_NPU_1.1'
REF = ROOT / 'reference/soc_prj/design_0/ip/design_0_Video_NPU_0'
MODES = ['YOLOV3TINY', 'YOLOV3', 'YOLOV4', 'YOLOV5S', 'YOLOV8N', 'MBFace']
VARIANTS = {
    'full': 'FULL',
    'full_native': 'FULL',
    'whole_no_video': None,
    'tiny_no_video': 'YOLOV3TINY',
    'mbface_no_video': 'MBFace',
    'v3_no_video': 'YOLOV3',
}
THREADS = '''set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "NPU_THREADS [get_param flow thread]"
get_num_thread
'''
CLOCK_SDC = '''# Both interface clocks must be copies of the same external source.
create_clock -name npu_data -period 10 [get_ports M_AXI_ACLK]
create_generated_clock -name npu_config -source [get_ports M_AXI_ACLK] -divide_by 1 [get_ports S_AXILite_ACLK]
'''


def run_tcl(out, name, text):
    script = out / (name + '.tcl')
    script.write_text(text, encoding='utf-8')
    log_path = out / (name + '.log')
    if log_path.exists():
        attempt = 1
        while (out / f'{name}_previous_{attempt}.log').exists():
            attempt += 1
        log_path.rename(out / f'{name}_previous_{attempt}.log')
    with log_path.open('w', encoding='utf-8') as log:
        result = subprocess.run([str(BIN), script.as_posix()], cwd=out, stdout=log,
                                stderr=subprocess.STDOUT)
    log = (out / (name + '.log')).read_text(encoding='utf-8', errors='replace')
    # TD may return 0 even after a Tcl/HDL error.
    assert result.returncode == 0 and ' ERROR:' not in log and 'coredump' not in log, name
    assert 'NPU_THREADS 16' in log and 'Number of Thread = 16' in log, name
    return log


def prepare(name, preset):
    out = ROOT / ('ip_' + name)
    out.mkdir(exist_ok=True)
    component = ET.parse(DEPOT / 'Component.xml').getroot()
    ns = {'i': 'http'}
    vals = {p.attrib['parameterId']: p.find('i:value', ns).text
            for p in component.find('i:parameters', ns)}
    full = preset == 'FULL'
    if full:
        preset = None
    vals.update({k: '0' for k in MODES})
    vals.update(NPU_SOFT='1', SOFT_NN='1', PRE_PROCESS='0', POST_PROCESS='0',
                SOFT_RESIZE='0', SOFT_CSC='0', SOFT_YOLO='0',
                SOFT_HDMI_DISPLAY='0', ALL_OPERATOR=str(int(preset is None)),
                SELECTABLE_NET=str(int(preset is not None)))
    if preset:
        vals[preset] = '1'
    if full:
        vals.update(PRE_PROCESS='1', POST_PROCESS='1', SOFT_RESIZE='1', SOFT_YOLO='1')
    groups = {
        'NN_POOLING': ['YOLOV3TINY', 'YOLOV4', 'YOLOV5S', 'YOLOV8N'],
        'NN_ACTIVATE': ['MBFace'],
        'NN_UPSAMPLE': MODES[:5],
        'NN_ROUTE': MODES[:5],
        'NN_SHORTCUT': MODES[1:],
    }
    for key, modes in groups.items():
        vals[key] = str(int(preset is None or preset in modes))
    design = (REF / 'Design.xml').read_text(encoding='utf-8')
    values = '<ipxact:configurableElementValues>\n' + ''.join(
        f'<ipxact:configurableElementValue referenceId="{k}">{v}</ipxact:configurableElementValue>\n'
        for k, v in vals.items()) + '</ipxact:configurableElementValues>'
    design = re.sub(r'<ipxact:configurableElementValues>.*?</ipxact:configurableElementValues>',
                    values, design, flags=re.S)
    design = design.replace('name="Video_NPU" version="1.0"', 'name="Video_NPU" version="1.1"')
    design = design.replace('DR1M90MEG484', 'DR1M90GEG400')
    design = design.replace('<anlogic:ipGenVersion>1.0', '<anlogic:ipGenVersion>1.1')
    (out / 'Design.xml').write_text(design, encoding='utf-8')
    for file in ['DesignConfiguration.xml', 'design_0_Video_NPU_0.xml']:
        (out / file).write_bytes((REF / file).read_bytes())
    (out / 'requested_config.json').write_text(json.dumps(vals, indent=2) + '\n')
    # Use the vendor dependency procs to check every derived soft-operator switch.
    checks = '''proc set_param {args} {}\n'''
    checks += ''.join(f'set {k} {v}\n' for k, v in vals.items())
    checks += f'source {{{(DEPOT / "Dependency.tcl").as_posix()}}}\n'
    calls = {
        'NN_POOLING': 'nn_pooling_def $NPU_SOFT $ALL_OPERATOR $YOLOV3TINY $YOLOV4 $YOLOV5S $YOLOV8N',
        'NN_ACTIVATE': 'nn_activate_def $NPU_SOFT $ALL_OPERATOR $MBFace',
        'NN_UPSAMPLE': 'nn_upsample_def $NPU_SOFT $ALL_OPERATOR $YOLOV3TINY $YOLOV3 $YOLOV4 $YOLOV5S $YOLOV8N',
        'NN_ROUTE': 'nn_route_def $NPU_SOFT $ALL_OPERATOR $YOLOV3TINY $YOLOV3 $YOLOV4 $YOLOV5S $YOLOV8N',
        'NN_SHORTCUT': 'nn_shortcut_def $NPU_SOFT $ALL_OPERATOR $YOLOV3 $YOLOV4 $YOLOV5S $YOLOV8N $MBFace',
    }
    for key, call in calls.items():
        checks += f'if {{[{call}] != ${key}}} {{error "Dependency mismatch {key}"}}\n'
    gen = f'cd {{{out.as_posix()}}}\n' + THREADS + checks
    gen += f'''set ::env(IP_EXPORT_PATH) {{{out.as_posix()}}}
xmlipgen -design_file Design.xml -designConfig_file DesignConfiguration.xml -component_file {{{(DEPOT / 'Component.xml').as_posix()}}} -usernamed_file design_0_Video_NPU_0.xml -mode behavior -package DR1M90GEG400
exit
'''
    run_tcl(out, 'generate', gen)
    assert (out / 'RTL/include/define.v').is_file()
    (out / 'enabled_macros.vh').write_bytes((out / 'RTL/include/define.v').read_bytes())
    # Virtual IO is a TD-supported IP boundary for capacity measurement. It does
    # not tie off AXI/control inputs or consume package pins; it is not a native
    # PS/HP integration or a physical timing signoff fixture.
    ports = []
    wrapper = (out / 'design_0_Video_NPU_0.v').read_text()
    for direction, hi, lo, port in re.findall(
            r'\b(input|output)\s*(?:\[(\d+):(\d+)\])?\s*(\w+)\s*[,\n]', wrapper):
        ports.extend([f'{port}[{i}]' for i in range(int(lo), int(hi)+1)] if hi else [port])
    assert len(ports) == 433
    (out / 'boundary.adc').write_text(''.join(
        'set_pin_assignment {' + port + '} {location=virtualIO;}\n' for port in ports))
    (out / 'fixture.sdc').write_text(CLOCK_SDC)
    # Minimal TD project: all functional inputs/outputs remain live at the boundary.
    source = (ROOT / 'reference/soc_prj/soc_prj.al').read_text(encoding='utf-8')
    start = source.index('    <Source_Files>')
    end = source.index('    <FileSets>')
    files = ''.join(f'<File Path="{file}"><FileInfo><Attr Name="UsedInSyn" Val="true"/>'
                    f'<Attr Name="UsedInP&R" Val="true"/><Attr Name="BelongTo" Val="design_1"/>'
                    f'<Attr Name="CompileOrder" Val="{i}"/></FileInfo></File>'
                    for i,file in enumerate(['RTL/video_npu_top_77b8d5bfaa14.v','design_0_Video_NPU_0.v']))
    source = source[:start] + '<Source_Files><Verilog>' + files + '</Verilog></Source_Files>\n' + source[end:]
    source = source.replace('<Name>soc_prj</Name>', '<Name>probe</Name>').replace('system_top','design_0_Video_NPU_0')
    source = re.sub(r'(<Project [^>]*Path=")[^"]*', lambda m: m[1] + out.as_posix(), source, count=1)
    (out / 'probe.al').write_text(source, encoding='utf-8')
    return out


def synth(out):
    text = f'''cd {{{out.as_posix()}}}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project -single_run probe.al
''' + THREADS + '''set_param flow syn_ip_flow off
if {[get_param flow syn_ip_flow] ne "off"} {error "Expected native synthesis flow"}
elaborate -top design_0_Video_NPU_0
read_adc -file boundary.adc
report_param -all -file effective_parameters.tcl
optimize_rtl
export_db rtl.db
optimize_gate -maparea gate.area
legalize_phy_inst
clear_user_sdc
read_sdc fixture.sdc
update_timing
if {[llength [get_clocks *]] != 2} {error "Expected two constrained interface clocks"}
report_area -file gate_full.area
report_timing_summary -file gate.timing -path_num 5
export_db gate.db
puts "NPU_SYNTH_DONE"
exit
'''
    log = run_tcl(out, 'synth', text)
    assert 'NPU_SYNTH_DONE' in log and (out / 'gate_full.area').is_file()
    assert not re.search(r'TMR-250[79]', log), 'Timing loop'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=VARIANTS, required=True)
    parser.add_argument('--generate-only', action='store_true')
    args = parser.parse_args()
    out = prepare(args.variant, VARIANTS[args.variant])
    if not args.generate_only:
        synth(out)
    print(out)
