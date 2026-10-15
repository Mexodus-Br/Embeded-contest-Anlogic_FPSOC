"""Verify a freshly extracted partner ZIP independently of the source tree."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
archive = ROOT / "deliverables/ps_partner_v1_ffc67e0.zip"
scratch = ROOT / ".tmp"
scratch.mkdir(exist_ok=True)
destination = Path(tempfile.mkdtemp(prefix="合作方 解压验证_", dir=scratch)).resolve()
with zipfile.ZipFile(archive) as stream:
    if stream.testzip() is not None:
        raise RuntimeError("ZIP CRC check failed")
    for member in stream.infolist():
        name = PurePosixPath(member.filename)
        resolved = (destination / member.filename).resolve()
        if name.is_absolute() or ".." in name.parts or destination not in resolved.parents:
            raise RuntimeError("Unsafe archive member")
    stream.extractall(destination)
package = destination / "ps_partner_v1"
environment = os.environ.copy()
environment.pop("PYTHONPATH", None)
result = subprocess.run([sys.executable, str(package / "tools/smoke.py")], cwd=package,
                        env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace", timeout=300)
print(result.stdout)
record = {"archive": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
          "bytes": archive.stat().st_size, "fresh_extraction": str(package),
          "exit_code": result.returncode, "stdout": result.stdout,
          "note": "Host-only Windows verification; no board/BSP access; extracted build/logs retained."}
report = package / ".smoke/report.json"
if report.exists():
    record["smoke"] = json.loads(report.read_text(encoding="utf-8"))
path = archive.with_name(archive.stem + "_verification.json")
path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Verification report:", path)
sys.exit(result.returncode)
