"""Final routed physical/CDC audits with direct byte identity, no hashes.

Reuse the proven TD net/pin/CDC queries and ALL their assertions. Replace only
the old hash identity mechanism with one in-memory exact route-DB byte snapshot.
Historical scripts, evidence, databases and logs remain untouched.
"""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'pl_safety/optimization/timing_20261017'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--build', required=True)
    p.add_argument('--tag', required=True)
    a = p.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+', a.tag)
    assert re.fullmatch('[A-Za-z0-9_-]+', a.build)
    out = ROOT / 'pl_safety/evidence' / ('interlock_audit_' + a.tag)
    out.mkdir(exist_ok=False)
    database = ROOT / 'pl_safety/build' / a.build / 'route.db'
    before = database.read_bytes()

    def verify_route_bytes(path):
        assert path.resolve() == database.resolve(), 'Unexpected database identity'
        assert path.read_bytes() == before, 'Routed DB changed during audit'
        return str(database.resolve())

    argv = sys.argv[:]
    try:
        for script, tag, extra in [('physical_audit.py', 'physical', []),
                                   ('pin_inventory.py', 'pins', ['--nets', 'physical']),
                                   ('cdc_audit.py', 'cdc', [])]:
            path = OLD / script
            source = path.read_text()
            old = 'E=Path(__file__).resolve().parent;R=E.parents[2]'
            assert source.count(old) == 1
            source = source.replace(old, 'E=AUDIT_OUTPUT;R=AUDIT_ROOT')
            source = source.replace("hashlib.sha256((b/'route.db').read_bytes()).hexdigest()",
                                    "verify_route_bytes(b/'route.db')")
            source = source.replace('route_db_sha256', 'route_db_path')
            for old, new in [
                ("hashlib.sha256((o/'nets.tsv').read_bytes()).hexdigest()", "str((o/'nets.tsv').resolve())"),
                ('hashlib.sha256(csv.read_bytes()).hexdigest()', 'str(csv.resolve())'),
                ('hashlib.sha256(original).hexdigest()', "'direct_bytes_equal_to_original_constraints'"),
                ('net_table_sha256', 'net_table_path'),
                ('original_sdc_sha256', 'original_sdc_byte_comparison')]:
                source = source.replace(old, new)
            assert 'hashlib.sha256(' not in source, script
            sys.argv = [str(path), '--build', a.build, '--tag', tag, *extra]
            verify_route_bytes(database)
            exec(compile(source, str(path), 'exec'),
                 {'__name__': '__main__', '__file__': str(path), 'AUDIT_OUTPUT': out,
                  'AUDIT_ROOT': ROOT, 'verify_route_bytes': verify_route_bytes})
            verify_route_bytes(database)
        print('PASS final physical/pin/CDC assertions; exact DB bytes unchanged; no hashes')
    finally:
        sys.argv = argv


if __name__ == '__main__':
    main()
