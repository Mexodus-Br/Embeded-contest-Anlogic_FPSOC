"""Build an allowlisted, pinned, reproducible host-only PS partner ZIP."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUTHOR = ROOT / "handoff/ps_partner_v1"
DEFAULT_COMMIT = "ffc67e05dbc7a8fb5559b5753c035ca26b9e815c"
PACKAGE_VERSION = "1.1"
RELEASE_DATE = "2026-10-22"
# Explicit release inputs only; no recursive guide/evidence collection.
GUIDES = ("README.md", "HOST_VALIDATION.md", "guides/PROJECT_CONTEXT.md",
          "guides/WORK_PLAN.md", "guides/BOUNDARIES.md", "guides/DELIVERY_CHECKLIST.md",
          "guides/LOG_VIEW_DOWNLOAD.md", "tools/smoke.py")
CURRENT_REFERENCES = (
    "pl_safety/INTERLOCK_CONTRACT.md",
    "integration/controlled_v1_20261021/REVIEW.md",
    "integration/controlled_v1_20261021/ACCEPTANCE.md",
    "integration/controlled_v1_20261021/BOOT_CANDIDATE.md",
    "bsp/wifi/http/BUILD_STATUS.md",
    "bsp/motor_test/BUILD_STATUS.md",
)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def selection(commit):
    files = {}

    def add(path, role, target=None):
        files[target or path] = (path, role)

    for name in ("README.md", "NOTICE.md", "SOURCE_ANALYSIS.md", "VALIDATION.md", "build.py", "generate_vectors.py",
                 "src/model.hpp", "src/model.cpp", "src/main.cpp", "configs/firmware_reference.cfg",
                 "tests/Arduino.h", "tests/oracle.cpp", "tests/test_regression.py", "vectors/firmware_host.json"):
        add("golden_model/" + name, "golden_host_reference")
    for line in git("ls-tree", "-r", "--name-only", commit, "golden_model/baseline").decode().splitlines():
        add(line, "unchanged_golden_provenance")
    for name in ("schema.json", "motion_v2.py", "generate.py", "tests/test_motion_v2.py",
                 "generated/interface_defs.h", "generated/interface_defs.vh", "generated/registers.md", "generated/errors.md"):
        add("pl_interface/" + name, "canonical_schema_and_motion_codec")
    for name in ("schema.json", "rate_design.json", "software/rs485_gp.h", "software/rs485_gp.c",
                 "software/rs485_telem.h", "software/rs485_telem.c", "tests/test_gp_software.c", "tests/test_telem_software.c",
                 "tools/generate_gp.py", "tools/generate_telem.py", "generated/rs485_defs.h",
                 "generated/gp_defs.h", "generated/gp_defs.vh", "generated/gp_registers.md",
                 "generated/telem_defs.h", "generated/telem_defs.vh", "generated/telem_registers.md"):
        add("pl_rs485/" + name, "telemetry_decoder_and_definitions")
    add("pl_rs485/evidence/telemetry_unit_final/frames.hex", "frozen_rtl_not_board_sample", "samples/telemetry_rtl_frames.hex")
    for name in ("pl_motion/MOTION_HANDOFF.md", "pl_rs485/RS485_DMA_HANDOFF.md",
                 "pl_rs485/optimization/OPTIMIZATION_HANDOFF.md"):
        add(name, "historical_delivery_reference", "reference/" + Path(name).name)
    for name in ("bsp/scope/delta_scope.cpp", "bsp/motion/motion_uapi.h", "bsp/motion/mot2_codec.h",
                 "bsp/telemetry/rs485_uapi.h"):
        add(name, "board_reference_only_not_host_build", "reference/board/" + Path(name).name)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", default=DEFAULT_COMMIT)
    parser.add_argument("--context-commit", default="HEAD",
                        help="Pinned approved requirements, guides and current status; base code stays separate")
    args = parser.parse_args()
    commit = git("rev-parse", args.source_commit + "^{commit}").decode().strip()
    context = git("rev-parse", args.context_commit + "^{commit}").decode().strip()
    payload, records = {}, []

    def store(target, data, **meta):
        path = PurePosixPath(target)
        if path.is_absolute() or ".." in path.parts or target in payload:
            raise RuntimeError("Unsafe/duplicate archive path: " + target)
        if any(x in path.parts for x in (".git", ".aws", ".codex", ".agents", "__pycache__")):
            raise RuntimeError("Forbidden archive path: " + target)
        if path.suffix.lower() in (".exe", ".ko", ".vvp", ".img", ".bit", ".hpf", ".dtb", ".zip", ".log"):
            raise RuntimeError("Forbidden compiled/board payload: " + target)
        if re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", data):
            raise RuntimeError("Private key in payload: " + target)
        payload[target] = data
        records.append({"path": target, "bytes": len(data), **meta})

    def pinned(target, source, role, revision):
        spec = revision + ":" + source
        store(target, git("show", spec), source_path=source, source_commit=revision,
              source_git_blob=git("rev-parse", spec).decode().strip(), role=role, origin="pinned_git")

    for target, (source, role) in sorted(selection(commit).items()):
        pinned(target, source, role, commit)
    pinned("PS_REQUIREMENTS_V1.md", "PS_REQUIREMENTS_V1.md", "approved_requirements_v1_1", context)
    for name in GUIDES:
        pinned(name, "handoff/ps_partner_v1/" + name, "curated_partner_guide_or_host_tool", context)
    for source in CURRENT_REFERENCES:
        # Preserve path identity: two BUILD_STATUS.md files must not collide.
        pinned("reference/current/" + source, source, "current_context_not_base_code_or_deployment_permission", context)
    records.sort(key=lambda x: x["path"])
    manifest = {"package": "ps_partner_v1", "package_version": PACKAGE_VERSION,
                "created_date": RELEASE_DATE, "source_commit": commit, "context_commit": context,
                "requirements_status": "functional_v1_1_adds_log_view_download_API_and_numeric_parameters_open",
                "four_g_extension_planned": False,
                "new_scope": "authenticated application log viewing, filtering, pagination, detail and download",
                "hash_scope": "ONE final partner ZIP only; no per-file, log, sample or evidence hashes computed",
                "hardware_integration_owner": "project_team_not_partner",
                "file_count_excluding_manifest": len(records), "uncompressed_bytes_excluding_manifest": sum(x["bytes"] for x in records),
                "selection_policy": "explicit_allowlist; no credentials, binaries, BSP build/deploy scripts, vendor IP or full logs",
                "files": records}
    payload["PACKAGE_MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    output = ROOT / "deliverables"
    output.mkdir(exist_ok=True)
    archive = output / ("ps_partner_v1_1_20261022_" + context[:7] + ".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as stream:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo("ps_partner_v1/" + name, (2026, 10, 22, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            stream.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(digest + "  " + archive.name + "\n", encoding="ascii")
    print(json.dumps({"archive": str(archive), "sha256": digest, "compressed_bytes": archive.stat().st_size,
                      "files": len(payload), "source_commit": commit, "context_commit": context,
                      "package_version": PACKAGE_VERSION}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
