"""Additional fixed-export checks, plus the unchanged Wi-Fi HTTP regression."""
from pathlib import Path
import importlib.util
import unittest
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('original_tests',str(H/'frozen/software/bsp/wifi/http/test_http.py'))
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)


class Integration(original.HTTPTests):
    def test_fixed_diagnostic_export(self):
        self.assertIn(b'/files/integration-snapshot.json',self.request('/')[2])
        route='/files/integration-snapshot.json'
        self.assertEqual(self.request(route,auth=False)[0],401)
        self.assertEqual(self.request(route)[0],404)
        body=b'{"source":"OFFLINE_TEST_ONLY"}\n'
        (self.root/'exports/integration-snapshot.json').write_bytes(body)
        for _ in range(3):self.assertEqual(self.request(route)[2],body)
        self.assertEqual(self.request(route,'POST')[0],405)
        self.assertEqual(self.request('/files/../integration-snapshot.json')[0],403)


if __name__=='__main__':unittest.main()
