"""Account for existing, unmodified IP hierarchy; never synthesize a pruned IP.

The residual is a structural observation, not a legal configuration or a lower
bound. Only disjoint hierarchy rows are added/subtracted. No file hashes.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIELDS = ['logic_lut', 'ripple', 'registers', 'eram', 'dsp', 'dram_lut',
          'shifter_lut', 'f7mux', 'f8mux', 'pll', 'adc', 'soc']


def rows(path):
    result = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        parts = [s.strip() for s in line.split('|')]
        if len(parts) != 16 or not all(s.isdigit() for s in parts[3:15]):
            continue
        result[parts[1]] = dict(zip(FIELDS, map(int, parts[3:15])))
    return result


def counts(row):
    return {
        'lut_capacity_equivalent': sum(row[k] for k in
            ['logic_lut', 'ripple', 'dram_lut', 'shifter_lut']),
        'registers': row['registers'], 'eram': row['eram'], 'dsp': row['dsp']}


def total(items):
    return {k: sum(item[k] for item in items) for k in
            ['lut_capacity_equivalent', 'registers', 'eram', 'dsp']}


def analyze(path):
    data = rows(path)
    core = counts(data['video_npu_top_77b8d5bfaa14_Inst'])
    shell = total([counts(data[k]) for k in
        ['U_soft_npu_axi_we', 'U_soft_topctrl', 'u_clp', 'u_soft_axi_rd_if']])
    operators = {k: counts(data[k]) for k in ['u_pooling', 'u_route', 'u_upsample']}
    operator_sum = total(operators.values())
    residual = {k: core[k] - operator_sum[k] for k in core}
    assert all(v >= 0 for v in residual.values())
    return dict(source=str(path.relative_to(ROOT)), ip_core=core,
                four_shell_siblings=shell, three_operator_siblings=operators,
                three_operators_total=operator_sum,
                structural_residual_not_a_configuration=residual)


def main():
    result = dict(
        meaning='Accounting of existing IP only; no pruned netlist was generated.',
        hard_only_runtime_qualified=False,
        legal_minimum_pl_known=False,
        external_ps_hp_interconnect_measured=False,
        gate=analyze(ROOT / 'ip_tiny_no_video/gate_full.area'),
        route=analyze(ROOT / 'physical_tiny_route100/route.area'))
    assert result['route']['ip_core']['lut_capacity_equivalent'] == 10884
    assert result['route']['structural_residual_not_a_configuration'] == dict(
        lut_capacity_equivalent=4459, registers=4645, eram=5, dsp=0)
    (ROOT / 'support_accounting.json').write_text(
        json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
