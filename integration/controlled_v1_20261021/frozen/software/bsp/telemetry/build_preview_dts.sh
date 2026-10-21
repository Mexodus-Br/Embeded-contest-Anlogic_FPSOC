#!/bin/bash
set -euo pipefail
TASK=${TASK:-$HOME/embedded-bsp-integrated}
BASE=${BASE:-$HOME/embedded-bsp}
cd "$TASK"
mkdir -p build/dts logs
exec > >(tee "logs/preview-dts-$(date -u +%Y%m%d-%H%M%S).log") 2>&1
cp "$BASE/vendor/sources/linux/arch/arm64/boot/dts/anlogic/"*.dts "$BASE/vendor/sources/linux/arch/arm64/boot/dts/anlogic/"*.dtsi "$BASE/vendor/sources/linux/arch/arm64/boot/dts/anlogic/"*.h build/dts/
cp bsp/configs/kernel.dts build/dts/preview.dts
cp bsp/gp/generated/gp-candidate.dtsi build/dts/gp-control.dtsi
cp bsp/motion/motion-control.dtsi build/dts/motion-control.dtsi
cp bsp/telemetry/board.dtsi build/dts/telemetry-board.dtsi
cp bsp/telemetry/preview-hpf.h build/dts/anlogic-dr1m90-hpf.h
sed -i 's/status = "disabled"/status = "okay"/' build/dts/gp-control.dtsi
printf '\n#include "gp-control.dtsi"\n#include "motion-control.dtsi"\n#include "telemetry-board.dtsi"\n' >> build/dts/preview.dts
"$BASE/vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-gcc" -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ -I build/dts -I "$BASE/vendor/sources/linux/include" -I "$BASE/vendor/sources/linux/arch/arm64/boot/dts" build/dts/preview.dts > build/preview.expanded.dts
"$BASE/output/kernel/scripts/dtc/dtc" -I dts -O dtb -o build/preview.dtb build/preview.expanded.dts
python3 bsp/telemetry/audit_dtb.py build/preview.dtb build/preview-resource-audit.json
