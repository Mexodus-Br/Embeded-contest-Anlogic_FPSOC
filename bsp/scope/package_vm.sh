#!/bin/bash
set -euo pipefail
export TASK=${TASK:-$HOME/embedded-bsp-scope}
cd "$TASK"
mkdir -p logs output
GP_RESET_BOOT=1 PLATFORM_NAME=project_gpio_scope FSBL_VARIANT=fsbl_gpio_scope bash bsp/scripts/build_fsbl.sh > logs/fsbl-build.log 2>&1
# Use unchanged DTS generator/clock gates with this candidate's reviewed HPF.
sed 's@bsp/motion/integration.review.json@bsp/scope/integration.review.json@g' bsp/scripts/stage_motion_boot.sh > build/stage_boot.sh
DMA_STATUS=okay bash build/stage_boot.sh > logs/boot-stage.log 2>&1
sed -e 's@embedded-bsp-dma/output/rootfs-target@embedded-bsp-motion/output/rootfs-target@g' bsp/scripts/stage_motion_rootfs.sh > build/stage_rootfs.sh
# The existing script creates the image after installation; inject coordinate
# files immediately before fakeroot, and remove the four-axis test application.
python3 - <<'PY'
from pathlib import Path
p=Path('build/stage_rootfs.sh');s=p.read_text()
marker='"$BASE/output/buildroot/host/bin/fakeroot"'
installation='''
rm -f "$TARGET/usr/bin/motion-accept"
install -D -m755 "$TASK/build/delta-scope" "$TARGET/usr/bin/delta-scope"
install -D -m755 "$TASK/build/delta-model" "$TARGET/usr/bin/delta-model"
install -D -m755 "$TASK/build/firmware-oracle" "$TARGET/usr/bin/firmware-oracle"
install -D -m755 "$TASK/build/scope-unit" "$TARGET/usr/bin/scope-unit"
install -D -m644 "$TASK/golden_model/configs/firmware_reference.cfg" "$TARGET/etc/delta-scope/firmware_reference.cfg"
install -D -m644 "$TASK/bsp/scope/vectors/inputs.txt" "$TARGET/etc/delta-scope/model-inputs.txt"
sha256sum "$TARGET/usr/bin/delta-scope" "$TARGET/usr/bin/delta-model" "$TARGET/usr/bin/firmware-oracle" "$TARGET/usr/bin/scope-unit" "$TARGET/etc/delta-scope/firmware_reference.cfg" "$TARGET/lib/modules/6.1.111-rt42-bsp-sd1/extra/bsp_motion.ko" "$TARGET/lib/modules/6.1.111-rt42-bsp-sd1/kernel/drivers/dma/anlogic/anlogic-dma-engine.ko" > "$TARGET/etc/delta-scope/files.sha256"
sed -i "s@$TARGET@@g" "$TARGET/etc/delta-scope/files.sha256"
'''
s=s.replace(marker,installation+marker).replace('"$TARGET/usr/bin/motion-accept" "$TARGET/lib/modules','"$TARGET/usr/bin/delta-scope" "$TARGET/lib/modules')
p.write_text(s)
PY
DMA_RESTAGE=1 bash build/stage_rootfs.sh > logs/rootfs-stage.log 2>&1
# Keep mutable build logs outside the release identity manifest on repeat builds.
python3 - <<'PY'
from pathlib import Path
for name in ('arm-build.log','modules-build.log','fsbl-build.log','boot-stage.log','rootfs-stage.log','image.log','image-verify.log','unit-host.log','scope-image-verification.json'):
    p=Path('output/release')/name
    if p.exists(): p.unlink()
PY
python3 bsp/scripts/make_sd_image.py "$TASK" > logs/image.log 2>&1
sed "s@'usr/bin/motion-accept'@'usr/bin/delta-scope','usr/bin/delta-model','usr/bin/firmware-oracle','usr/bin/scope-unit','etc/delta-scope/firmware_reference.cfg','etc/delta-scope/model-inputs.txt','etc/delta-scope/files.sha256'@" bsp/scripts/verify_motion_image.py > build/verify_scope_image.py
python3 build/verify_scope_image.py "$TASK" > logs/image-verify.log 2>&1
echo SCOPE_PACKAGE_COMPLETE
tail -8 logs/image.log
