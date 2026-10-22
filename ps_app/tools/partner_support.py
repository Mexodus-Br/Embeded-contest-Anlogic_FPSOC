"""Shared host compiler setup for the partner baseline and PS libraries."""
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "ps_partner_v1_1_20261022_005289b" / "ps_partner_v1"
OUT = ROOT / "build" / "partner"


def compiler(zig=None, target="native"):
    if target == "sdk":
        cc, cxx = os.environ.get("PS_CC"), os.environ.get("PS_CXX")
        if not cc or not cxx:
            raise RuntimeError("SDK requires PS_CC and PS_CXX from the target Buildroot/Linaro environment")
        flags = ["--sysroot=" + os.environ["PS_SYSROOT"]] if os.environ.get("PS_SYSROOT") else []
        return {"cc": cc, "c++": cxx}, flags
    zig = zig or os.environ.get("ZIG") or shutil.which("zig")
    if zig:
        command = [str(zig)]
        arch = "aarch64-linux-musl" if target == "aarch64" else (
            "x86_64-windows-gnu" if os.name == "nt" else "native")
        return command, ["-target", arch] + (["-static"] if target == "aarch64" else [])
    if target != "native":
        raise RuntimeError("Cross compilation requires --zig or ZIG")
    cxx, cc = shutil.which("g++"), shutil.which("gcc")
    if not cxx or not cc:
        raise RuntimeError("Provide GCC/G++ on PATH, or --zig PATH / ZIG")
    return {"c++": cxx, "cc": cc}, []


def compile_sources(sources, destination, toolchain, *, cxx=True, includes=(), extra=(), libraries=()):
    command, target_flags = toolchain
    language = "c++" if cxx else "cc"
    prefix = [command[language]] if isinstance(command, dict) else command + [language]
    flags = ["-std=c++17" if cxx else "-std=c11", "-O0", "-Wall", "-Wextra",
             "-Wpedantic", "-fno-fast-math", "-ffp-contract=off", *target_flags]
    args = prefix + flags + list(extra) + ["-I" + str(p) for p in includes] + list(map(str, sources)) + ["-o", str(destination)] + list(libraries)
    env = os.environ.copy()
    env["ZIG_GLOBAL_CACHE_DIR"] = str(ROOT / ".cache" / "zig-global")
    env["ZIG_LOCAL_CACHE_DIR"] = str(ROOT / ".cache" / "zig-partner")
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(args, check=True, env=env, cwd=ROOT, timeout=180)
    return args
