"""SAF2/legacy ABI and generator checks, with no file or log hashing."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def preserved(old, new, path=''):
    if isinstance(old, dict):
        assert isinstance(new, dict), path
        return sum(preserved(value, new[key], path + '/' + key) for key,value in old.items())
    if isinstance(old, list):
        assert isinstance(new, list) and len(new) == len(old), path
        return sum(preserved(value, new[i], path + '/' + str(i)) for i,value in enumerate(old))
    assert type(old) is type(new) and old == new, (path, old, new)
    return 1


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def definitions(data):
    text = data.decode('utf-8') if isinstance(data, bytes) else data
    return {name: int(value, 16) for name,value in re.findall(
        r"(?:`define|#define)\s+(\w+)\s+(?:32'h|UINT32_C\(0x|0x)([0-9a-fA-F]+)", text)}


def main():
    old = json.loads(subprocess.check_output(['git','show','249f3c3:pl_interface/schema.json'], cwd=ROOT))
    new = json.loads((ROOT / 'pl_interface/schema.json').read_text(encoding='utf-8'))
    count = preserved(old, new)
    checked = 0
    files = ['pl_interface/generated/interface_defs.h', 'pl_interface/generated/interface_defs.vh',
             'pl_rs485/generated/gp_defs.h', 'pl_rs485/generated/gp_defs.vh',
             'pl_rs485/generated/telem_defs.h', 'pl_rs485/generated/telem_defs.vh',
             'pl_rs485/generated/rs485_defs.h', 'pl_rs485/generated/rs485_defs.vh',
             'pl_rs485/generated/rate_defs.h', 'pl_rs485/generated/rate_defs.vh',
             'pl_safety/generated/safety_defs.h', 'pl_safety/generated/safety_defs.vh']
    for name in files:
        expected = definitions(subprocess.check_output(['git','show','249f3c3:' + name], cwd=ROOT))
        actual = definitions((ROOT / name).read_bytes())
        assert expected == actual, name
        checked += len(expected)
    generator = module('interlock_definitions', ROOT / 'pl_safety/generate_interlock.py')
    expected = {'SI_' + key: value for key,value in generator.constants().items()}
    for suffix in ['h','vh']:
        assert definitions((ROOT / ('pl_safety/generated/interlock_defs.' + suffix)).read_bytes()) == expected
    p = new['interlock_profiles']['gp_safety_interlock_v2']
    assert p['profile'] == int.from_bytes(b'SAF2','little') and p['collector_profile'] == int.from_bytes(b'R5S2','little')
    assert (p['timeout_min_us'],p['timeout_default_us'],p['timeout_max_us'],p['heartbeat_period_us']) == (1000000,2000000,3000000,500000)
    assert new['safety_profiles']['gp_safety_home_v1']['caps'] == 63
    print(f'PASS legacy schema leaves={count}, generated numeric definitions={checked}, SAF2/R5S2 constants and frozen parameters; no hashes')


if __name__ == '__main__':
    main()
