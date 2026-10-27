"""Guarded Windows raw SD deployment. Requires elevation and explicit card approval."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
from pathlib import Path
import subprocess
import time
import traceback

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--disk', type=int, required=True)
p.add_argument('--unique-id', required=True)
p.add_argument('--bytes', type=int, required=True)
p.add_argument('--image', type=Path, required=True)
p.add_argument('--sha256', required=True)
p.add_argument('--root-partuuid', required=True)
p.add_argument('--log', type=Path, required=True)
p.add_argument('--backup',type=Path,required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
task = root/'integration/home_calibration_20261027'
assert a.image.resolve().is_relative_to((task/'artifacts/release-r2').resolve())
assert a.log.resolve().is_relative_to((task/'artifacts').resolve())
assert a.backup.resolve().is_relative_to((task/'artifacts/private-rollback').resolve())
assert not a.backup.exists(), 'Never overwrite a prior rollback backup'
assert a.sha256=='335a509643f57fe6753c5f596fc7e7f0d84cff7b9c8febc584fcc6779e85f69d'
assert a.root_partuuid=='a61e22d5-02'
assert a.disk > 0 and a.bytes >= 536870912 and a.bytes % 512 == 0
assert a.image.stat().st_size == 536870912
assert len(a.sha256) == 64 and a.root_partuuid.endswith('-02')

k = c.WinDLL('kernel32', use_last_error=True)
shell = c.WinDLL('shell32', use_last_error=True)
k.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
k.CreateFileW.restype = w.HANDLE
k.DeviceIoControl.argtypes = [w.HANDLE, w.DWORD, c.c_void_p, w.DWORD, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]
k.DeviceIoControl.restype = w.BOOL
k.ReadFile.argtypes = [w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]
k.ReadFile.restype = w.BOOL
k.WriteFile.argtypes = k.ReadFile.argtypes
k.WriteFile.restype = w.BOOL
k.FlushFileBuffers.argtypes = [w.HANDLE]
k.FlushFileBuffers.restype = w.BOOL
k.CloseHandle.argtypes = [w.HANDLE]
k.VirtualAlloc.argtypes = [c.c_void_p, c.c_size_t, w.DWORD, w.DWORD]
k.VirtualAlloc.restype = c.c_void_p
k.VirtualFree.argtypes = [c.c_void_p, c.c_size_t, w.DWORD]
INVALID = c.c_void_p(-1).value

def check(ok):
    if not ok:
        raise c.WinError(c.get_last_error())

def open_device(path, access, flags=0):
    h = k.CreateFileW(path, access, 3, None, 3, flags, None)
    if h == INVALID:
        raise c.WinError(c.get_last_error())
    return h

def ioctl(h, code, output=None):
    count = w.DWORD()
    check(k.DeviceIoControl(h, code, None, 0,
                           c.byref(output) if output is not None else None,
                           c.sizeof(output) if output is not None else 0,
                           c.byref(count), None))

def identity():
    script = '''$ErrorActionPreference='Stop'; $d=Get-Disk -Number %d;
    $parts=@(Get-Partition -DiskNumber %d | Select-Object PartitionNumber,DriveLetter,Offset,Size);
    @{disk=($d | Select-Object Number,FriendlyName,UniqueId,BusType,Size,LogicalSectorSize,IsBoot,IsSystem,IsReadOnly);partitions=$parts} | ConvertTo-Json -Depth 5 -Compress''' % (a.disk, a.disk)
    data = json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',script], encoding='utf-8'))
    d = data['disk']
    assert d['FriendlyName']=='Generic- SD/MMC/MS PRO'
    assert d['Number'] == a.disk and d['UniqueId'] == a.unique_id
    assert d['Size'] == a.bytes and d['BusType'] == 'USB'
    assert d['LogicalSectorSize'] == 512
    assert not d['IsBoot'] and not d['IsSystem'] and not d['IsReadOnly']
    assert all(str(x.get('DriveLetter','')).upper() not in ('C','D') for x in data['partitions'])
    return data

handles = []
disk = None
buffer = None
record = {'status':'STARTED','expected_sha256':a.sha256,'root_partuuid':a.root_partuuid,
          'image':str(a.image.resolve()),'disk_number':a.disk,'emmc':'NOT_MODIFIED',
          'board_tests':'NOT_TESTED','started_local':time.strftime('%Y-%m-%dT%H:%M:%S%z')}
exit_code = 1
with a.log.open('x', encoding='utf-8') as log:
    def emit(message):
        print(message, flush=True)
        log.write(message+'\n'); log.flush()
    try:
        assert shell.IsUserAnAdmin(), 'Administrator elevation required'
        record['identity'] = identity()
        digest = hashlib.sha256()
        with a.image.open('rb') as source:
            for block in iter(lambda: source.read(4 << 20), b''):
                digest.update(block)
        assert digest.hexdigest() == a.sha256, 'Source SHA256 mismatch'
        emit('SOURCE_AND_TARGET_IDENTITY_VERIFIED')
        for part in record['identity']['partitions']:
            letter = str(part.get('DriveLetter') or '').strip('\x00')
            if letter:
                assert len(letter) == 1 and letter.isalpha()
                h = open_device('\\\\.\\'+letter+':', 0xC0000000)
                handles.append(h)
                ioctl(h, 0x00090018)  # FSCTL_LOCK_VOLUME
                ioctl(h, 0x00090020)  # FSCTL_DISMOUNT_VOLUME
                emit('LOCKED_AND_DISMOUNTED_VOLUME='+letter)
        assert identity()['disk'] == record['identity']['disk']
        path = '\\\\.\\PhysicalDrive'+str(a.disk)
        disk = open_device(path, 0xC0000000, 0xA0000000)  # write-through, unbuffered
        length = c.c_longlong()
        ioctl(disk, 0x0007405C, length)  # IOCTL_DISK_GET_LENGTH_INFO
        assert length.value == a.bytes
        buffer = k.VirtualAlloc(None, 4 << 20, 0x3000, 4)
        check(buffer)
        # Before any physical write, preserve every live partition and the MBR.
        # This card has two partitions entirely within the first 512MiB.
        # Backup may contain credentials: private ACL is established by launcher.
        assert all(int(p['Offset'])+int(p['Size'])<=536870912 for p in record['identity']['partitions'])
        emit('PRIVATE_ROLLBACK_BACKUP_BEGIN_536870912_BYTES')
        with a.backup.open('xb') as destination:
            for index in range(128):
                count=w.DWORD();check(k.ReadFile(disk,buffer,4<<20,c.byref(count),None))
                assert count.value==4<<20,'Short backup physical read'
                block=c.string_at(buffer,count.value)
                if index==0:
                    assert block[510:512]==b'\x55\xaa'
                    old_uuid='%08x-02'%int.from_bytes(block[440:444],'little')
                    assert old_uuid=='70d791a8-02','Old card identity changed'
                    record['previous_root_partuuid']=old_uuid
                    for pindex in range(4):
                        entry=block[446+16*pindex:462+16*pindex]
                        if entry[4]:
                            end=(int.from_bytes(entry[8:12],'little')+int.from_bytes(entry[12:16],'little'))*512
                            assert end<=536870912,'Live partition extends beyond rollback backup'
                destination.write(block)
            destination.flush()
            import os
            os.fsync(destination.fileno())
        k.CloseHandle(disk);disk=None
        disk=open_device(path,0x80000000,0x20000000)
        with a.backup.open('rb') as saved:
            for index in range(128):
                count=w.DWORD();check(k.ReadFile(disk,buffer,4<<20,c.byref(count),None))
                assert count.value==4<<20
                assert c.string_at(buffer,count.value)==saved.read(4<<20),'Backup direct readback mismatch'
            assert not saved.read(1)
        assert a.backup.stat().st_size==536870912
        record['private_rollback_backup']=str(a.backup.resolve())
        record['rollback_backup_verified']='BYTE_IDENTICAL_DIRECT_READ; covers MBR and all live partitions'
        emit('ROLLBACK_BACKUP_VERIFIED_BEFORE_WRITE')
        k.CloseHandle(disk);disk=None
        assert identity()['disk']==record['identity']['disk']
        disk=open_device(path,0xC0000000,0xA0000000)
        emit('WRITE_BEGIN_UNBUFFERED_536870912_BYTES')
        start = time.monotonic()
        with a.image.open('rb') as source:
            for index in range(512):
                block = source.read(1 << 20)
                assert len(block) == 1 << 20
                c.memmove(buffer, block, len(block))
                count = w.DWORD()
                check(k.WriteFile(disk, buffer, len(block), c.byref(count), None))
                assert count.value == len(block), 'Short physical write'
                record['written_bytes'] = (index+1) << 20
                if (index+1) % 32 == 0:
                    emit('WRITTEN_BYTES='+str(record['written_bytes']))
        check(k.FlushFileBuffers(disk))
        record['write_seconds'] = time.monotonic()-start
        k.CloseHandle(disk); disk = None
        disk = open_device(path, 0x80000000, 0x20000000)
        ioctl(disk, 0x0007405C, length)
        assert length.value == a.bytes
        emit('READBACK_BEGIN_UNBUFFERED_536870912_BYTES')
        start = time.monotonic()
        digest = hashlib.sha256()
        mbr = None
        fat_sector = None
        ext_super = None
        for index in range(128):
            count = w.DWORD()
            check(k.ReadFile(disk, buffer, 4 << 20, c.byref(count), None))
            assert count.value == 4 << 20, 'Short physical read'
            block = c.string_at(buffer, count.value)
            digest.update(block)
            if index == 0:
                mbr = block[:512]
                fat_sector = block[1048576:1049088]
            offset = 68157440+1024
            if index*(4 << 20) <= offset < (index+1)*(4 << 20):
                rel = offset-index*(4 << 20)
                ext_super = block[rel:rel+1024]
            record['readback_bytes'] = (index+1)*(4 << 20)
            if (index+1) % 8 == 0:
                emit('READBACK_BYTES='+str(record['readback_bytes']))
        record['readback_seconds'] = time.monotonic()-start
        record['actual_readback_sha256'] = digest.hexdigest()
        emit('READBACK_SHA256='+digest.hexdigest())
        assert digest.hexdigest() == a.sha256, 'Full direct readback SHA256 mismatch'
        assert mbr[510:] == b'\x55\xaa'
        assert '%08x-02' % int.from_bytes(mbr[440:444], 'little') == a.root_partuuid
        assert int.from_bytes(mbr[454:458], 'little') == 2048
        assert int.from_bytes(mbr[458:462], 'little') == 131072
        assert int.from_bytes(mbr[470:474], 'little') == 133120
        assert int.from_bytes(mbr[474:478], 'little') == 524288
        assert fat_sector[510:] == b'\x55\xaa'
        assert ext_super[56:58] == b'\x53\xef'
        record['partition_and_filesystem_signatures'] = 'PASS'
        record['fsck'] = 'NOT_RUN_ON_WINDOWS; source FAT/EXT4 fsck passed before byte-identical deployment'
        record['status'] = 'SD_DEPLOYMENT_VERIFIED_NOT_BOARD_BOOT_TESTED'
        emit(record['status'])
        exit_code = 0
    except BaseException as error:
        record['status'] = 'FAILED_NOT_VERIFIED'
        record['error'] = str(error)
        emit(traceback.format_exc())
    finally:
        if disk is not None:
            k.CloseHandle(disk)
        if buffer:
            k.VirtualFree(buffer, 0, 0x8000)
        for h in reversed(handles):
            k.CloseHandle(h)
        record['finished_local'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        record['exit_code'] = exit_code
        a.log.with_suffix(a.log.suffix+'.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
raise SystemExit(exit_code)
