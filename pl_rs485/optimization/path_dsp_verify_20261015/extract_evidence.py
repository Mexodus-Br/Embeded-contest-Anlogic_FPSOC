"""Read-only follow-up audit of the sealed route reports and retained checkpoints."""
import hashlib
import json
import re
from pathlib import Path

E = Path(__file__).resolve().parent
R = E.parents[2]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


identities = {}
for label, work, archive in [
    ('baseline', R/'bsp/work/telemetry_soc_prj', E.parent/'baseline'),
    ('optimized', R/'bsp/work/telemetry_opt_r1', E.parent/'top_r1/reports'),
]:
    identities[label] = {'checkpoint_sha256': sha(work/'gp_route.db')}
    for name in ['gp_route.area', 'gp_route.timing']:
        assert sha(work/name) == sha(archive/name), (label, name)
        identities[label][name] = sha(archive/name)

t = (E.parent/'top_r1/reports/gp_route.timing').read_text()
first = t.split('Max Paths\n', 1)[1].split('Slack               : 0.112ns', 1)[0]
assert 'Slack               : 0.080ns' in first
(E/'critical_path.txt').write_text(first, encoding='utf-8')
begin = re.search(r'Begin Point\s*:\s*(.*?) \(rising', first)[1]
end = re.search(r'End Point\s*:\s*(.*?) \(rising', first)[1]
summary = {
    'source_commit': '49e8ac6',
    'evidence_commit': '5f88d0f',
    'identities': identities,
    'path': {
        'begin': begin, 'end': end, 'clock': 'board_100m', 'corner': 'slow',
        'setup_slack_ns': 0.080, 'budget_ns': 10.000,
        'data_delay_ns': 9.702, 'cell_delay_ns': 1.996, 'net_delay_ns': 7.706,
        'logic_level': 7, 'max_fanout': 201, 'clock_skew_ns': 0.090,
        'default_clock_uncertainty_ns': 0.060,
        'launch_clock_arrival_ns': 4.810, 'capture_clock_arrival_ns': 4.419,
        'setup_ns': 0.068, 'crpr_ns': 0.301,
        'data_arrival_ns': 14.512, 'required_ns': 14.592,
        'notable_nets': [
            {'name': 'collector/inflight[0]_dup_3', 'fanout': 201, 'delay_ns': 1.991},
            {'name': 'collector/missed[0]_b17[8]', 'fanout': 15, 'delay_ns': 2.124},
        ],
    },
    'dsp_hierarchy': {},
}
for label, area in [('baseline', E.parent/'baseline/gp_route.area'),
                    ('optimized', E.parent/'top_r1/reports/gp_route.area')]:
    text = area.read_text()
    counts = {'top': int(re.search(r'#dsp\s+(\d+)', text)[1])}
    for module in ['rs485_latest_cache', 'motion_planner', 'rs485_multirate']:
        row = next(x for x in text.splitlines() if '|'+module in x.replace(' ', ''))
        counts[module] = int(row.split('|')[7].strip())
    assert counts['top'] == sum(counts[m] for m in ['rs485_latest_cache', 'motion_planner', 'rs485_multirate'])
    summary['dsp_hierarchy'][label] = counts
assert summary['dsp_hierarchy']['baseline']['rs485_latest_cache'] == 10
assert summary['dsp_hierarchy']['optimized']['rs485_latest_cache'] == 0
assert summary['dsp_hierarchy']['optimized']['top'] == 5
for p in E.glob('*dsp*.rpt'):
    summary[p.name] = sha(p)
before = (E/'baseline_dsp.rpt').read_text()
after = (E/'optimized_dsp.rpt').read_text()
summary['removed_dsp_instances'] = []
for group in range(5):
    for suffix in [167, 260]:
        name = f'control/core/fabric/telemetry/cache/mult{group}_syn_{suffix}'
        line = next(x for x in before.splitlines() if name+' ' in x)
        location = re.search(r'\[(\d+), (\d+)\]', line)
        assert name not in after
        summary['removed_dsp_instances'].append({'name': name, 'location': [int(x) for x in location.groups()]})
for name, marker in [('baseline_dsp_final.log', 'BASELINE_DSP_VERIFIED'),
                     ('optimized_dsp_final.log', 'OPTIMIZED_PATH_DSP_VERIFIED'),
                     ('baseline_connections.log', 'BASELINE_DSP_CONNECTIONS_VERIFIED')]:
    log = (E/name).read_text(encoding='utf-8')
    assert marker in log and 'ERROR:' not in log
    summary[name] = sha(E/name)
(E/'critical_path.txt').write_text(first, encoding='utf-8')
(E/'verification.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
print(json.dumps(summary['dsp_hierarchy'], indent=2))
