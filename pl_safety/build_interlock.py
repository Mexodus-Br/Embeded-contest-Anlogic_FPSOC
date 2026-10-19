"""Full actual SAF2 project from the routed SAF1 reference; no file hashing.

Retain original device/PS/protected IP/IO/100MHz constraints. No bit generation.
Historical manifest is used only as an input path inventory, never rehashed.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import traceback

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'pl_safety'
REFERENCE = D / 'build/closure_cofactor_route5'
THREADS = '''set_param flow thread 16
if {[get_param flow thread] != 16} {error "Expected threads=16"}
puts "INTERLOCK_TD_THREADS [get_param flow thread]"
get_num_thread
'''


def prepare(tag):
    out = D / 'build' / tag
    out.mkdir(exist_ok=False)
    inventory = json.loads((REFERENCE / 'inputs.json').read_text())['candidate_inputs_sha256']
    copied = []
    for name in inventory:
        # Old auxiliary process evidence is not a project input for this run.
        if Path(name).suffix.lower() in ('.log', '.logw', '.bak', '.violation'):
            continue
        source = REFERENCE / name
        dest = out / name
        assert source.is_file(), source
        assert dest.resolve().is_relative_to(out.resolve()), name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        assert source.read_bytes() == dest.read_bytes(), source
        copied.append(name)
    # Replace only the authorized PL RTL and generated definitions. Keep the
    # actual native PS and protected vendor files from the complete reference.
    replacements = []
    for folder in ['pl_motion/rtl', 'pl_rs485/rtl', 'pl_safety/rtl', 'pl_safety/generated']:
        for source in (ROOT / folder).glob('*.v*'):
            shutil.copyfile(source, out / 'gp' / source.name)
            replacements.append(source.relative_to(ROOT).as_posix())
    for source in (ROOT / 'pl_rs485/generated').glob('*.vh'):
        shutil.copyfile(source, out / 'gp' / source.name)
    for source in (ROOT / 'pl_interface/generated').glob('*.vh'):
        shutil.copyfile(source, out / 'gp/generated' / source.name)
        shutil.copyfile(source, out / 'gp' / source.name)
    project = (out / 'system.al').read_text(encoding='utf-8')
    project = re.sub(r'(<Project [^>]*Path=")[^"]*', lambda m: m[1] + out.as_posix(), project, count=1)
    additions = []
    for folder in ['rtl', 'generated']:
        for source in sorted((D / folder).glob('*.v')):
            name = 'gp/' + source.name
            if 'Path="' + name + '"' not in project:
                additions.append('<File Path="' + name + '"><FileInfo><Attr Name="UsedInSyn" Val="true" />'
                                 '<Attr Name="UsedInP&amp;R" Val="true" /><Attr Name="BelongTo" Val="design_1" />'
                                 '<Attr Name="CompileOrder" Val="3" /></FileInfo></File>')
    project = project.replace('</Verilog>', ''.join(additions) + '</Verilog>').replace('P&amp;R', 'P&R')
    (out / 'system.al').write_text(project, encoding='utf-8')
    wrapper = out / 'system/hdl/system_wrapper.v'
    text = wrapper.read_text()
    assert text.count('safety_rs485_gp_ps_top #(') == 1
    wrapper.write_text(text.replace('safety_rs485_gp_ps_top #(', 'interlock_rs485_gp_ps_top #('))
    unchanged = ['gp/gp.sdc', 'gp/gp.adc', 'gp/ps-generated-properties.tcl', 'gp/axi_dma.v',
                 'gp/axi_protocol_converter_merge.v', 'gp/axi_dma_func_pkg.vh', 'gp/axi_dma_param_pkg.vh']
    for name in unchanged:
        assert (out / name).read_bytes() == (REFERENCE / name).read_bytes(), name
    metadata = {'reference': str(REFERENCE), 'head': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'inventory_path_count': len(copied), 'source_replacements': replacements,
        'unchanged_direct_byte_checks': unchanged, 'hashes_computed': False,
        'reference_speed': 2, 'production_profile': False, 'resource_fixture_profile': 2,
        'no_bitgen': True, 'signoff_pass': False}
    (out / 'inputs.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--margin', type=float, default=1.25)
    a = parser.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+', a.tag)
    assert 0 <= a.margin <= 3
    out = prepare(a.tag)
    (out / 'place_budget.sdc').write_text(f'set_clock_uncertainty -setup {a.margin} [get_clocks board_100m]\n')
    (out / 'route_budget.sdc').write_text(f'set_clock_uncertainty -setup {a.margin} [get_clocks board_100m]\n')
    original = '''clear_user_sdc
read_sdc gp/gp.sdc
read_sdc gp/ps-generated-properties.tcl
'''
    script = f'''cd {out.as_posix()}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
open_project -single_run system.al
{THREADS}
elaborate -top system_wrapper
read_adc -file gp/gp.adc
{original}
set_param place hfn_opt_effort high
set_param place max_fanout 128
set_param place opt_timing high
set_param place logic_level_opt on
report_param -all -file effective_parameters.tcl
optimize_rtl
optimize_gate -maparea gate.area
report_timing_summary -file gate.timing -path_num 10
export_db gate.db
{THREADS}
read_sdc place_budget.sdc
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place_budget.timing -path_num 10
{original}
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 10
export_db place.db
{THREADS}
{original}
read_sdc route_budget.sdc
route
update_timing -mode final
report_timing_summary -file route_budget.timing -path_num 10
{original}
export_sdc -file nominal_route.sdc
update_timing -mode final
report_timing_summary -file route.timing -path_num 10
report_area -io_info -file route.area
check_timing -verbose -file route.check
report_route_status -drc -file route.drc
export_db route.db
puts INTERLOCK_FULL_TOP_COMPLETE
exit
'''
    (out / 'run.tcl').write_text(script)
    if a.prepare_only:
        print('PASS complete actual project prepared without hashes', out)
        return
    result = {'passed': False, 'signoff_pass': False, 'hashes_computed': False}
    try:
        with (out / 'run.log').open('w', encoding='utf-8') as log:
            p = subprocess.run([shutil.which('td_commands_prompt'), (out / 'run.tcl').as_posix()],
                               cwd=out, stdout=log, stderr=subprocess.STDOUT, timeout=14400)
        text = (out / 'run.log').read_text(encoding='utf-8', errors='replace')
        assert p.returncode == 0 and 'INTERLOCK_FULL_TOP_COMPLETE' in text and not re.search(r'\bERROR:', text)
        assert not re.search(r'TMR-250[79]', text), 'Combinational timing loop is not admissible'
        assert 'INTERLOCK_TD_THREADS 16' in text and 'Number of Thread = 16' in text
        assert not re.search(r'Global iterations in (?!16\b)\d+ thread', text)
        stages = {}
        for stage in ['gate', 'place', 'route']:
            report = (out / (stage + '.timing')).read_text()
            stages[stage] = {key: float(re.search(pattern, report)[1]) for key, pattern in
                            [('setup_ns', r'SWNS:\s*([-\d.]+)ns'), ('hold_ns', r'HWNS:\s*([-\d.]+)ns')]}
        for stage in ['place', 'route']:
            report = (out / (stage + '.timing')).read_text()
            assert set(re.findall(r'sdc uncertainty\s*:?\s*([-\d.]+)', report)) <= {'0.000'}, stage
        for name in ['gp/gp.sdc', 'gp/gp.adc', 'gp/ps-generated-properties.tcl']:
            assert (out / name).read_bytes() == (REFERENCE / name).read_bytes(), name
        result.update(passed=True, threads=16, stages=stages,
                      timing_pass=stages['route']['setup_ns'] > 1 and stages['route']['hold_ns'] >= 0)
        print(json.dumps(result, indent=2))
    except Exception:
        result['failure'] = traceback.format_exc()
        raise
    finally:
        (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
