"""Offline host-only checks for the curated partner kit; no device access."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]


def verify():
    manifest = json.loads((ROOT / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    seen = set()
    for row in manifest["files"]:
        if row["path"] in seen:
            raise RuntimeError("Duplicate member: " + row["path"])
        seen.add(row["path"])
        path = (ROOT / row["path"]).resolve()
        if ROOT not in path.parents or not path.is_file():
            raise RuntimeError("Missing or unsafe member: " + row["path"])
        data = path.read_bytes()
        if len(data) != row["bytes"]:
            raise RuntimeError("Size mismatch: " + row["path"])
    if manifest["file_count_excluding_manifest"] != len(seen):
        raise RuntimeError("Manifest file count mismatch")
    print("PASS package inventory/sizes: %d files; baseline %s" % (len(manifest["files"]), manifest["source_commit"][:12]))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    manifest = verify()
    if args.verify_only:
        return
    originals = {row["path"]: (ROOT / row["path"]).read_bytes() for row in manifest["files"]}
    original_manifest = (ROOT / "PACKAGE_MANIFEST.json").read_bytes()
    cc, cxx = shutil.which("gcc"), shutil.which("g++")
    if not cc or not cxx:
        raise RuntimeError("Install GCC/G++ with C++17 support and add gcc/g++ to PATH; Python 3.10+ is required.")
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10+ required")
    build = ROOT / ".smoke"
    build.mkdir(exist_ok=True)
    records = []

    def run(name, command):
        started = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", timeout=180)
        (build / (name + ".log")).write_text(result.stdout, encoding="utf-8")
        records.append({"name": name, "exit_code": result.returncode,
                        "seconds": round(time.monotonic() - started, 3), "command": list(map(str, command))})
        print(("PASS " if result.returncode == 0 else "FAIL ") + name, flush=True)
        if result.returncode:
            raise RuntimeError("See .smoke/" + name + ".log\n" + result.stdout[-2500:])

    for path in ("pl_interface/generate.py", "pl_rs485/tools/generate_gp.py", "pl_rs485/tools/generate_telem.py"):
        run("definitions_" + Path(path).stem, [sys.executable, path, "--check"])
    run("golden_regression", [sys.executable, "golden_model/tests/test_regression.py"])
    golden = json.loads((ROOT / "golden_model/build/test_report.json").read_text(encoding="utf-8"))
    if (golden["reference_cases"], golden["valid_reference_cases"], golden["invalid_reference_cases"]) != (1272, 826, 446):
        raise RuntimeError("Golden vector counts changed")
    run("motion_v2", [sys.executable, "pl_interface/tests/test_motion_v2.py"])
    sources = ["pl_rs485/software/rs485_gp.c", "pl_rs485/software/rs485_telem.c"]
    for name, test in (("gp_mock", "test_gp_software.c"), ("telemetry_decode", "test_telem_software.c")):
        exe = build / (name + ".exe")
        run(name + "_compile", [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
                                *sources, "pl_rs485/tests/" + test, "-o", str(exe)])
        command = [str(exe)]
        if name == "telemetry_decode":
            command.append(str(ROOT / "samples/telemetry_rtl_frames.hex"))
        run(name, command)
    frames = [bytes.fromhex(line)[::-1] for line in (ROOT / "samples/telemetry_rtl_frames.hex").read_text().splitlines() if line.strip()]
    if len(frames) != 17:
        raise RuntimeError("Expected 17 frozen telemetry frames")
    for frame in frames:
        if len(frame) != 64 or zlib.crc32(frame[:60]) != int.from_bytes(frame[60:], "little"):
            raise RuntimeError("Independent zlib/frame-byte-order check failed")
    print("PASS independent telemetry CRC/byte-order: 17 frames")
    verify()
    for name, before in originals.items():
        if (ROOT / name).read_bytes() != before:
            raise RuntimeError("Test modified distributed source: " + name)
    if (ROOT / "PACKAGE_MANIFEST.json").read_bytes() != original_manifest:
        raise RuntimeError("Test modified manifest")
    print("PASS distributed originals unchanged by direct byte comparison; no file/log hashes")
    report = {"passed": True, "hardware_access": False, "source_commit": manifest["source_commit"],
              "context_commit": manifest["context_commit"], "package_version": manifest["package_version"],
              "distributed_originals_byte_equal": True, "file_or_log_hashes_computed": False,
              "python": sys.version, "platform": sys.platform,
              "cc": subprocess.check_output([cc, "--version"], text=True).splitlines()[0],
              "cxx": subprocess.check_output([cxx, "--version"], text=True).splitlines()[0],
              "golden": {k: golden[k] for k in ("reference_cases", "valid_reference_cases", "invalid_reference_cases", "test_methods", "passed")},
              "telemetry_frames": 17, "telemetry_byte_corruptions_rejected": 1088,
              "checks": records, "report": ".smoke/report.json"}
    (build / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("HOST_ONLY_SMOKE_PASS; report .smoke/report.json")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as error:
        print("HOST_ONLY_SMOKE_FAIL: " + str(error), file=sys.stderr)
        sys.exit(1)
