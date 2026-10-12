#!/usr/bin/env bash
# Isolated DT compilation; retain the matched kernel and original release intact.
set -euo pipefail
export LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=1791676800
TASK=${TASK:-$HOME/embedded-bsp-gp}
BASE=${BASE:-$HOME/embedded-bsp}
BSP=${BSP_DIR:-$TASK/bsp}
OUT=$TASK/output
KERNEL=$BASE/vendor/sources/linux
mkdir -p "$OUT/boot" "$OUT/debug" "$OUT/dts" "$OUT/buildroot/images"
test "$(sha256sum "$BASE/output/kernel/.config" | cut -d' ' -f1)" = 81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1
test "$(sha256sum "$BASE/output/kernel/Module.symvers" | cut -d' ' -f1)" = ccc69b7dbd1968066b6ce46d5e5a741f55045f7cc9663db722c3959c1cb548a3
cp "$KERNEL/arch/arm64/boot/dts/anlogic/"*.dts "$KERNEL/arch/arm64/boot/dts/anlogic/"*.dtsi "$OUT/dts/"
cp "$KERNEL/arch/arm64/boot/dts/anlogic/"*.h "$OUT/dts/"
python3 "$BSP/scripts/dts_from_hpf.py" "$TASK/system.hpf" "$OUT/dts/anlogic-dr1m90-hpf.h"
cp "$BSP/configs/kernel.dts" "$OUT/dts/gp-board.dts"
cp "$BSP/gp/generated/gp-candidate.dtsi" "$OUT/dts/gp-control.dtsi"
if test "${GP_STATUS:-disabled}" = okay; then
  test -f "$BSP/gp/integration.review.json"
  python3 - "$BSP/gp/integration.review.json" "$TASK/system.hpf" <<'PY'
import hashlib,json,sys
e=json.load(open(sys.argv[1]))
assert e['status']=='READY_FOR_BSP_INTEGRATION'
assert e['bsp_review']=='REVIEWED_FOR_PROBE_BUILD'
assert e['hpf']['sha256']==hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest()
PY
  sed -i 's/status = "disabled"/status = "okay"/' "$OUT/dts/gp-control.dtsi"
fi
printf '\n#include "gp-control.dtsi"\n' >> "$OUT/dts/gp-board.dts"
"$BASE/vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-gcc" -E -P -x assembler-with-cpp \
  -nostdinc -undef -D__DTS__ -I "$OUT/dts" -I "$KERNEL/include" \
  -I "$KERNEL/arch/arm64/boot/dts" "$OUT/dts/gp-board.dts" > "$OUT/debug/gp-board.expanded.dts"
"$BASE/output/kernel/scripts/dtc/dtc" -I dts -O dtb -o "$OUT/boot/system.dtb" "$OUT/debug/gp-board.expanded.dts"
# Boot-critical HPF clock values must remain identical before reusing U-Boot.
python3 - "$BASE/output/hpf-dts.h" "$OUT/dts/anlogic-dr1m90-hpf.h" <<'PY'
import re,sys
keys=['AL_PROCESSOR_CORE0_CLOCK','AL_PROCESSOR_CORE1_CLOCK','AL_UART_CLOCK','AL_MMC0_PS_MAX_FREQ','AL_MMC1_PS_MAX_FREQ','AL_DDRC_CAPACITY']
def values(path):
    t=open(path).read()
    return {k:re.findall(r'^#define\s+'+k+r'\s+([^\n]+)',t,re.M)[-1].strip() for k in keys}
assert values(sys.argv[1])==values(sys.argv[2]), 'U-Boot boot-critical clocks changed; rebuild required'
PY
cp "$BASE/output/boot/u-boot.bin" "$BASE/output/boot/uImage.lz4" "$OUT/boot/"
cp "$BASE/output/gp-rootfs/rootfs.ext4" "$OUT/buildroot/images/"
test -e "$OUT/kernel" || ln -s "$BASE/output/kernel" "$OUT/kernel"
cp "$BASE/output/debug/kernel.config" "$BASE/output/debug/uboot.config" \
   "$BASE/output/kernel/Module.symvers" "$BASE/output/kernel/System.map" "$BASE/output/kernel/vmlinux" "$OUT/debug/"
cp "$BASE/output/buildroot/.config" "$OUT/debug/buildroot.config"
sha256sum "$OUT/boot/"* "$OUT/buildroot/images/rootfs.ext4"
fdtget "$OUT/boot/system.dtb" /soc/gp-control@80400000 status
