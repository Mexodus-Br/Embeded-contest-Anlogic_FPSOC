#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=1791676800
BASE=${BASE:-$HOME/embedded-bsp}
TASK=${TASK:-$HOME/embedded-bsp-dma}
OUT=$TASK/output
KERNEL=$BASE/vendor/sources/linux
mkdir -p "$OUT/dts" "$OUT/debug" "$OUT/boot"
test "$(sha256sum "$BASE/output/kernel/.config" | cut -d' ' -f1)" = 81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1
test "$(sha256sum "$BASE/output/kernel/Module.symvers" | cut -d' ' -f1)" = ccc69b7dbd1968066b6ce46d5e5a741f55045f7cc9663db722c3959c1cb548a3
cp "$KERNEL/arch/arm64/boot/dts/anlogic/"*.dts "$KERNEL/arch/arm64/boot/dts/anlogic/"*.dtsi "$KERNEL/arch/arm64/boot/dts/anlogic/"*.h "$OUT/dts/"
python3 "$TASK/bsp/scripts/dts_from_hpf.py" "$TASK/system.hpf" "$OUT/dts/anlogic-dr1m90-hpf.h"
cp "$TASK/bsp/configs/kernel.dts" "$OUT/dts/dma-board.dts"
cp "$TASK/bsp/gp/generated/gp-candidate.dtsi" "$OUT/dts/gp-control.dtsi"
cp "$TASK/bsp/dma/dma-control.dtsi" "$OUT/dts/dma-control.dtsi"
if test "${DMA_STATUS:-disabled}" = okay; then
 python3 - "$TASK/bsp/dma/integration.review.json" "$TASK/system.hpf" <<'PY'
import hashlib,json,sys
m=json.load(open(sys.argv[1]));assert m['status']=='REVIEWED_FOR_INDEPENDENT_LOOPBACK_BUILD'
assert m['hpf_sha256']==hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest()
assert m['kernel_config_sha256']=='81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1'
PY
 sed -i 's/status = "disabled"/status = "okay"/' "$OUT/dts/gp-control.dtsi" "$OUT/dts/dma-control.dtsi"
fi
printf '\n#include "gp-control.dtsi"\n#include "dma-control.dtsi"\n' >> "$OUT/dts/dma-board.dts"
"$BASE/vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-gcc" -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ -I "$OUT/dts" -I "$KERNEL/include" -I "$KERNEL/arch/arm64/boot/dts" "$OUT/dts/dma-board.dts" > "$OUT/debug/dma-board.expanded.dts"
"$BASE/output/kernel/scripts/dtc/dtc" -I dts -O dtb -o "$OUT/boot/system.dtb" "$OUT/debug/dma-board.expanded.dts"
python3 - "$BASE/output/hpf-dts.h" "$OUT/dts/anlogic-dr1m90-hpf.h" <<'PY'
import re,sys
keys=['AL_PROCESSOR_CORE0_CLOCK','AL_PROCESSOR_CORE1_CLOCK','AL_UART_CLOCK','AL_MMC0_PS_MAX_FREQ','AL_MMC1_PS_MAX_FREQ','AL_DDRC_CAPACITY']
def values(p):
 t=open(p).read();return {k:re.findall(r'^#define\s+'+k+r'\s+([^\n]+)',t,re.M)[-1].strip() for k in keys}
assert values(sys.argv[1])==values(sys.argv[2]),'Rebuild U-Boot: critical clocks changed'
PY
cp "$BASE/output/boot/u-boot.bin" "$BASE/output/boot/uImage.lz4" "$OUT/boot/"
test -e "$OUT/kernel" || ln -s "$BASE/output/kernel" "$OUT/kernel"
cp "$BASE/output/debug/kernel.config" "$BASE/output/debug/uboot.config" "$BASE/output/kernel/Module.symvers" "$BASE/output/kernel/System.map" "$BASE/output/kernel/vmlinux" "$OUT/debug/"
cp "$TASK/bsp/dma/provider/Module.symvers" "$OUT/debug/dma-provider.Module.symvers"
fdtget "$OUT/boot/system.dtb" /soc/dma@80500000 status
fdtget "$OUT/boot/system.dtb" /soc/gp-control@80400000 status
