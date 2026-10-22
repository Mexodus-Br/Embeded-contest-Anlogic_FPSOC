"""Generate expectations ONLY from the separately compiled original-source oracle."""
import argparse
import json
import math
from pathlib import Path
import random
import struct
import subprocess
from build import ROOT, BUILD, build, verify_baseline

SEED = 20261007
def f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]

def cases():
    result = []
    def add(group, mode, values):
        result.append({"id": f"{group}_{len(result):04d}", "group": group, "mode": mode,
                       "tokens": [str(v).lower() for v in values]})
    for p in [(0,0,-140),(0,0,-220),(30,20,-200),(-30,20,-200),(30,-20,-200),
              (-30,-20,-200),(110,110,-300),(110.001,0,-200),(0,0,-300.001),
              (0,0,-139),(0,0,0),(0,0,100),(500,0,-200),(0,0,-1000)]:
        add("representative", "xyz", p)
    d = f32(f32(83.7)-f32(30.4))
    for radius in (130,430):
        z = -math.sqrt(radius*radius-d*d)
        for dz in (-0.01,-0.0001,0,0.0001,0.01):
            add("boundary", "xyz", (0,0,z+dz))
    # Tangent-half-angle denominator pole, approached from both sides.
    pole = 150-math.sqrt(280**2-d*d)
    for dz in (-0.01,-0.00001,0,0.00001,0.01):
        add("pole", "xyz", (0,0,pole+dz))
    for p in [("nan",0,-200),(0,"inf",-200),(0,0,"-inf"),(0,0,"inf"),
              ("1e30",0,-200),("1e100",0,-200),("-0",0,-140)]:
        add("numeric", "xyz", p)
    for a in (-0.48,0,0.001,-0.001,1,-1,14.3,-14.3,"nan","inf",1e30):
        add("steps", "angles", (a,a,a))
    factor=f32(f32(4.5*3200)/2/math.pi)
    # Adjacent representable float angles around integer and half-step boundaries.
    for n in (-1091,-2,-1,-0.5,0.5,1,2,1091):
        angle=f32(n/factor)
        bits=struct.unpack("I",struct.pack("f",angle))[0]
        for shift in (-1,0,1):
            a=struct.unpack("f",struct.pack("I",bits+shift))[0]
            add("rounding", "angles", (a,-a,a))
    rng=random.Random(SEED)
    for _ in range(1000):
        add("random", "xyz", (rng.uniform(-180,180),rng.uniform(-180,180),rng.uniform(-480,50)))
    for i in range(201):
        t=i/200
        add("trajectory", "xyz", (-60+120*t,20*math.sin(2*math.pi*t),-220+20*math.cos(2*math.pi*t)))
    return result

def oracle(records):
    data="".join(r["mode"]+" "+" ".join(r["tokens"])+"\n" for r in records)
    output=subprocess.check_output([str(BUILD/"firmware_oracle.exe")],input=data,text=True)
    rows=[json.loads(line) for line in output.splitlines()]
    if len(rows)!=len(records):
        raise RuntimeError("oracle row count mismatch")
    return rows

def generate(destination):
    records=cases()
    for record,expected in zip(records,oracle(records)):
        record["expected"]=expected
    manifest=verify_baseline()
    payload={"schema_version":1,"seed":SEED,"expectation_source":"unchanged original C++ sources + host Arduino shim",
             "numeric_profile":"host_float32_double64","baseline_sha256":{r["file"]:r["sha256"] for r in manifest["files"]},
             "build_info":json.loads((BUILD/"build_info.json").read_text()),"cases":records}
    destination.write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(f"Generated {len(records)} original-source reference cases: {destination}")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=ROOT/"vectors/firmware_host.json")
    p.add_argument("--no-build",action="store_true")
    a=p.parse_args()
    if not a.no_build: build()
    generate(a.output)
