"""Derive kernel constants and candidate DTS from the confirmed shared profile.

Generated DTS is not a deployment approval: actual PL/HPF evidence is separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

def prepare(workspace, output):
    raw = (workspace / 'pl_interface/schema.json').read_bytes()
    schema = json.loads(raw)
    p = schema['gp_control_profiles']['gp_control_probe_v1']
    if not p['status'].startswith('USER_CONFIRMED'):
        raise ValueError('GP profile not confirmed')
    a, irq = p['address'], p['irq']
    if not (a['address_width'] == 33 and a['data_width'] == 32
            and a['base'] >= a['legacy_avoidance']['base'] + a['legacy_avoidance']['size']
            and irq['gic_intid'] == irq['spi'] + 32
            and irq['dts_cells'] == [0, irq['spi'], 4]
            and irq['trigger'] == 'level-high'):
        raise ValueError('confirmed profile transport changed')
    generated = (workspace / 'pl_interface/generated/interface_defs.h').read_text(encoding='utf-8')
    if 'schema.json SHA256 ' + hashlib.sha256(raw).hexdigest() not in generated.splitlines()[0]:
        raise ValueError('shared generated header is stale')
    # Kernel cannot include libc stdint.h. Keep only generated integer defines;
    # no register or bit definition is independently handwritten here.
    lines = [l for l in generated.splitlines() if l.startswith('#define PLI_')]
    lines = [re.sub(r'UINT(32|64)_C\(([^)]+)\)', lambda m: '(' + m[2] + ('U)' if m[1] == '32' else 'ULL)'), l) for l in lines]
    output.mkdir(parents=True, exist_ok=True)
    (output / 'gp_defs.h').write_text('/* Derived from shared generator output; do not edit. */\n' + '\n'.join(lines) + '\n', encoding='utf-8')
    node = f'''/* CANDIDATE: requires generated HPF/IP/IRQ/address/STA evidence. */
&soc {{
    bsp_gp: gp-control@{a['base']:x} {{
        compatible = "embedded-contest,gp-control-probe-v1";
        reg = <0x0 0x{a['base']:08x} 0x0 0x{a['size']:08x}>;
        interrupt-parent = <&gic>;
        interrupts = <0 {irq['spi']} 4>;
        status = "disabled";
    }};
}};
'''
    (output / 'gp-candidate.dtsi').write_text(node, encoding='utf-8')
    (output / 'inputs.json').write_text(json.dumps({'profile': 'gp_control_probe_v1', 'status': 'SOFTWARE_PREPARED_NOT_DEPLOYABLE', 'schema_sha256': hashlib.sha256(raw).hexdigest(), 'header_sha256': hashlib.sha256(generated.encode()).hexdigest(), 'contract_commit': 'ca50bbf', 'deployment': p['deployment']}, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'gp/generated')
    args = parser.parse_args()
    prepare(args.workspace, args.output)
