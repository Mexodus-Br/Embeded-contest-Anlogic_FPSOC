"""Build a new SD FILE using matched wifi1 tools. Never opens a block device.

Run from a fresh extracted task directory on the build VM. Existing controlled
PL/HPF/FSBL/kernel stay immutable. Product limitations are recorded, not waived.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile

TASK = Path(__file__).resolve().parent
SRC = TASK/'src'
HOME_DIR = Path.home()
OLD = HOME_DIR/'embedded-controlled-v1-20261021'
WIFI = HOME_DIR/'embedded-bsp-wifi-20261018'
BASE = HOME_DIR/'embedded-bsp'
K = WIFI/'vendor/sources/linux'
O = WIFI/'output/kernel'
HOST = WIFI/'output/buildroot/host'
BOOT = OLD/'boot_candidate_v1/output/release'
TARGET = TASK/'rootfs-target'
RELEASE = TASK/'output/release'
BUILD = TASK/'build'

def run(*args, **kwargs):
    try:
        return subprocess.check_output(list(map(str, args)), stderr=subprocess.STDOUT, **kwargs).decode()
    except subprocess.CalledProcessError as error:
        print(error.output.decode(errors='replace'), flush=True)
        raise

assert not TARGET.exists() and not RELEASE.exists(), 'Never overwrite a prior attempt'
BUILD.mkdir(exist_ok=True)
RELEASE.mkdir(parents=True)
release = (O/'include/config/kernel.release').read_text().strip()
assert release == '6.1.111-rt42-bsp-wifi1'
assert (O/'.config').read_bytes() == (OLD/'build/kernel.config').read_bytes()
assert (O/'Module.symvers').read_bytes() == (OLD/'build/Module.symvers').read_bytes()
identity = json.loads((TASK/'source-identity.json').read_text())
identity.update(kernel=release, version='full-system-20261026-r1',
    hardware_origin_commit='4b2579e', backend_origin_commit='b9239a1',
    board_acceptance='NOT_EXECUTED', motion_qualified=False,
    xyz_source=None, rs485_service_publication=False,
    pulse_profile='H=L=500 cycles / 5us, DIR setup/hold=500 cycles, 100MHz',
    previous_stage1_profile='cf764ad MOTOR3125: H=L=3125 cycles / 31.25us',
    pl_rebuilt=False, limitations=['Real XYZ/FK/calibration unavailable; jog/teach/coordinate execution remain refused',
        'RS485 raw 32B/64B owner publication not implemented; driver_feedback remains null',
        'PROFILE2 fixture is not approved production HOME configuration',
        '5us pulse differs from cf764ad; stage3 requires confirmed pulse suitability and waveform acceptance; if parameters change, rebuild PL and affected verification',
        'HP1 interrupted RX remains quarantined without proven DDR drain',
        'HTTP device-owning process requires root/CAP_SYS_RAWIO; LAN is explicit opt-in'])

# One new execution module, built with the ORIGINAL matching kernel compiler.
cross = BASE/'vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-'
module = SRC/'bsp/safety_execution'
result = run('make', '-C', K, 'O='+str(O), 'M='+str(module), 'ARCH=arm64',
             'CROSS_COMPILE='+str(cross), 'W=1', 'modules')
(BUILD/'module-build.log').write_text(result)
print('MODULE_BUILD_OK', flush=True)
maintenance = BUILD/'saf2-maint.c'
diagnostic_source = (SRC/'integration/controlled_v1_20261021/safety/saf2_diag.c').read_text()
assert diagnostic_source.count('/dev/bsp-saf2-diag') == 1
maintenance.write_text(diagnostic_source.replace('/dev/bsp-saf2-diag', '/dev/bsp-saf2-exec')
    .replace('BOARD_SAF2_DIAGNOSTIC', 'BOARD_SAF2_EXEC_MAINT'))
run(str(cross)+'gcc', '-D_DEFAULT_SOURCE', '-std=c11', '-O2', '-Wall', '-Wextra',
    '-Werror', '-pedantic', '-I'+str(SRC/'integration/controlled_v1_20261021/safety'),
    maintenance, '-o', BUILD/'saf2-maint')

# Userspace uses Buildroot's compiler/sysroot, not the unrelated Windows SDK.
env = os.environ.copy()
env.update(PS_CC=str(HOST/'bin/aarch64-linux-gnu-gcc'),
           PS_CXX=str(HOST/'bin/aarch64-linux-gnu-g++'))
result = run('python3', SRC/'ps_app/tools/build_ps.py', '--target', 'sdk', '--server', env=env)
(BUILD/'userspace-build.log').write_text(result)
print('USERSPACE_BUILD_OK', flush=True)

shutil.copytree(OLD/'rootfs-target-complete', TARGET, symlinks=True)
direct = {}
def install(source, destination, mode=0o644):
    path = TARGET/destination
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, path)
    path.chmod(mode)
    direct[destination] = str(source)

for name in ['ps_server', 'ps_control']:
    install(SRC/'ps_app/build/partner/sdk'/name, 'usr/bin/'+name, 0o750)
# The original diagnostic-only Buildroot omitted the C++ runtime. Install only
# the compiler's corresponding runtime SONAMEs, without replacing existing libc.
for name in ['libstdc++.so.6', 'libgcc_s.so.1']:
    if not any((TARGET/folder/name).exists() for folder in ['lib', 'usr/lib']):
        source = Path(run(env['PS_CXX'], '-print-file-name='+name).strip())
        assert source.is_absolute() and source.is_file(), 'Missing SDK runtime '+name
        install(source.resolve(), 'usr/lib/'+name)
install(TASK/'ps-local.py', 'usr/bin/ps-local', 0o700)
install(BUILD/'saf2-maint', 'usr/bin/saf2-maint', 0o700)
install(TASK/'S47ps-hmi', 'etc/init.d/S47ps-hmi', 0o700)
install(module/'bsp_saf2_exec.ko', 'lib/modules/'+release+'/extra/bsp_saf2_exec.ko')
for name in ['web', 'scenarios']:
    for source in (SRC/'ps_app'/name).rglob('*'):
        if source.is_file():
            install(source, 'opt/ps-app/'+str(source.relative_to(SRC/'ps_app')))
for name in ['usr/bin/saf2-diag', 'lib/modules/'+release+'/extra/bsp_saf2_diag.ko']:
    path = TARGET/name
    if path.exists():
        path.unlink()  # candidate copy only: never two safety compatible owners
for folder in ['etc/ps-hmi', 'var/lib/ps-hmi']:
    (TARGET/folder).mkdir(parents=True, exist_ok=True)
    (TARGET/folder).chmod(0o700)
(BUILD/'identity.json').write_text(json.dumps(identity, indent=2)+'\n')
install(BUILD/'identity.json', 'etc/full-system-identity.json')
assert not (TARGET/'etc/ps-hmi/token').exists()
for name in ['etc/wifi/wpa_supplicant.conf', 'etc/wifi-http/auth.json', 'etc/ps-hmi/bind-ipv4']:
    assert not (TARGET/name).exists(), 'No personal credentials/network exposure in distribution'
run('depmod', '-b', TARGET, release)

# Check EVERY module import against the same kernel and provider symbol tables.
symbols = {}
for path in [O/'Module.symvers', OLD/'candidate/frozen/software/bsp/telemetry/provider/Module.symvers',
             OLD/'build/aic8800/Module.symvers']:
    for line in path.read_text().splitlines():
        values = line.split()
        symbols[values[1]] = int(values[0], 16)
modules = list((TARGET/'lib/modules'/release).rglob('*.ko'))
modules += list((TARGET/'opt/wifi-candidates').glob('*.ko'))
module_audit = {}
for path in modules:
    magic = run('modinfo', '-F', 'vermagic', path).strip()
    assert magic.startswith(release+' '), (path, magic)
    imports = run('modprobe', '--dump-modversions', path).splitlines()
    for line in imports:
        crc, name = line.split()
        assert symbols.get(name) == int(crc, 16), (path, name, crc)
    module_audit[str(path.relative_to(TARGET))] = {'vermagic': magic, 'matched_imports': len(imports)}
(BUILD/'module-audit.json').write_text(json.dumps(module_audit, indent=2)+'\n')

# Resolve DT from the SAME exported HPF chain: change ONLY statuses and safety compatible.
dtb = RELEASE/'system.dtb'
shutil.copyfile(BOOT/'system.dtb', dtb)
nodes = ['/soc/gp-control@80400000', '/soc/dma@80500000', '/soc/motion-control@80600000',
         '/soc/rs485-control@80700000', '/soc/dma@80900000', '/soc/safety@80a00000']
for node in nodes:
    assert run('fdtget', '-t', 's', dtb, node, 'status').strip() == 'disabled'
    run('fdtput', '-t', 's', dtb, node, 'status', 'okay')
run('fdtput', '-t', 's', dtb, nodes[-1], 'compatible', 'bsp,saf2-execution-v1')
before = run(O/'scripts/dtc/dtc', '-I', 'dtb', '-O', 'dts', BOOT/'system.dtb')
after = run(O/'scripts/dtc/dtc', '-I', 'dtb', '-O', 'dts', dtb)
# Ignore DTC warning text, compare actual source after the root declaration.
before = before[before.index('/dts-v1/;'):]
after = after[after.index('/dts-v1/;'):]
# Structured roundtrip proves no other properties were changed.
check = BUILD/'dt-roundtrip.dtb'
shutil.copyfile(dtb, check)
for node in nodes:
    run('fdtput', '-t', 's', check, node, 'status', 'disabled')
run('fdtput', '-t', 's', check, nodes[-1], 'compatible', 'bsp,saf2-diagnostic-v1')
restored = run(O/'scripts/dtc/dtc', '-I', 'dtb', '-O', 'dts', check)
assert restored[restored.index('/dts-v1/;'):] == before
assert 'validated-hp1-reset-drain' not in after
assert run('fdtget', '-t', 'x', dtb, '/memory', 'reg').split() == ['0', '0', '0', '40000000']
(BUILD/'system-enabled.dts').write_text(after)

# ELF interpreter, every DT_NEEDED dependency and versioned runtime requirement.
readelf = str(HOST/'bin/aarch64-linux-gnu-readelf')
def library(name):
    found = [p for folder in ['lib', 'usr/lib'] for p in (TARGET/folder).glob(name)]
    assert found, 'Missing target runtime '+name
    path = found[0]
    # Resolve absolute symlinks against the image tree, never the build host.
    for _ in range(12):
        if not path.is_symlink():
            return path
        target = os.readlink(path)
        path = TARGET/target.lstrip('/') if target.startswith('/') else path.parent/target
    raise AssertionError('Library symlink loop')
abi = {}
def version_requirements(path):
    text = run(readelf, '-V', path)
    if 'Version needs section' not in text:
        return {}
    needs = text.split('Version needs section', 1)[1]
    result = {}
    current = None
    for line in needs.splitlines():
        match = re.search(r'File: (\S+)', line)
        if match:
            current = match[1]
            result.setdefault(current, set())
        match = re.search(r'Name: (\S+)', line)
        if match:
            assert current
            result[current].add(match[1])
    for name, versions in result.items():
        definitions = run(readelf, '-V', library(name)).split('Version needs section', 1)[0]
        offered = set(re.findall(r'Name: (\S+)', definitions))
        assert versions <= offered, (str(path), name, versions-offered)
    return {name: sorted(versions) for name, versions in result.items()}
for name in ['ps_server', 'ps_control']:
    binary = TARGET/'usr/bin'/name
    assert 'AArch64' in run(readelf, '-h', binary)
    program = run(readelf, '-l', binary)
    interp = re.search(r'Requesting program interpreter: ([^\]]+)', program)[1]
    assert library(Path(interp).name).is_file()
    needed = re.findall(r'Shared library: \[([^\]]+)\]', run(readelf, '-d', binary))
    requirements = {name: version_requirements(binary)}
    pending = list(needed)
    seen = set()
    while pending:
        lib = pending.pop()
        if lib in seen:
            continue
        seen.add(lib)
        path = library(lib)
        requirements[lib] = version_requirements(path)
        pending.extend(re.findall(r'Shared library: \[([^\]]+)\]', run(readelf, '-d', path)))
    abi[name] = {'interpreter': interp, 'dependency_closure': sorted(seen), 'required_versions': requirements}
(BUILD/'abi-audit.json').write_text(json.dumps(abi, indent=2)+'\n')
print('MODULE_CRC_DT_RUNTIME_ABI_OK', flush=True)

# Make a fresh ext4. No mount, sudo, loop devices, or card access.
rootfs = RELEASE/'rootfs.ext4'
script = BUILD/'fakeroot.sh'
script.write_text("#!/bin/sh\nset -eu\nchown -h -R 0:0 '%s'\n'%s/bin/makedevs' -d '%s/output/buildroot/build/buildroot-fs/full_devices_table.txt' '%s'\n'%s/sbin/mkfs.ext4' -F -d '%s' -r 1 -N 0 -m 5 -L ps-full-r1 -O ^64bit -U 7c5d0f73-2a1e-4dd1-a2b4-202610260001 '%s' 256M\n" % (TARGET, HOST, WIFI, TARGET, HOST, TARGET, rootfs))
run(HOST/'bin/fakeroot', '--', 'sh', script)
run('e2fsck', '-fn', rootfs)
with tempfile.TemporaryDirectory(dir=BUILD) as tmp:
    extracted = Path(tmp)/'file'
    for destination, source in direct.items():
        if extracted.exists():
            extracted.unlink()
        run('debugfs', '-R', 'dump /'+destination+' '+str(extracted), rootfs)
        assert extracted.read_bytes() == Path(source).read_bytes(), destination

# Reuse the immutable same-batch PL/HPF/FSBL/BOOT/kernel; no PL implementation run.
for name in ['BOOT.bin', 'system.hpf', 'system.bit', 'fsbl.elf', 'u-boot.bin', 'uImage.lz4']:
    shutil.copyfile(BOOT/name, RELEASE/name)
with zipfile.ZipFile(RELEASE/'system.hpf') as z:
    assert z.read('HPFs/system.bit') == (RELEASE/'system.bit').read_bytes()
assert (RELEASE/'uImage.lz4').read_bytes() == (WIFI/'output/boot/uImage.lz4').read_bytes()
# Hash only necessary final deployment artifacts. Never logs or intermediate trees.
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1 << 20), b''):
            h.update(data)
    return h.hexdigest()
signature = int(sha(rootfs)[:8], 16) or 1
uuid = '%08x-02' % signature
command = (BOOT/'boot.cmd').read_text()
old_uuid = json.loads((BOOT/'manifest.json').read_text())['root_partuuid']
assert old_uuid in command
(RELEASE/'boot.cmd').write_text(command.replace(old_uuid, uuid))
run('mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none', '-n', 'PS full SD only',
    '-d', RELEASE/'boot.cmd', RELEASE/'boot.scr')
fat = BUILD/'boot.vfat'
with fat.open('wb') as f:
    f.truncate(64*1024*1024)
run('mkfs.vfat', '-F', '32', '-i', '%08x' % signature, '-n', 'PSFULLBOOT', fat)
boot_names = ['BOOT.bin', 'boot.scr', 'system.dtb', 'uImage.lz4']
run('mcopy', '-i', fat, *[RELEASE/n for n in boot_names], '::/')
run('fsck.vfat', '-n', fat)
image = RELEASE/'sdcard.img'
mbr = bytearray(512)
struct.pack_into('<I', mbr, 440, signature)
parts = [(0x80, 0x0c, 2048, 131072), (0, 0x83, 133120, 524288)]
for i, (flag, kind, start, count) in enumerate(parts):
    struct.pack_into('<B3sB3sII', mbr, 446+16*i, flag, b'\xfe\xff\xff', kind, b'\xfe\xff\xff', start, count)
mbr[510:] = b'\x55\xaa'
with image.open('wb') as f:
    f.truncate(512*1024*1024)
    f.write(mbr)
    for source, part in zip([fat, rootfs], parts):
        f.seek(part[2]*512)
        with source.open('rb') as r:
            shutil.copyfileobj(r, f)
# Read actual image partitions and FAT files back, not just staging directories.
with image.open('rb') as f:
    assert f.read(512) == mbr
    for source, part in zip([fat, rootfs], parts):
        f.seek(part[2]*512)
        with source.open('rb') as r:
            for data in iter(lambda: r.read(1 << 20), b''):
                assert f.read(len(data)) == data
with tempfile.TemporaryDirectory(dir=BUILD) as tmp:
    for name in boot_names:
        p = Path(tmp)/name
        run('mcopy', '-i', str(image)+'@@1048576', '::/'+name, p)
        assert p.read_bytes() == (RELEASE/name).read_bytes()
identity.update(root_partuuid=uuid, status='OFFLINE_INTEGRATED_IMAGE_WITH_FUNCTIONAL_LIMITATIONS',
    module_crc_audit='PASS', runtime_abi_audit='PASS', dt_roundtrip_audit='PASS',
    ext4_installed_files_readback=len(direct), partition_and_fat_readback='PASS',
    files={name: {'bytes': (RELEASE/name).stat().st_size, 'sha256': sha(RELEASE/name)}
           for name in ['sdcard.img', 'BOOT.bin', 'system.hpf', 'system.bit', 'fsbl.elf',
                        'u-boot.bin', 'uImage.lz4', 'system.dtb', 'rootfs.ext4', 'boot.cmd', 'boot.scr']})
(RELEASE/'manifest.json').write_text(json.dumps(identity, indent=2)+'\n')
(RELEASE/'SHA256SUMS').write_text(''.join(v['sha256']+'  '+k+'\n' for k, v in identity['files'].items()))
print(json.dumps({'image': str(image), 'root_partuuid': uuid, 'sha256': identity['files']['sdcard.img']['sha256']}, indent=2))
