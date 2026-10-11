#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=1791676800
TASK=${TASK:-$HOME/embedded-bsp}
SDK=$TASK/sdk/master_sdk
BM=$TASK/vendor/tools/aarch64-bm/bin/aarch64-none-elf-
PLAT=$SDK/solutions/boards/project_sd_baseline
mkdir -p "$PLAT"
cp -a "$SDK/solutions/boards/board_dr1x90_ad101_v10/." "$PLAT/"
python3 - "$TASK/system.hpf" "$PLAT" <<'PY'
import pathlib, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    plat = pathlib.Path(sys.argv[2])
    for name, dest in [('soc_plat.h', 'inc'), ('soc_plat.c', 'src')]:
        (plat / dest / name).write_bytes(z.read('HPFs/' + name))
PY
grep -q 'DDRC_IO_VOL.*1.35' "$PLAT/inc/soc_plat.h"
grep -q '^#define DDR_INIT_V2' "$PLAT/inc/soc_plat.h"
# TD 2026 HPF omits the HAVE_* declarations needed by FD 2026 master_sdk.
# These enable header declarations only; generated *_ENABLE routing stays authoritative.
python3 - "$SDK" "$PLAT" <<'PY'
import pathlib, re, sys
sdk, plat = map(pathlib.Path, sys.argv[1:])
base = (sdk / 'solutions/boards/board_dr1x90_ad101_v10/inc/soc_plat.h').read_text()
declarations = re.findall(r'^#define HAVE_\w+.*$', base, re.M)
p = plat / 'inc/soc_plat.h'
p.write_text(p.read_text() + '\n/* FD HAL declaration compatibility */\n' + '\n'.join(declarations) + '\n')
PY
"${BM}gcc" --version
mkdir -p "$SDK/solutions/demo/fsbl/build"
# The vendor archiver adds, rather than replaces, archive members. Start this
# specific platform archive clean so source-path migrations cannot keep stale members.
if test -f "$TASK/output/fsbl/lib/libplat.a"; then
  rm -- "$TASK/output/fsbl/lib/libplat.a"
fi
make -C "$SDK/solutions/demo/fsbl" -j4 SDK_ROOT="$SDK" PLAT_DIR="$PLAT" \
  COMPILE_PREFIX="$BM" CHIP=dr1m90 ARMv8_STATE=64 ARMv8_EL=EL3 PINMUX_MODE= \
  APP_TAR_DIR="$TASK/output/fsbl"
cp "$SDK/solutions/demo/fsbl/build/fsbl.elf" "$TASK/output/fsbl/fsbl.elf"
"${BM}nm" "$TASK/output/fsbl/fsbl.elf" > "$TASK/output/fsbl/symbols.txt"
"${BM}objdump" -d "$TASK/output/fsbl/fsbl.elf" > "$TASK/output/fsbl/disassembly.txt"
cp "$SDK/solutions/demo/fsbl/build/fsbl.map" "$TASK/output/fsbl/"
