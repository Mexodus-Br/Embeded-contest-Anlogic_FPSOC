"""Build PS C++17 libraries and host CLI; no hardware access."""
import argparse
import json
import os
from partner_support import KIT, ROOT, OUT, compile_sources, compiler

def build(zig=None, target="native", server=False):
    tc = compiler(zig, target)
    output = OUT / target
    objects = []
    for name in ("rs485_gp", "rs485_telem"):
        obj = output / (name + ".o")
        compile_sources([KIT / "pl_rs485/software" / (name + ".c")], obj, tc, cxx=False, extra=["-c"])
        objects.append(obj)
    suffix = ".exe" if os.name == "nt" and target == "native" else ""
    base = [ROOT / "src/ps_core.cpp", KIT / "golden_model/src/model.cpp", *objects]
    includes = [ROOT / "src", ROOT / "third_party", KIT]
    commands = [compile_sources(base + [ROOT / "src/ps_cli.cpp"], output / ("ps_core" + suffix), tc, includes=includes)]
    if server:
        commands.append(compile_sources(base + [ROOT / "src/ps_backend.cpp", ROOT / "src/ps_runtime.cpp", ROOT / "src/ps_service.cpp", ROOT / "src/ps_server.cpp"], output / ("ps_server" + suffix), tc,
                                        includes=includes, libraries=["-lws2_32", "-lbcrypt"] if os.name == "nt" and target == "native" else (["-pthread", "-lstdc++fs"] if target == "sdk" else ["-pthread"])))
    (output / "build_info.json").write_text(json.dumps({"target": target, "commands": commands, "hardware_access": False}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zig")
    p.add_argument("--target", choices=["native", "aarch64", "sdk"], default="native")
    p.add_argument("--server", action="store_true")
    a = p.parse_args()
    build(a.zig, a.target, a.server)
