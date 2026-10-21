"""Verify final SD file partitions and actual contents, without mounting or devices."""
from pathlib import Path
import json,struct,subprocess,zipfile,tempfile,re,hashlib
H=Path(__file__).resolve().parent; P=H.parent; T=P/'boot_candidate_v1'; R=T/'output/release'
m=json.loads((R/'manifest.json').read_text());image=R/'sdcard.img'
def equal_segment(stream,source):
    with source.open('rb') as f:
        while True:
            chunk=f.read(1024*1024)
            if not chunk:break
            assert stream.read(len(chunk))==chunk,source.name
with image.open('rb') as f:
    mbr=f.read(512);assert mbr[510:]==b'\x55\xaa'
    sig=struct.unpack_from('<I',mbr,440)[0];assert f'{sig:08x}-02'==m['root_partuuid']
    for i,p in enumerate(m['partitions']):
        kind,start,count=struct.unpack_from('<B3xII',mbr,450+16*i)
        assert (start,count)==(p['start_sector'],p['sectors'])
        assert kind==[0x0c,0x83][i]
        f.seek(start*512);equal_segment(f,R/['boot.vfat','rootfs.ext4'][i])
assert image.stat().st_size==512*1024*1024
with (R/'rootfs.ext4').open('rb') as f:equal_segment(f,P/'build/rootfs-offline-complete.ext4')
with zipfile.ZipFile(R/'system.hpf') as z:
    assert z.read('HPFs/system.bit')==(R/'system.bit').read_bytes()
    header=z.read('HPFs/soc_plat.h').decode()
    assert re.search(r'#define\s+DDRC_IO_VOL\s+1\.35\b',header)
    assert re.search(r'#define\s+DDRC_DQ_WIDTH\s+32\b',header)
with tempfile.TemporaryDirectory() as directory:
    d=Path(directory)
    fat=f'{image}@@{m["partitions"][0]["start_sector"]*512}'
    for name in ['BOOT.bin','boot.scr','system.dtb','uImage.lz4']:
        subprocess.check_call(['mcopy','-i',fat,'::/'+name,str(d/name)])
        assert (d/name).read_bytes()==(R/name).read_bytes(),name
subprocess.check_call(['fsck.vfat','-n',str(R/'boot.vfat')])
subprocess.check_call(['e2fsck','-fn',str(R/'rootfs.ext4')])
dis=(T/'output/fsbl/disassembly.txt').read_text()
assert re.search(r'\bbl\s+[0-9a-f]+ <AlTop_GPPortEnable>',dis)
assert re.search(r'\bbl\s+[0-9a-f]+ <AlTop_P2F_RstRelease>',dis)
gp=re.search(r'^[0-9a-f]+ <AlTop_GPPortEnable>:(.*?)(?=^[0-9a-f]+ <)',dis,re.M|re.S)[1]
assert '#0x33' in gp and ('#0xffffffcc' in gp or '#0xffffffffffffffcc' in gp)
assert re.search(r'#0x[0-9a-f]*f880',gp) and 'str' in gp
base=Path.home()/'embedded-bsp/sdk/master_sdk'
sdk=T/'sdk/master_sdk'
for name in ['inc/soc_plat.h','src/soc_plat.c']:
    data=(sdk/'solutions/boards/project_controlled_v1'/name).read_text()
    with zipfile.ZipFile(R/'system.hpf') as z:raw=z.read('HPFs/'+Path(name).name).decode().replace('\r\n','\n')
    assert data.startswith(raw),name
assert (T/'output/boot/uImage.lz4').read_bytes()==(Path.home()/'embedded-bsp-wifi-20261018/output/boot/uImage.lz4').read_bytes()
assert (T/'output/boot/u-boot.bin').read_bytes()==(Path.home()/'embedded-bsp-wifi-20261018/output/boot/u-boot.bin').read_bytes()
# Revalidate only the named final-delivery artifact hashes, never logs/intermediates.
for name,record in m['files'].items():
    assert name in {'sdcard.img','BOOT.bin','system.hpf','system.bit','fsbl.elf','u-boot.bin','system.dtb','uImage.lz4','rootfs.ext4','boot.cmd','boot.scr','boot.bif'}
    h=hashlib.sha256()
    with (R/name).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    assert h.hexdigest()==record['sha256'] and (R/name).stat().st_size==record['bytes'],name
m.update(status='OFFLINE_BOOT_IMAGE_VERIFIED_RELEASE_BLOCKED',candidate='controlled_v1_20261021',
    hardware='final fixed-pin rtl37_candidate_r5 from rtl_path38; full PROFILE2 fixture',
    setup_ns=0.078,hold_ns=0.020,clock_mhz=100,setup_gt_1ns_required_for_this_candidate=False,
    other_release_gates_waived=False,signoff_pass=False,all_control_nodes_disabled=True,
    board_booted=False,no_motor_accepted=False,mechanical_motion_authorized=False)
(R/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
result={'status':'PASS_OFFLINE_IMAGE_CONTENTS','root_partuuid':m['root_partuuid'],
    'partition_bytes_equal':True,'fat_boot_files_read_back_from_sd_image':True,
    'rootfs_bytes_equal_to_audited_final':True,'new_hpf_bit_equal':True,
    'new_fsbl_uses_new_hpf':True,'fsbl_gp_hp0_hp1_reset_mask_0x33_verified_in_disassembly':True,
    'kernel_wifi1_unchanged':True,'uboot_boot_macros_equal':True,
    'rootfs_existing_inventory_and_module_crc_audits_apply':True,
    'not_board_validation':True,'signoff_pass':False}
(T/'output/debug/boot-image-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
