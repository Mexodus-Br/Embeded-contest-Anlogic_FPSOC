#!/bin/bash
set -euo pipefail
export LC_ALL=C
I=$(cd "$(dirname "$0")" && pwd)
TASK=$(dirname "$I")
WIFI=${WIFI:-$HOME/embedded-bsp-wifi-20261018}
BASE=${BASE:-$HOME/embedded-bsp}
K=$WIFI/vendor/sources/linux
O=$WIFI/output/kernel
S=$I/frozen/software
CROSS_COMPILE=$BASE/vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-
test "$(cat "$O/include/config/kernel.release")" = 6.1.111-rt42-bsp-wifi1
test -s "$O/Module.symvers"
mkdir -p "$TASK/build"
test ! -e "$TASK/build/build.ok"
exec > >(tee "$TASK/build/software-$(date -u +%Y%m%d-%H%M%S).log") 2>&1
cp "$O/.config" "$TASK/build/kernel.config"
cp "$O/Module.symvers" "$TASK/build/Module.symvers"
cp "$O/include/config/kernel.release" "$TASK/build/kernel.release"
# Build on the SAME wifi1 source, output, configuration and symbols.
for pair in "gp:$S/bsp/gp" "provider:$S/bsp/telemetry/provider" "rs485:$S/bsp/telemetry/client" "motion:$S/bsp/motion/client" "safety:$I/safety"; do
 name=${pair%%:*}; path=${pair#*:}
 extra=()
 if [[ $name == rs485 || $name == motion ]]; then extra=("KBUILD_EXTRA_SYMBOLS=$S/bsp/telemetry/provider/Module.symvers"); fi
 make -C "$K" O="$O" M="$path" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" "${extra[@]}" W=1 modules
done
"${CROSS_COMPILE}gcc" -D_DEFAULT_SOURCE -std=c11 -O2 -Wall -Wextra -Werror -pedantic "$I/safety/saf2_diag.c" -o "$TASK/build/saf2-diag"
"${CROSS_COMPILE}gcc" -D_DEFAULT_SOURCE -std=c11 -O2 -Wall -Wextra -Werror -pedantic "$S/bsp/telemetry/rs485_accept.c" "$S/pl_rs485/software/rs485_gp.c" "$S/pl_rs485/software/rs485_telem.c" -o "$TASK/build/rs485-accept"
python3 "$S/pl_interface/generate.py" --check
python3 "$S/bsp/wifi/http/test_http.py"
python3 "$S/bsp/wifi/test_host.py"
# Copy final software only. No directory hashes; no hashes for logs or symbol tables.
mkdir -p "$TASK/build/modules"
cp "$S/bsp/gp/bsp_gp.ko" "$S/bsp/telemetry/provider/anlogic-dma-engine.ko" "$S/bsp/telemetry/client/bsp_rs485.ko" "$S/bsp/motion/client/bsp_motion.ko" "$I/safety/bsp_saf2_diag.ko" "$TASK/build/modules/"
for module in "$TASK/build/modules/"*.ko; do
 echo "MODULE $(basename "$module")"; modinfo -F vermagic "$module"; modinfo -F depends "$module"
done
cmp "$O/.config" "$TASK/build/kernel.config"
cmp "$O/Module.symvers" "$TASK/build/Module.symvers"
echo SOFTWARE_BUILD_COMPLETE_NOT_DEPLOYED
touch "$TASK/build/build.ok"
