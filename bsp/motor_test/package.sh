#!/bin/bash
set -euo pipefail
export TASK=${TASK:-$HOME/embedded-bsp-motor3125}
cd "$TASK"
mkdir -p logs build output
# Frozen original provider/client; canonical headers from the accepted scope release.
bash bsp/scripts/build_motion_software.sh > logs/modules-build.log 2>&1
bash bsp/scope/build_arm.sh
test -f system.hpf
GP_RESET_BOOT=1 PLATFORM_NAME=project_motor3125 FSBL_VARIANT=fsbl_motor3125 bash bsp/scripts/build_fsbl.sh > logs/fsbl-build.log 2>&1
sed 's@bsp/motion/integration.review.json@bsp/scope/integration.review.json@g' bsp/scripts/stage_motion_boot.sh > build/stage_boot.sh
DMA_STATUS=okay bash build/stage_boot.sh > logs/boot-stage.log 2>&1
sed 's@embedded-bsp-dma/output/rootfs-target@embedded-bsp-motion/output/rootfs-target@g' bsp/scripts/stage_motion_rootfs.sh > build/stage_rootfs.sh
python3 - <<'PY'
from pathlib import Path
p=Path('build/stage_rootfs.sh');s=p.read_text();marker='"$BASE/output/buildroot/host/bin/fakeroot"'
install='''
rm -f "$TARGET/usr/bin/motion-accept"
install -D -m755 "$TASK/build/delta-scope" "$TARGET/usr/bin/delta-scope"
install -D -m755 "$TASK/build/delta-model" "$TARGET/usr/bin/delta-model"
install -D -m755 "$TASK/build/firmware-oracle" "$TARGET/usr/bin/firmware-oracle"
install -D -m755 "$TASK/build/scope-unit" "$TARGET/usr/bin/scope-unit"
install -D -m644 "$TASK/golden_model/configs/firmware_reference.cfg" "$TARGET/etc/delta-scope/firmware_reference.cfg"
install -D -m644 "$TASK/bsp/scope/vectors/inputs.txt" "$TARGET/etc/delta-scope/model-inputs.txt"
install -D -m644 "$TASK/bsp/motor_test/README.md" "$TARGET/root/MOTOR3125_README.md"
printf 'MOTOR3125 BENCH ONLY; H=3125 L=3125 guards=500 MAX_HZ=16000; no auto enable/start; mechanics uncalibrated\\n' > "$TARGET/etc/motor3125-profile"
sha256sum "$TARGET/usr/bin/delta-scope" "$TARGET/usr/bin/delta-model" "$TARGET/etc/delta-scope/firmware_reference.cfg" "$TARGET/lib/modules/6.1.111-rt42-bsp-sd1/extra/bsp_motion.ko" "$TARGET/lib/modules/6.1.111-rt42-bsp-sd1/kernel/drivers/dma/anlogic/anlogic-dma-engine.ko" > "$TARGET/etc/delta-scope/files.sha256"
sed -i "s@$TARGET@@g" "$TARGET/etc/delta-scope/files.sha256"
python3 - "$TARGET" <<'CHECK_INIT'
from pathlib import Path
import sys
r=Path(sys.argv[1]);seen=[]
for p in (r/'etc/init.d').glob('*'):
    if p.is_file():
        t=p.read_text(errors='replace')
        if any(x in t for x in ['delta-scope','bsp_motion','motion-accept']):seen.append(str(p))
assert not seen,('Unexpected automatic motion startup',seen)
CHECK_INIT
'''
assert s.count(marker)==1
s=s.replace(marker,install+marker).replace('"$TARGET/usr/bin/motion-accept" "$TARGET/lib/modules','"$TARGET/usr/bin/delta-scope" "$TARGET/lib/modules')
p.write_text(s)
PY
DMA_RESTAGE=1 bash build/stage_rootfs.sh > logs/rootfs-stage.log 2>&1
python3 bsp/scripts/make_sd_image.py "$TASK" > logs/image.log 2>&1
sed "s@'usr/bin/motion-accept'@'usr/bin/delta-scope','usr/bin/delta-model','usr/bin/firmware-oracle','usr/bin/scope-unit','etc/delta-scope/firmware_reference.cfg','etc/delta-scope/model-inputs.txt','etc/delta-scope/files.sha256','etc/motor3125-profile'@" bsp/scripts/verify_motion_image.py > build/verify_motor_image.py
python3 build/verify_motor_image.py "$TASK" > logs/image-verify.log 2>&1
echo MOTOR3125_PACKAGE_COMPLETE
