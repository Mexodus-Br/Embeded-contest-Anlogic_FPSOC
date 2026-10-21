"""Verify transported SD file and its embedded root partition; never open a disk."""
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[2];A=R/'bsp/artifacts/motor3125';W=R/'bsp/work/motor3125_soc_prj';D=R/'bsp/motor_test'
m=json.loads((A/'manifest.json').read_text())
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()
for name in ['sdcard.img','BOOT.bin','system.dtb','fsbl.elf']:
    p=A/name;assert p.stat().st_size==m['files'][name]['bytes']
    assert digest(p)==m['files'][name]['sha256'],name
for name in ['system.hpf','system.bit']:
    assert digest(W/name)==m['files'][name]['sha256'],name
with (A/'sdcard.img').open('rb') as f:
    b=f.read(512);assert b[510:512]==b'\x55\xaa'
    signature=struct.unpack_from('<I',b,440)[0]
    assert f'{signature:08x}-02'==m['root_partuuid']
    parts=[]
    for i in range(2):
        kind=b[446+i*16+4];start,count=struct.unpack_from('<II',b,446+i*16+8)
        parts.append((kind,start,count))
    assert parts==[(12,2048,131072),(131,133120,524288)]
    f.seek(parts[1][1]*512);h=hashlib.sha256();left=parts[1][2]*512
    while left:
        data=f.read(min(left,1024*1024));assert data;h.update(data);left-=len(data)
    assert h.hexdigest()==m['files']['rootfs.ext4']['sha256']
    f.seek(parts[1][1]*512+1024+56);assert f.read(2)==b'\x53\xef'
v=json.loads((A/'image-verification.json').read_text())
assert v['status']=='IMAGE_VERIFIED_NOT_DEPLOYED_OR_BOARD_TESTED'
assert v['sd_image_sha256']==m['files']['sdcard.img']['sha256']
proof={'status':'PASS_LOCAL_FILE_DOWNLOAD_AND_EMBEDDED_ROOT_VERIFIED','sd_image_sha256':m['files']['sdcard.img']['sha256'],
       'bytes':m['files']['sdcard.img']['bytes'],'root_partuuid':m['root_partuuid'],
       'physical_sd_write':'NOT_EXECUTED','cold_boot':'NOT_EXECUTED','motor_execution':'NOT_EXECUTED'}
(D/'IMAGE_VERIFICATION.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof,indent=2))
