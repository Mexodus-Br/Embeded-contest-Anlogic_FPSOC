#!/bin/sh
# Explicit, board-local approval for the only supplied firmware family.
set -eu
umask 077
[ "$(id -u)" = 0 ] || exit 1
recognized() {
 for dev in /sys/bus/usb/devices/*; do
  [ -f "$dev/idVendor" ] && [ -f "$dev/idProduct" ] || continue
  pair=$(cat "$dev/idVendor"):$(cat "$dev/idProduct")
  case "$pair" in a69c:8d80|a69c:8d81) return 0;; esac
 done
 return 1
}
case "${1:-status}" in
 status)
  lsusb
  echo 'Only a69c:8d80 boot / a69c:8d81 runtime + confirmed D80 label is supported by this candidate firmware'
  ;;
 approve-d80)
  case "${2:-}" in
   --physical-label-confirmed) ;;
   --usb-and-firmware-verified)
    [ -d /sys/module/aic8800_fdrv ] && [ -d /sys/class/net/wlan0/wireless ] || { echo 'Runtime driver/interface qualification missing'; exit 1; };;
   *) echo 'Confirm the physical label or the verified runtime USB/firmware/interface before approval'; exit 1;;
  esac
  recognized || { echo 'D80 USB ID absent; inspect Host, power, J18 and wiring'; exit 1; }
  mkdir -p /etc/wifi
  chmod 700 /etc/wifi
  printf 'D80\n' > /etc/wifi/driver-approved
  echo 'Board-local D80 approval stored; run wifi-driver load'
  ;;
 load)
  [ "$(cat /etc/wifi/driver-approved 2>/dev/null || :)" = D80 ] || { echo 'driver not approved for this physical board'; exit 1; }
  recognized || { echo 'Approved device absent; inspect Host/power first'; exit 1; }
  # Non-Android loader requests flat paths; the runtime driver appends D80.
  # Both names resolve to the exact same supplied U02 file, with no renaming.
  for name in fw_patch_table_8800d80_u02.bin fw_patch_8800d80_u02.bin fw_adid_8800d80_u02.bin fmacfw_8800d80_u02.bin fmacfw_8800d80_h_u02.bin fmacfw_8800d80_u02_ipc.bin calibmode_8800d80.bin lmacfw_rf_8800d80_u02.bin fw_ble_scan_ad_filter.bin aic_userconfig_8800d80.txt aic_powerlimit_8800d80.txt; do
   [ -f "/vendor/etc/firmware/aic8800D80/$name" ] || { echo 'D80 firmware set incomplete'; exit 1; }
   [ -e "/vendor/etc/firmware/$name" ] || ln -s "aic8800D80/$name" "/vendor/etc/firmware/$name"
  done
  modprobe cfg80211
  [ -d /sys/module/aic_load_fw ] || insmod /opt/wifi-candidates/aic_load_fw.ko
  # Firmware download can cause USB re-enumeration; runtime driver may bind later.
  [ -d /sys/module/aic8800_fdrv ] || insmod /opt/wifi-candidates/aic8800_fdrv.ko
  ;;
 revoke)
  wifi-sta autostart-off
  wifi-sta stop
  rm -f /etc/wifi/driver-approved
  # Do not force an in-use module unload.
  rmmod aic8800_fdrv 2>/dev/null || :
  rmmod aic_load_fw 2>/dev/null || :
  ;;
 *) echo 'usage: wifi-driver status|approve-d80 --physical-label-confirmed/--usb-and-firmware-verified|load|revoke'; exit 2;;
esac
