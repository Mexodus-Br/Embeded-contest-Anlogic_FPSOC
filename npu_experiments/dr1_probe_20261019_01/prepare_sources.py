"""Extract only needed vendor references from local packages; no hashing."""
from pathlib import Path
from zipfile import ZipFile
import tarfile

ROOT=Path(__file__).resolve().parent
DOCS=Path(r'D:\Works\Embedded_contest\docs\Analogic')
DEMO=DOCS/'01_start/02_start_Linux/05_application_demo/05-5_NPU演示/demo.zip'
with ZipFile(DEMO) as z:
    for name in z.namelist():
        if name.endswith('/'):
            continue
        if name in ['soc_prj/soc_prj.al','soc_prj/soc_prj_Runs/phy_1/soc_prj_phy.area'] or name.startswith('soc_prj/design_0/ip/design_0_Video_NPU_0/'):
            p=ROOT/'reference'/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(z.read(name))
with tarfile.open(DOCS/'sdk.2025.7.tar.gz',mode='r|gz') as archive:
    for member in archive:
        if member.isfile() and member.name.startswith('sdk/app/npu/scripts/'):
            p=ROOT/'sdk2025_reference'/member.name
            assert p.resolve().is_relative_to(ROOT.resolve())
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(archive.extractfile(member).read())
print('Vendor references extracted. Original package/RTL unchanged.')
