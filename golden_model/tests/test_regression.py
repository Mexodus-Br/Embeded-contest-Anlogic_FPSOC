"""Original source fidelity, independent geometry, diagnostics and config tests."""
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build import ROOT, BUILD, build, verify_baseline
from generate_vectors import oracle, f32

CONFIG=ROOT/"configs/firmware_reference.cfg"
def run(records, config=CONFIG):
    data="".join(r["mode"]+" "+" ".join(r["tokens"])+"\n" for r in records)
    output=subprocess.check_output([str(BUILD/"delta_model.exe"),"--config",str(config),"--batch"],input=data,text=True)
    return [json.loads(line) for line in output.splitlines()]

def record(mode,*values):
    return {"mode":mode,"tokens":[str(v).lower() for v in values]}

class Regression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline=verify_baseline()
        cls.fixture=json.loads((ROOT/"vectors/firmware_host.json").read_text())
        cls.cases=cls.fixture["cases"]
        cls.outputs=run(cls.cases)
        cls.metrics={"reference_cases":len(cls.cases),"numeric_profile":"host_float32_double64",
                     "avr_execution_verified":False}

    def test_baseline_and_fixture_provenance(self):
        self.assertEqual(self.fixture["baseline_sha256"],{r["file"]:r["sha256"] for r in self.baseline["files"]})
        # Existing original files, when available, must still match this capture.
        for r in self.baseline["files"]:
            original=Path(r["original_path"])
            if original.exists(): self.assertEqual(original.read_bytes(),(ROOT/"baseline"/r["file"]).read_bytes())

    def test_frozen_vectors_against_live_original(self):
        for c,actual in zip(self.cases,oracle(self.cases)):
            with self.subTest(case=c["id"]): self.assertEqual(c["expected"],actual)

    def test_extraction_against_original(self):
        self.assertEqual(len(self.outputs),len(self.cases))
        valid=0
        for c,out in zip(self.cases,self.outputs):
            with self.subTest(case=c["id"]):
                # Same compiler/profile: exact float equality and exact integer steps.
                self.assertEqual(c["expected"]["angles_rad"],out["angles_rad"])
                expected=c["expected"]["absolute_steps"]
                if out["valid"]:
                    self.assertEqual(expected,out["absolute_steps"]);valid+=1
                else: self.assertIsNone(out["absolute_steps"])
                if c["mode"]=="angles": self.assertEqual(out["steps_valid"],all(s is not None for s in expected))
        self.metrics.update(valid_reference_cases=valid,invalid_reference_cases=len(self.cases)-valid)

    def test_independent_rod_lengths(self):
        # Cartesian elbow construction from geometry, not the IK quadratic.
        # 64 float32 eps * 430 mm gives 0.00328125 mm temporary host check bound.
        tolerance=64*2**-23*430
        R,r,L,l=map(f32,(83.7,30.4,150,280));D=f32(R-r)
        axes=((0,-1),(-math.sqrt(3)/2,0.5),(math.sqrt(3)/2,0.5))
        worst=0;count=0
        for case,out in zip(self.cases,self.outputs):
            if case["mode"]!="xyz" or not out["ik_valid"]:continue
            x,y,z=out["input"]
            for angle,(ux,uy) in zip(out["angles_rad"],axes):
                elbow=(ux*(D+L*math.cos(angle)),uy*(D+L*math.cos(angle)),-L*math.sin(angle))
                length=math.sqrt((x-elbow[0])**2+(y-elbow[1])**2+(z-elbow[2])**2)
                error=abs(length-l);worst=max(worst,error);count+=1
                with self.subTest(case=case["id"]):self.assertLessEqual(error,tolerance)
        self.metrics.update(geometry_checks=count,max_rod_error_mm=worst,provisional_rod_tolerance_mm=tolerance)

    def test_symmetry_and_manual_center_example(self):
        a,b=run([record("xyz",30,20,-200),record("xyz",-30,20,-200)])
        self.assertEqual(a["angles_rad"][0],b["angles_rad"][0])
        self.assertEqual(a["angles_rad"][1],b["angles_rad"][2])
        self.assertEqual(a["angles_rad"][2],b["angles_rad"][1])
        # Hand-checkable center equation D*cos(theta)+z*sin(theta) = -C/(2L).
        out=run([record("xyz",0,0,-140)])[0]
        D=f32(f32(83.7)-f32(30.4));z=-140;L=150;l=280
        C=z*z+D*D+L*L-l*l
        theta=math.atan2(z,D)+math.acos(-C/(2*L*math.hypot(D,z)))
        for a in out["angles_rad"]:self.assertLess(abs(a-theta),2e-6)
        self.assertEqual(out["absolute_steps"],[-1090]*3)
        self.assertEqual(run([record("angles",-0.48,-0.48,-0.48)])[0]["absolute_steps"],[-1100]*3)

    def test_failures_and_legacy_box(self):
        unreachable,upper,nan,overflow=run([record("xyz",0,0,0),record("xyz",0,0,100),
                                          record("xyz","nan",0,-200),record("xyz",1e30,0,-200)])
        self.assertFalse(unreachable["valid"])
        self.assertIn("negative_discriminant",unreachable["ik_reasons"])
        self.assertTrue(unreachable["firmware_box_allowed"])
        self.assertTrue(upper["firmware_box_allowed"])
        self.assertIn("nonfinite_input",nan["ik_reasons"])
        self.assertIn("nonfinite_intermediate",overflow["ik_reasons"])
        # Exact denominator singularity using a deliberately simple, declared test config.
        cfg=BUILD/"singular.cfg";cfg.write_text("base_radius_mm=0\neffector_radius_mm=0\n")
        singular=run([record("xyz",0,0,-130)],cfg)[0]
        self.assertFalse(singular["ik_valid"])
        self.assertIn("zero_denominator",singular["ik_reasons"])
        self.assertEqual(singular["K"],[0,0,0])

    def test_steps_offsets_rounding_and_direction(self):
        cfg=BUILD/"offsets.cfg"
        cfg.write_text("angle_offset_x_rad=0.25\nangle_offset_y_rad=-0.25\nstep_offset_x=10\nstep_offset_y=-10\ninverse_x=0\n")
        out=run([record("angles",0,0,0)],cfg)[0]
        self.assertEqual(out["absolute_steps"],[582,-582,0])
        base=run([record("angles",1,-1,0)])[0]
        cfg.write_text("inverse_x=0\ninverse_y=0\ninverse_z=0\n")
        self.assertEqual(run([record("angles",1,-1,0)],cfg)[0]["absolute_steps"],base["absolute_steps"])
        # Exact factor 1: ratio float rounds to float(2*pi), then divide by double PI rounds to 1.
        cfg.write_text("main_gear_teeth=6.283185307179586\nmotor_gear_teeth=1\nmicrosteps=1\nsteps_per_rev=1\n")
        out=run([record("angles",1.999,-1.999,0.999)],cfg)[0]
        self.assertEqual(out["rad_to_step_factor"],1)
        self.assertEqual(out["absolute_steps"],[1,-1,0])
        out=run([record("angles",32768,-32769,1)],cfg)[0]
        self.assertFalse(out["valid"]);self.assertEqual(out["step_reasons"][:2],["step_range_exceeded"]*2)

    def test_config_replacement_and_invalid_configs(self):
        cfg=BUILD/"replacement.cfg"
        cfg.write_text("upper_length_mm=160\nlower_length_mm=290\n")
        out=run([record("xyz",0,0,-200)],cfg)[0]
        self.assertTrue(out["valid"])
        self.assertNotEqual(out["angles_rad"],run([record("xyz",0,0,-200)])[0]["angles_rad"])
        for text in ("unknown=1\n","upper_length_mm=0\n","microsteps=1.5\n","motor_gear_teeth=0\n",
                     "base_radius_mm=nan\n","microsteps=2000000000\n","inverse_x=2\n","target_min=5\ntarget_max=4\n",
                     "steps_per_rev=200\nsteps_per_rev=200\n"):
            cfg.write_text(text)
            p=subprocess.run([str(BUILD/"delta_model.exe"),"--config",str(cfg),"xyz","0","0","-200"],capture_output=True)
            self.assertEqual(p.returncode,2)

    def test_continuous_trajectory(self):
        trajectory=[o for c,o in zip(self.cases,self.outputs) if c["group"]=="trajectory"]
        self.assertEqual(len(trajectory),201)
        self.assertTrue(all(o["valid"] for o in trajectory))
        angle_delta=max(abs(b-a) for p,q in zip(trajectory,trajectory[1:]) for a,b in zip(p["angles_rad"],q["angles_rad"]))
        step_delta=max(abs(b-a) for p,q in zip(trajectory,trajectory[1:]) for a,b in zip(p["absolute_steps"],q["absolute_steps"]))
        self.assertLess(angle_delta,0.02) # Continuity check for this fixed sampling, not a velocity limit.
        self.assertLess(step_delta,46) # 0.02 rad * reference factor plus truncation.
        self.metrics.update(trajectory_points=201,max_adjacent_angle_delta_rad=angle_delta,max_adjacent_step_delta=step_delta)
        with (BUILD/"trajectory.jsonl").open("w",encoding="utf-8") as stream:
            for i,o in enumerate(trajectory):
                row={"sample":i,**o}
                if i:
                    row["delta_angles_rad"]=[b-a for a,b in zip(trajectory[i-1]["angles_rad"],o["angles_rad"])]
                    row["delta_steps"]=[b-a for a,b in zip(trajectory[i-1]["absolute_steps"],o["absolute_steps"])]
                stream.write(json.dumps(row,allow_nan=False)+"\n")

    def test_cli_exit_codes_and_malformed_batch(self):
        exe=str(BUILD/"delta_model.exe")
        for args,expected in [(["xyz","0","0","-200"],0),(["xyz","0","0","0"],1),
                              (["xyz","0","0"],2),(["xyz","bad","0","-200"],2)]:
            p=subprocess.run([exe]+args,capture_output=True)
            self.assertEqual(p.returncode,expected)
        p=subprocess.run([exe,"--batch"],input="xyz 0 0\n",text=True,capture_output=True)
        self.assertEqual(p.returncode,2)

if __name__=="__main__":
    build()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Regression)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={**getattr(Regression,"metrics",{}),"test_methods":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
            "passed":result.wasSuccessful(),"build_info":json.loads((BUILD/"build_info.json").read_text())}
    (BUILD/"test_report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    sys.exit(0 if result.wasSuccessful() else 1)
