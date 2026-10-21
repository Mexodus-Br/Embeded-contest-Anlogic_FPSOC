"""Build a reviewable SD *file* image without touching a disk or needing root."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import os
import time
os.environ['SOURCE_DATE_EPOCH'] = '1791676800'
os.environ['TZ'] = 'UTC'
time.tzset()

p = argparse.ArgumentParser()
p.add_argument('task', type=Path)
a = p.parse_args()
task = a.task.resolve()
out = task / 'output'
release = out / 'release'
release.mkdir(exist_ok=True)
boot = release / 'boot'
boot.mkdir(exist_ok=True)
for src, name in [(out/'fsbl/fsbl.elf', 'fsbl.elf'),
                  (out/'boot/u-boot.bin', 'u-boot.bin'),
                  (out/'boot/uImage.lz4', 'uImage.lz4'),
                  (out/'boot/system.dtb', 'system.dtb')]:
    if not src.is_file() or src.stat().st_size == 0:
        raise SystemExit('Missing build artifact: ' + str(src))
    shutil.copy2(src, release/name)
shutil.copy2(task/'system.hpf', release/'system.hpf')
import zipfile
with zipfile.ZipFile(task/'system.hpf') as z:
    (release/'system.bit').write_bytes(z.read('HPFs/system.bit'))
    for name in ['soc_plat.c', 'soc_plat.h', 'soc_plat_dts.h', 'Design.xml', 'hpf.info']:
        (release/name).write_bytes(z.read('HPFs/'+name))
bif = '''//arch=dr1m90; split=false; format=BIN
the_ROM_image:
{
 image {
  [bootloader,destination_cpu=apu-0,checksum=sha2] fsbl.elf
  [destination_device=pl,partition_owner=fsbl,encryption=none,checksum=sha2,load=0x200000] system.bit
  [destination_device=ps,destination_cpu=apu-0,org_endian,checksum=sha2,load=0x200000,exec=0x200000,partition_owner=fsbl] u-boot.bin
 }
}
'''
(release/'boot.bif').write_text(bif)
subprocess.run([str(task/'vendor/tools/bootgen/linux64/bin/albg'), '-w', '-log', 'info',
                '-image', 'boot.bif', '-arch', 'dr1m90', '-o', 'BOOT.bin'], cwd=release, check=True)
rootfs = out/'buildroot/images/rootfs.ext4'
assert rootfs.is_file()
shutil.copy2(rootfs, release/'rootfs.ext4')
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1 << 20), b''):
            h.update(data)
    return h.hexdigest()
seed = ''.join(sha(release/n) for n in ['BOOT.bin', 'system.dtb', 'uImage.lz4']) + sha(rootfs)
signature = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16) or 1
partuuid = '{:08x}-02'.format(signature)
cmd = '''# SD-only baseline. Never reuse a saved root device name.
if test "${devtype}" = "mmc" && test "${devnum}" = "0"; then
  if part uuid mmc 0:2 sdroot; then
    if test "${sdroot}" = "@UUID@"; then
      if load mmc 0:1 0x10000000 uImage.lz4 && load mmc 0:1 0x14000000 system.dtb; then
        setenv bootargs console=ttyS0,115200n8 earlycon=uart,mmio32,0xf8401000 loglevel=7 root=PARTUUID=@UUID@ rootwait rootfstype=ext4 rw
        bootm 0x10000000 - 0x14000000
      else
        echo BSP_ERROR_missing_SD_boot_files
      fi
    else
      echo BSP_ERROR_unexpected_SD_partition_UUID
    fi
  else
    echo BSP_ERROR_no_SD_root_partition
  fi
else
  echo BSP_ERROR_refusing_non_SD_boot_source
fi
'''.replace('@UUID@', partuuid)
(release/'boot.cmd').write_text(cmd)
subprocess.run(['mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none', '-n', 'BSP SD only',
                '-d', str(release/'boot.cmd'), str(release/'boot.scr')], check=True)
for name in ['BOOT.bin', 'boot.scr', 'system.dtb', 'uImage.lz4']:
    shutil.copy2(release/name, boot/name)
    os.utime(boot/name, (1791676800, 1791676800))
fat = release/'boot.vfat'
assert not fat.exists() or fat.is_file()
with fat.open('wb') as f:
    f.truncate(64*1024*1024)
subprocess.run(['mkfs.vfat', '-F', '32', '-i', '{:08x}'.format(signature), '-n', 'BSPBOOT', str(fat)], check=True)
subprocess.run(['mcopy', '-i', str(fat), '-m', *map(str, sorted(boot.iterdir())), '::/'], check=True)
# mcopy preserves modification time but otherwise uses current creation/access
# times. Normalize root directory timestamps in this simple four-file FAT image.
with fat.open('r+b') as f:
    bpb = f.read(512)
    bps = struct.unpack_from('<H', bpb, 11)[0]
    spc = bpb[13]
    reserved = struct.unpack_from('<H', bpb, 14)[0]
    fats = bpb[16]
    fatsecs = struct.unpack_from('<I', bpb, 36)[0]
    cluster = struct.unpack_from('<I', bpb, 44)[0]
    data_start = (reserved + fats*fatsecs)*bps
    dosdate = ((2026-1980)<<9) | (10<<5) | 11
    while cluster < 0x0ffffff8:
        off = data_start + (cluster-2)*spc*bps
        f.seek(off)
        entries = bytearray(f.read(spc*bps))
        for i in range(0,len(entries),32):
            if entries[i] in (0,0xe5) or entries[i+11] == 0x0f:
                continue
            entries[i+13] = 0
            struct.pack_into('<HHH',entries,i+14,0,dosdate,dosdate)
            struct.pack_into('<HH',entries,i+22,0,dosdate)
        f.seek(off)
        f.write(entries)
        f.seek(reserved*bps+cluster*4)
        cluster = struct.unpack('<I',f.read(4))[0] & 0x0fffffff
image = release/'sdcard.img'
assert not image.exists() or image.is_file()
boot_start, boot_sectors = 2048, 64*1024*1024//512
root_start, root_sectors = boot_start + boot_sectors, 256*1024*1024//512
assert rootfs.stat().st_size <= root_sectors*512
mbr = bytearray(512)
struct.pack_into('<I', mbr, 440, signature)
for i, (flag, kind, start, count) in enumerate([(0x80,0x0c,boot_start,boot_sectors),(0,0x83,root_start,root_sectors)]):
    struct.pack_into('<B3sB3sII', mbr, 446+16*i, flag, b'\xfe\xff\xff', kind, b'\xfe\xff\xff', start, count)
mbr[510:512] = b'\x55\xaa'
with image.open('wb') as dst:
    dst.truncate(512*1024*1024)
    dst.write(mbr)
    for path, sector in [(fat,boot_start),(rootfs,root_start)]:
        dst.seek(sector*512)
        with path.open('rb') as src:
            shutil.copyfileobj(src,dst)
# Final delivery artifacts only. Never recurse over release: historical callers
# may leave logs, intermediate FAT images or evidence files in that directory.
identity_names = ['sdcard.img', 'BOOT.bin', 'system.hpf', 'system.bit',
                  'fsbl.elf', 'u-boot.bin', 'system.dtb', 'uImage.lz4',
                  'rootfs.ext4', 'boot.cmd', 'boot.scr', 'boot.bif']
identity_files = [release / name for name in identity_names]
manifest = {
    'status':'BUILT_NOT_BOARD_BOOT_TESTED',
    'ddr':{'capacity_mib':1024,'dq_width':32,'rate_mts':1333,'io_voltage_v':1.35,'physical_voltage_measured':False},
    'root_partuuid':partuuid,
    'partitions':[{'number':1,'start_sector':boot_start,'sectors':boot_sectors,'filesystem':'FAT32'},
                  {'number':2,'start_sector':root_start,'sectors':root_sectors,'filesystem':'EXT4'}],
    'versions':{'linux':(out/'kernel/include/config/kernel.release').read_text().strip(),'uboot':'2021.01','buildroot':'2022.02.6','TD':'2026.1 SP2 6.2.2.200067','FD':'2026.1 SP1'},
    'files':{str(x.relative_to(release)):{'bytes':x.stat().st_size,'sha256':sha(x)}
             for x in identity_files}
}
(release/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(release/'SHA256SUMS').write_text(''.join(sha(x)+'  '+str(x.relative_to(release))+'\n'
                                      for x in identity_files))
print(json.dumps({'image':str(image),'partuuid':partuuid,'sha256':sha(image)},indent=2))
