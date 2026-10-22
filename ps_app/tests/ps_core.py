"""Independent numerical and wire compatibility checks for the PS pure library."""
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "ps_partner_v1_1_20261022_005289b/ps_partner_v1"
EXE = ROOT / "build/partner/native" / ("ps_core.exe" if os.name == "nt" else "ps_core")
FIXTURE = json.loads((ROOT / "scenarios/ps-host.json").read_text())

def batch(requests):
    result = subprocess.run([str(EXE)], input="".join(json.dumps(r) + "\n" for r in requests), text=True, encoding="utf-8", capture_output=True, check=True)
    rows = [json.loads(s) for s in result.stdout.splitlines()]
    assert len(rows) == len(requests)
    return rows

def run(r):
    return batch([r])[0]

class Core(unittest.TestCase):
    def test_reference_xyz_vectors(self):
        cases = json.loads((KIT / "golden_model/vectors/firmware_host.json").read_text())["cases"]
        cases = [c for c in cases if c["mode"] == "xyz" and all(math.isfinite(float(t)) for t in c["tokens"]) and max(abs(float(t)) for t in c["tokens"]) < 3e38]
        actual = batch([{"op": "ik", "xyz_mm": list(map(float, c["tokens"]))} for c in cases])
        for c, a in zip(cases, actual):
            expected = c["expected"]
            if a["ok"]:
                self.assertEqual(a["result"]["angles_rad"], expected["angles_rad"], c["id"])
                self.assertEqual(a["result"]["steps"], list(map(str, expected["absolute_steps"])) + ["0"], c["id"])
            else:
                self.assertTrue(any(v is None for v in expected["angles_rad"] + expected["absolute_steps"]), c["id"])

    def test_trapezoid_independent_equations(self):
        r = run(FIXTURE)["result"]
        self.assertTrue(r["executable"])
        self.assertEqual(r["duration_us"], "450000")
        self.assertEqual(r["target"]["steps"], ["-1089", "-966", "-1213", "0"])
        self.assertEqual(sum(int(p["duration_us"]) for p in r["samples"]), 450000)
        for sample in r["samples"]:
            t = int(sample["time_us"]) / 1e6
            x = 50*t*t if t < .2 else 20*(t-.1) if t <= .25 else 5-50*(.45-t)**2
            self.assertAlmostEqual(sample["xyz_mm"][0], x, places=10)
            self.assertEqual(sample["xyz_mm"][1:], [0, -140])
        self.assertEqual(r["samples"][-1]["speed_mm_s"], 0)

    def test_triangle_long_duration_and_multiple_legs(self):
        for distance, duration in ((.01, None), (5, "1000000")):
            r = copy.deepcopy(FIXTURE)
            r["points"] = [{"xyz_mm": [distance,0,-140]}, {"xyz_mm": [0,0,-140], "dwell_us":"50000"}]
            if duration: r["points"][0]["duration_us"] = duration
            out = run(r)
            self.assertTrue(out["ok"], out)
            out = out["result"]
            self.assertEqual(out["legs"][0]["profile"], "triangle" if duration is None else "trapezoid")
            if duration: self.assertEqual(out["legs"][0]["duration_us"], duration)
            self.assertEqual(out["samples"][-1]["steps"], FIXTURE["start"]["steps"])
            self.assertEqual(sum(x["end"] for x in out["samples"]), 1)
            self.assertEqual(out["samples"][-1]["duration_us"], "50000")

    def test_invalid_path_and_boundaries(self):
        mutations = [
            (lambda r: r["points"][0].update(duration_us="1000"), "DURATION_INSUFFICIENT"),
            (lambda r: r["start"].update(steps=["0"]*4), "START_MISMATCH"),
            (lambda r: r["points"][0].update(xyz_mm=[0,0,0]), "IK_UNREACHABLE"),
            (lambda r: r["fixture"].update(max_samples="1"), "RESOURCE_LIMIT"),
            (lambda r: r["fixture"].update(pulse_interval_us="1000000"), "PULSE_RATE"),
            (lambda r: r["fixture"].update(forbidden_boxes=[{"min":[2.123,-1,-141],"max":[2.124,1,-139]}]), "PATH_FORBIDDEN"),
            (lambda r: r["points"][0].update(duration_us=1000000), "FORMAT"),
            (lambda r: r.update(device="/dev/mem"), "FORMAT"),
        ]
        for mutation, code in mutations:
            r = copy.deepcopy(FIXTURE); mutation(r); out=run(r)
            self.assertFalse(out["ok"], out);self.assertEqual(out["error"]["code"], code)
            self.assertNotIn("samples", out)

    def test_unknown_start_only_explains_target(self):
        r = copy.deepcopy(FIXTURE);r["start"]={"valid":False,"position_id":"unknown","xyz_mm":None,"steps":None}
        out=run(r)["result"]
        self.assertFalse(out["executable"]);self.assertEqual(out["samples"], [])
        self.assertEqual(out["errors"][0]["code"], "POSITION_UNKNOWN")

    def test_motion_bytes_against_original_codec(self):
        spec=importlib.util.spec_from_file_location("motion_v2",KIT/"pl_interface/motion_v2.py");codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
        values=[-2**63, -9007199254740993, 9007199254740993, 2**63-1]
        for value in values:
            req={"op":"motion_encode","session_id":str(2**64-1),"sequence":2**32-1,"duration_us":"123456","steps":[str(value),"1","-1","0"],"end":True}
            out=run(req);self.assertTrue(out["ok"],out)
            raw=bytes.fromhex(out["result"]["hex_le"])
            original=codec.encode({"session_id":2**64-1,"sequence":2**32-1,"duration_tick":123456,"flags":1,"axis_mask":7,"target0":value,"target1":1,"target2":-1,"target3":0})
            self.assertEqual(raw, original);self.assertEqual(len(raw),72)
        req["steps"][3]="1";self.assertFalse(run(req)["ok"])

    def test_telemetry_records_and_corruption(self):
        lines=(KIT/"samples/telemetry_rtl_frames.hex").read_text().splitlines()
        out=batch([{"op":"telemetry_decode","hex":s,"byte_order":"verilog_msb_hex"} for s in lines])
        self.assertEqual(len(out),17);self.assertEqual(sum(r["result"]["data_valid"] for r in out),16)
        for line,r in zip(lines,out):
            b=bytes.fromhex(line)[::-1];row=r["result"]
            self.assertEqual(row["completion_serial"],str(int.from_bytes(b[20:28],"little")))
            self.assertEqual(row["event_us"],str((int.from_bytes(b[28:60],"little")>>48)&(2**64-1)))
            if not row["data_valid"]: self.assertIsNone(row["value"])
        raw=bytearray(bytes.fromhex(lines[0])[::-1]);requests=[]
        for i in range(64):
            corrupt=raw.copy();corrupt[i]^=1;requests.append({"op":"telemetry_decode","hex":corrupt.hex()})
        self.assertTrue(all(not r["ok"] for r in batch(requests)))
        # Valid CRC with >2^53 serial must remain exact at the JSON boundary.
        raw[20:28]=(2**64-2).to_bytes(8,"little");raw[60:]=struct.pack("<I",zlib.crc32(raw[:60]))
        self.assertEqual(run({"op":"telemetry_decode","hex":raw.hex()})["result"]["completion_serial"],str(2**64-2))

if __name__=="__main__":
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Core))
    (ROOT/'build/partner/core_report.json').write_text(json.dumps({'passed':result.wasSuccessful(),'test_methods':result.testsRun,'scope':'host_pure_library'},indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
