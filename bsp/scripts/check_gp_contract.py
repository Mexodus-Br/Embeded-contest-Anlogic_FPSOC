"""Check frozen GP software inputs; require explicit PL evidence before integration."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

REQUIRED = {'gp_ports', 'protocol_converter', 'address_decode', 'irq_mapping',
            'clock_reset', 'hdl_simulation', 'sta', 'address_map'}

class ContractError(ValueError):
    pass

def require(yes, message):
    if not yes:
        raise ContractError(message)

def inside(root, relative):
    p = (root / relative).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError:
        raise ContractError('evidence escapes workspace')
    return p

def check(workspace, evidence=None):
    raw = (workspace / 'pl_interface/schema.json').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    schema = json.loads(raw)
    profile = schema['gp_control_profiles']['gp_control_probe_v1']
    require(profile['status'].startswith('USER_CONFIRMED'), 'shared profile not confirmed')
    require(profile['supported_commands'] == ['SNAPSHOT', 'NOP'], 'command scope changed')
    a, irq = profile['address'], profile['irq']
    require(isinstance(a['base'], int) and 0 <= a['base'] < 2**32 and a['base'] % 4096 == 0 and a['size'] == 4096,
            'invalid probe MMIO window')
    legacy = a['legacy_avoidance']
    require(a['base'] + a['size'] <= legacy['base'] or legacy['base'] + legacy['size'] <= a['base'], 'legacy PL resource conflict')
    require(a['gp_port'] == 'GP0' and a['address_width'] == 33 and a['data_width'] == 32 and a['id_width'] == 12, 'GP widths changed')
    require(irq['gic_intid'] == irq['spi']+32 and irq['dts_cells'] == [0,irq['spi'],4], 'SPI/INTID mismatch')
    require(irq['trigger'] == 'level-high' and irq['pl_line'] == 0, 'IRQ wiring/trigger mismatch')
    require(profile['converter']['input_protocol'] == 'AXI3' and profile['converter']['output_protocol'] == 'AXI4-Lite', 'converter protocol mismatch')
    registers = {r['name']:r for r in schema['registers']}
    offsets = []
    for name in profile['supported_registers']:
        r = registers[name]
        require(r['width'] == 32 and 0 <= r['offset'] <= a['size']-4 and r['offset'] % 4 == 0, 'register window/alignment mismatch')
        offsets.append(r['offset'])
    require(len(offsets) == len(set(offsets)), 'register alias')
    if evidence is None:
        return {'status':'CONFIRMED_SOFTWARE_SCOPE_ONLY', 'schema_sha256':digest, 'deployable':False}
    e = evidence
    require(e['status'] == 'READY_FOR_BSP_INTEGRATION', 'PL integration not ready')
    require(e['schema_sha256'] == digest, 'PL/schema identity mismatch')
    kinds = set()
    require(e['review_reference'].strip(), 'review reference missing')
    for record in e['records']:
        require(record['verified'] is True, 'unverified PL evidence: ' + record['kind'])
        data = inside(workspace, record['path']).read_bytes()
        require(hashlib.sha256(data).hexdigest() == record['sha256'], 'evidence changed: ' + record['path'])
        kinds.add(record['kind'])
    require(REQUIRED <= kinds, 'missing evidence categories: ' + ', '.join(sorted(REQUIRED-kinds)))
    for source in e['sources']:
        require(hashlib.sha256(inside(workspace,source['path']).read_bytes()).hexdigest() == source['sha256'], 'source hash mismatch')
    require(e['sources'], 'no integrated PL source manifest')
    hp = inside(workspace,e['hpf']['path'])
    require(hashlib.sha256(hp.read_bytes()).hexdigest() == e['hpf']['sha256'], 'HPF changed')
    with zipfile.ZipFile(hp) as z:
        require(hashlib.sha256(z.read('HPFs/system.bit')).hexdigest() == e['bitstream_sha256'], 'HPF contains different bitstream')
        header = z.read('HPFs/soc_plat.h').decode()
    # Reuse the prior DDR baseline's generated macros; changes require review.
    import re
    defines = dict(re.findall(r'^#define\s+(DDRC_\w+)\s+([^\r\n]+)',header,re.M))
    for key,value in e['ddr_expected_macros'].items():
        require(key in defines and defines[key].strip() == value, 'DDR initialization input mismatch: ' + key)
    require(e['ddr_expected_macros'], 'DDR audit missing')
    require(e['motor_outputs'] == 'not exported' and e['dma'] == 'not connected', 'probe isolation changed')
    return {'status':'PL_EVIDENCE_HASHES_CHECKED_REVIEW_REQUIRED', 'schema_sha256':digest, 'deployable':False,
            'note':'Hashes preserve reviewed evidence; do not prove electrical/board behavior.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--evidence',type=Path)
    p.add_argument('--require-evidence',action='store_true')
    a=p.parse_args()
    try:
        require(not a.require_evidence or a.evidence is not None,'integration requires actual PL evidence')
        e=json.loads(a.evidence.read_text(encoding='utf-8')) if a.evidence else None
        print(json.dumps(check(a.workspace,e),indent=2))
    except (ContractError, KeyError, OSError, TypeError, ValueError, zipfile.BadZipFile) as err:
        raise SystemExit('GP_BLOCKED: '+str(err))
if __name__=='__main__':
    main()
