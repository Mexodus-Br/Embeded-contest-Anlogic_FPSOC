"""Build host extraction and byte-identical source oracle, without downloads."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"

def verify_baseline():
    manifest = json.loads((ROOT / "baseline/manifest.json").read_text(encoding="utf-8-sig"))
    for record in manifest["files"]:
        path = ROOT / "baseline" / record["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise RuntimeError(f"baseline SHA-256 mismatch: {path}")
    return manifest

def build(compiler="g++"):
    verify_baseline()
    exe = shutil.which(compiler)
    if exe is None:
        raise RuntimeError(f"C++ compiler not found: {compiler}")
    BUILD.mkdir(exist_ok=True)
    flags = [exe, "-std=c++17", "-O0", "-Wall", "-Wextra", "-Wpedantic", "-fno-fast-math", "-ffp-contract=off"]
    version = subprocess.check_output([exe, "--version"], text=True).splitlines()[0]
    commands = [
        flags + [str(ROOT / "src/model.cpp"), str(ROOT / "src/main.cpp"), "-o", str(BUILD / "delta_model.exe")],
        flags + ["-I" + str(ROOT / "tests"), "-I" + str(ROOT / "baseline"), str(ROOT / "tests/oracle.cpp"),
                 str(ROOT / "baseline/robotGeometry.cpp"), str(ROOT / "baseline/RampsStepper.cpp"), "-o", str(BUILD / "firmware_oracle.exe")],
    ]
    for command in commands:
        subprocess.run(command, check=True)
    metadata = {"compiler": version, "compiler_path": exe, "commands": commands, "python": sys.version,
                "numeric_profile": "host_float32_double64", "avr_execution_verified": False}
    (BUILD / "build_info.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(version)
    return metadata

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="g++")
    args = parser.parse_args()
    try:
        build(args.compiler)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")
