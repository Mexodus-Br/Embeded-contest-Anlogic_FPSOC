"""Run unchanged partner reference suites using GCC or Zig; never access devices.

The kit's smoke.py requires gcc/g++ executable names. This runner supports the
existing Zig compiler explicitly, without impersonating GCC or editing the kit.
"""
import argparse
import importlib.util
import json
import platform
import subprocess
import sys
import unittest
import zlib
from partner_support import KIT, OUT, compile_sources, compiler


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zig")
    args = parser.parse_args()
    toolchain = compiler(args.zig)
    manifest = json.loads((KIT / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    originals = {r["path"]: (KIT / r["path"]).read_bytes() for r in manifest["files"]}
    originals["PACKAGE_MANIFEST.json"] = (KIT / "PACKAGE_MANIFEST.json").read_bytes()
    commands = []
    for name in ("tools/smoke.py", "pl_interface/generate.py", "pl_rs485/tools/generate_gp.py",
                 "pl_rs485/tools/generate_telem.py", "pl_interface/tests/test_motion_v2.py"):
        flags = ["--verify-only"] if name == "tools/smoke.py" else (["--check"] if "generate" in name else [])
        subprocess.run([sys.executable, "-B", str(KIT / name), *flags], check=True, timeout=60)
    golden = KIT / "golden_model"
    commands.append(compile_sources([golden / "src/model.cpp", golden / "src/main.cpp"], OUT / "delta_model.exe", toolchain))
    commands.append(compile_sources([golden / "tests/oracle.cpp", golden / "baseline/robotGeometry.cpp", golden / "baseline/RampsStepper.cpp"],
                                   OUT / "firmware_oracle.exe", toolchain, includes=[golden / "tests", golden / "baseline"]))
    # Import original tests; relocate only their build/test output directory.
    sys.path.insert(0, str(golden))
    regression = module("partner_regression", golden / "tests/test_regression.py")
    regression.BUILD = OUT
    sys.modules["generate_vectors"].BUILD = OUT
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(regression.Regression)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError("Unchanged Golden regression suite failed")
    sources = [KIT / "pl_rs485/software" / n for n in ("rs485_gp.c", "rs485_telem.c")]
    for name in ("gp", "telem"):
        exe = OUT / (name + "_reference.exe")
        commands.append(compile_sources(sources + [KIT / "pl_rs485/tests" / ("test_" + name + "_software.c")], exe, toolchain, cxx=False))
        subprocess.run([str(exe)] + ([str(KIT / "samples/telemetry_rtl_frames.hex")] if name == "telem" else []), check=True, timeout=60)
    frames = [bytes.fromhex(s)[::-1] for s in (KIT / "samples/telemetry_rtl_frames.hex").read_text().splitlines() if s.strip()]
    assert len(frames) == 17
    assert all(len(f) == 64 and zlib.crc32(f[:60]) == int.from_bytes(f[60:], "little") for f in frames)
    assert all((KIT / name).read_bytes() == before for name, before in originals.items())
    report = {"passed": True, "scope": "host_only", "hardware_access": False,
              "runner": "tools/verify_partner.py (explicit alternative to GCC-only kit smoke)",
              "compiler": toolchain[0], "python": sys.version, "platform": platform.platform(),
              "package_version": manifest["package_version"], "distributed_originals_byte_equal": True,
              "golden": {**regression.Regression.metrics, "test_methods": result.testsRun},
              "motion_v2_tests": 3, "telemetry_frames": 17, "commands": commands}
    (OUT / "reference_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PARTNER_REFERENCE_PASS:", OUT / "reference_report.json")


if __name__ == "__main__":
    main()
