"""Failure cases that must prevent unreviewed register/IRQ scope migration."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('gate', ROOT / 'bsp/scripts/check_gp_contract.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'pl_interface').mkdir()
        self.schema = json.loads((ROOT / 'pl_interface/schema.json').read_text(encoding='utf-8'))

    def tearDown(self):
        self.temp.cleanup()

    def run_schema(self, change=None):
        s = copy.deepcopy(self.schema)
        if change:
            change(s)
        (self.root / 'pl_interface/schema.json').write_text(json.dumps(s), encoding='utf-8')
        return gate.check(self.root)

    def test_confirmed_scope_is_not_deployment(self):
        self.assertFalse(self.run_schema()['deployable'])

    def reject(self, change):
        with self.assertRaises(gate.ContractError):
            self.run_schema(change)

    def test_draft_cannot_be_used(self):
        self.reject(lambda s: s['gp_control_profiles']['gp_control_probe_v1'].update(status='DRAFT'))

    def test_intid_not_linux_irq_number(self):
        self.reject(lambda s: s['gp_control_profiles']['gp_control_probe_v1']['irq'].update(spi=114))

    def test_motor_command_scope_cannot_expand(self):
        self.reject(lambda s: s['gp_control_profiles']['gp_control_probe_v1']['supported_commands'].append('START'))

    def test_offset_cannot_escape_window(self):
        self.reject(lambda s: s['registers'][0].update(offset=4096))

    def test_offset_alignment(self):
        self.reject(lambda s: s['registers'][0].update(offset=2))

    def test_offset_alias(self):
        self.reject(lambda s: s['registers'][1].update(offset=0))

    def test_address_width_cannot_drop_high_bit(self):
        self.reject(lambda s: s['gp_control_profiles']['gp_control_probe_v1']['address'].update(address_width=32))

    def test_existing_resources_not_reused(self):
        p = self.schema['gp_control_profiles']['gp_control_probe_v1']
        self.reject(lambda s: s['gp_control_profiles']['gp_control_probe_v1']['address'].update(base=p['address']['legacy_avoidance']['base']))

    def test_level_interrupt_not_silently_edge(self):
        self.reject(lambda s: s['gp_control_profiles']['gp_control_probe_v1']['irq'].update(trigger='edge-rising'))

    def test_stale_evidence(self):
        self.run_schema()
        with self.assertRaises(gate.ContractError):
            gate.check(self.root, {'status':'READY_FOR_BSP_INTEGRATION', 'schema_sha256':'0'*64})

if __name__ == '__main__':
    unittest.main()
