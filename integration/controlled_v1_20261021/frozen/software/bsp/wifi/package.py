"""Reuse the SD-only file packer with explicit final-artifact hash allowlist."""
import json, runpy, sys
from pathlib import Path
task = Path(sys.argv[1])
# make_sd_image requires vendor bootgen at this path, but does not write devices.
target = task/'vendor/tools'
if not target.exists():
    target.symlink_to(Path.home()/'embedded-bsp/vendor/tools', target_is_directory=True)
runpy.run_path(str(task/'bsp/scripts/make_sd_image.py'), run_name='__main__')
manifest_path = task/'output/release/manifest.json'
manifest = json.loads(manifest_path.read_text())
manifest.update(profile='wifi-sta-scope-hardware-candidate',
                hardware_acceptance='NOT_EXECUTED_BOARD_AND_SD_UNAVAILABLE',
                automatic_sta_enabled=False,
                wifi_driver_selection='PENDING_PHYSICAL_LABEL_AND_USB_ID')
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
