"""Package authorized local FD SDK for SCP transfer, preserving source files."""
from pathlib import Path
import tarfile
p = Path(__file__).resolve().parents[1] / 'work/master-sdk.tar.gz'
with tarfile.open(p, 'w:gz') as t:
    t.add(r'D:\Anlogic\FD_2026.1_SP1\data\embeddedsw\master_sdk', arcname='master_sdk')
print(p, p.stat().st_size)
