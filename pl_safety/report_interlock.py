"""Compare the same complete native-PS top before/after SAF2; no hashes."""
import argparse
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def register_cost(folder, stage):
    text = (folder / (stage + '.area')).read_text()
    result = {'slice_reg': int(re.search(r'^  #slice reg\s+(\d+)', text, re.M)[1]),
              'pad_reg': int(re.search(r'^  #pad reg\s+(\d+)', text, re.M)[1])}
    modules = {}
    for line in text.splitlines():
        columns = [x.strip() for x in line.split('|')]
        if len(columns) > 5 and columns[2] in ['safety_interlock', 'safety_interlock_regs',
                'safety_controller', 'safety_regs', 'motion_service', 'rs485_gp_regs', 'rs485_transaction']:
            modules[columns[2]] = {'logic_lut': int(columns[3]), 'ripple': int(columns[4]),
                                   'sequential': int(columns[5])}
    result['relevant_modules_tool_hierarchy'] = modules
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--build', required=True)
    p.add_argument('--audit', required=True)
    p.add_argument('--tag', required=True)
    p.add_argument('--summary', default='summary.json', help='Explicit completed build/resume summary basename')
    p.add_argument('--route-log', help='Additional completed route log basename; original logs remain included')
    a = p.parse_args()
    old = ROOT / 'pl_safety/optimization/timing_20261017'
    spec = importlib.util.spec_from_file_location('baseline_report', old / 'report.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    baseline = ROOT / 'pl_safety/build/closure_cofactor_route5'
    current = ROOT / 'pl_safety/build' / a.build
    audit = ROOT / 'pl_safety/evidence' / a.audit
    out = ROOT / 'pl_safety/evidence' / a.tag
    out.mkdir(exist_ok=False)
    assert Path(a.summary).name == a.summary
    summary = json.loads((current / a.summary).read_text())
    assert summary['passed'] and summary['threads'] == 16
    assert not re.search(r'TMR-250[79]', (current / 'run.log').read_text(errors='replace'))
    if summary.get('resumed_from'):
        assert a.route_log, 'Resumed summary requires its explicit completed route log'
    if a.route_log:
        assert Path(a.route_log).name == a.route_log
        route_log = current / a.route_log
        route_text = route_log.read_text(errors='replace')
        assert 'INTERLOCK_RESUMED_ROUTE_COMPLETE' in route_text
        assert not re.search(r'\bERROR:|TMR-250[79]', route_text)
        assert 'INTERLOCK_TD_THREADS 16' in route_text and 'Number of Thread = 16' in route_text
        original_logs = helper.pnr_logs
        def logs_with_resume(folder):
            logs = original_logs(folder)
            if folder == current:
                # Compare the completed gate/place plus completed resumed route.
                # Keep interrupted logs on disk, but do not double count their
                # partial routing warnings/iterations as part of the final flow.
                resumed_stage = 'place' if summary.get('resumed_from') == 'gate.db' else 'route'
                logs = [(path, content.split('RUN-1002 : start command "'+resumed_stage+'"')[0]
                         if path.name == 'run.log' else content) for path, content in logs]
                logs.append((route_log, route_text))
            return logs
        helper.pnr_logs = logs_with_resume
    for name in ['gp/gp.sdc', 'gp/gp.adc', 'gp/ps-generated-properties.tcl']:
        assert (current / name).read_bytes() == (baseline / name).read_bytes(), name
    audits = {name: json.loads((audit / name / 'result.json').read_text())
              for name in ['physical', 'pins', 'cdc']}
    assert all(x['passed'] and x['build'] == a.build for x in audits.values())
    prior = json.loads((old / 'comparison_closure_cofactor_route5.json').read_text())
    before, after = helper.resources(baseline), helper.resources(current)
    owner_cache_bits = int('reg home_owner_q;' in (current / 'gp/safety_controller.v').read_text())
    epoch_cache_bits = int('reg epoch_match_q;' in (current / 'gp/safety_interlock.v').read_text())
    reset_predecode_bits = 2 * int('aw_reset,w_reset;' in (current / 'gp/rs485_gp_regs.v').read_text())
    source_predecode_bits = 6 * int('output reg [5:0] protection_decoded' in (current / 'gp/rs485_transaction.v').read_text())
    context_cache_bits = 2 * int('reg active_context_q,off_context_q;' in (current / 'gp/safety_interlock.v').read_text())
    declared_bits = 2460 + owner_cache_bits + epoch_cache_bits + reset_predecode_bits + source_predecode_bits + context_cache_bits
    result = {
        'baseline': 'eccab43/88af6ee closure_cofactor_route5, complete native PS and protected IP',
        'build': a.build, 'completed_summary': a.summary, 'additional_route_log': a.route_log,
        'resumed_log_scope': 'Completed original gate/place plus completed resumed route; interrupted routing retained on disk but excluded from aggregate counts' if a.route_log else None,
        'resources_before': before, 'resources_after': after,
        'absolute_delta': {k: after[k]['used'] - before[k]['used'] for k in before},
        'timing_before': {s: helper.stage(baseline, s) for s in ['gate', 'place', 'route']},
        'timing_after': {s: helper.stage(current, s) for s in ['gate', 'place', 'route']},
        'routing_before': helper.routing(baseline), 'routing_after': helper.routing(current),
        'fanout_before': prior['fanout_after'],
        'fanout_after': helper.net_stats(audit / 'pins/result.json'),
        'clocks_before': helper.clocks(baseline), 'clocks_after': helper.clocks(current),
        'check_timing_before': helper.check_diagnostics(baseline),
        'check_timing_after': helper.check_diagnostics(current),
        'warnings_before': helper.warnings(baseline), 'warnings_after': helper.warnings(current),
        'original_constraints_byte_equal': True, 'threads': 16,
        'new_declared_state_bits': {'monitor': 1034, 'register_extension': 1422,
                                    'idle_admission': 1, 'home_opcode_predecode': 1,
                                    'rs485_run_predecode': 2, 'home_owner_decode': owner_cache_bits,
                                    'epoch_comparison_cache': epoch_cache_bits,
                                    'rs485_reset_predecode': reset_predecode_bits,
                                    'rs485_emit_predecode': source_predecode_bits,
                                    'monitoring_context_projections': context_cache_bits,
                                    'total': declared_bits},
        'state_cost_note': 'Declared bits include full 1024-bit snapshot. Whole-top mapped/routed FF deltas below are actual tool costs; optimization may merge/prune or replicate state.',
        'actual_register_cost_before': {s: register_cost(baseline, s) for s in ['gate', 'route']},
        'actual_register_cost_after': {s: register_cost(current, s) for s in ['gate', 'route']},
        'timing_pass': summary['timing_pass'], 'signoff_pass': False,
        'hashes_computed': False,
        'independent_open_gates': ['SYN-5066 original vendor S2MM diagnosis',
            'physical safety pins/electrical/synchronizer qualification and IO timing',
            'RS485 0x3E protection semantics, STP querying, transceiver and delayed replies',
            'mechanical HOME/stop/power recovery and production HOME profile',
            'BSP DMA/DDR buffer quarantine and board validation']}
    result['new_warning_codes'] = sorted(set(result['warnings_after']) - set(result['warnings_before']))
    assert {k: v['frequency_mhz'] for k, v in result['clocks_before'].items()} == {
        k: v['frequency_mhz'] for k, v in result['clocks_after'].items()}
    (out / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# SAF2 complete actual-top comparison', '',
             'Same native PS, protected GP converter, dual DMA/HP0/HP1, 100MHz original constraints. '
             'All TD build and database audit stages explicitly use/read back 16 threads.', '',
             '|Resource|Before used|Before %|Before remaining|After used|Total|After %|After remaining|Delta|',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name, r in after.items():
        percent = f"{r['percent']:.3f}" if r['percent'] is not None else 'N/A'
        b = before[name]
        before_percent = f"{b['percent']:.3f}" if b['percent'] is not None else 'N/A'
        lines.append(f"|{name}|{b['used']}|{before_percent}|{b['remaining']}|{r['used']}|{r['total']}|{percent}|{r['remaining']}|{result['absolute_delta'][name]:+d}|")
    lines += ['', '|Stage|Before setup/hold ns|After setup/hold ns|', '|---|---:|---:|']
    for s in ['gate', 'place', 'route']:
        b, c = result['timing_before'][s], result['timing_after'][s]
        lines.append(f"|{s}|{b['setup_ns']:+.3f}/{b['hold_ns']:+.3f}|{c['setup_ns']:+.3f}/{c['hold_ns']:+.3f}|")
    lines += ['', '|Stage|Worst setup launch|Capture|Logic levels|Cell ns|Net ns|',
              '|---|---|---|---|---:|---:|']
    for s in ['gate', 'place', 'route']:
        w = result['timing_after'][s]['reported_worst_setup'][0]
        lines.append(f"|{s}|{w['Begin Point']}|{w['End Point']}|{w.get('Logic Level','N/A')}|{w['cell_delay_ns']}|{w['net_delay_ns']}|")
    lines += ['', '|Stage|Before slice/PAD FF|After slice/PAD FF|Slice FF delta|PAD FF delta|',
              '|---|---:|---:|---:|---:|']
    for s in ['gate', 'route']:
        b = result['actual_register_cost_before'][s]
        c = result['actual_register_cost_after'][s]
        lines.append(f"|{s}|{b['slice_reg']}/{b['pad_reg']}|{c['slice_reg']}/{c['pad_reg']}|{c['slice_reg']-b['slice_reg']:+d}|{c['pad_reg']-b['pad_reg']:+d}|")
    lines += ['', f"Route target passed: {result['timing_pass']}. Release signoff: False.", '',
              f"Added declared state: {declared_bits} bits (monitor 1034, register extension 1422, idle admission 1, HOME opcode predecode 1, RUN predecode 2, same-edge HOME owner decode {owner_cache_bits}, full-word epoch comparison {epoch_cache_bits}, reset predecode {reset_predecode_bits}, EMIT predecode {source_predecode_bits}, current monitoring contexts {context_cache_bits}). "
              'Actual whole-top register cost is the slice_reg/pad_reg delta above; declared state is not a utilization estimate.', '',
              'comparison.json contains the worst setup/hold paths with logic levels and cell/net delays, '
              'separate data/CE/reset/legal-clock fanout, congestion, clock loads, timing diagnostics and warning comparisons. '
              'Physical/pin/CDC audit results refer to the exact unchanged route database by direct byte comparison; no hashes.', '',
              'Independent open gates:']
    lines += ['- ' + x for x in result['independent_open_gates']]
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'timing_pass': result['timing_pass'], 'delta': result['absolute_delta'],
                      'new_warning_codes': result['new_warning_codes']}, indent=2))


if __name__ == '__main__':
    main()
