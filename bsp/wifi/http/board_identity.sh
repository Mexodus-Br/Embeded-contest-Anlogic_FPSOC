#!/bin/sh
set -eu
echo WIFI_IDENTITY_BEGIN
uname -a
cat /proc/cmdline
findmnt -n -o SOURCE,MAJ:MIN,FSTYPE /
test "$(uname -r)" = 6.1.111-rt42-bsp-wifi1
grep -q 'root=PARTUUID=70d791a8-02' /proc/cmdline
test "$(blkid -s PARTUUID -o value /dev/mmcblk0p2)" = 70d791a8-02
test "$(cat /sys/class/block/mmcblk0/device/type)" = SD
grep -E 'MemTotal|CmaTotal' /proc/meminfo
wifi-usb
for name in /opt/wifi-candidates/aic_load_fw.ko /opt/wifi-candidates/aic8800_fdrv.ko; do modinfo -F vermagic "$name"; done
ls -l /lib/firmware/regulatory.db /lib/firmware/regulatory.db.p7s
ls -l /vendor/etc/firmware/aic8800D80
cat /proc/modules
echo WIFI_IDENTITY_END
