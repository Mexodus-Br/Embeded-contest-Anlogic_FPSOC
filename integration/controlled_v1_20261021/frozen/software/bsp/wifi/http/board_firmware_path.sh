#!/bin/sh
set -eu
echo WIFI_PATH_REPAIR_BEGIN
for name in fw_patch_table_8800d80_u02.bin fw_patch_8800d80_u02.bin fw_adid_8800d80_u02.bin fmacfw_8800d80_u02.bin fmacfw_8800d80_h_u02.bin fmacfw_8800d80_u02_ipc.bin calibmode_8800d80.bin lmacfw_rf_8800d80_u02.bin fw_ble_scan_ad_filter.bin aic_userconfig_8800d80.txt aic_powerlimit_8800d80.txt; do
 test -f "/vendor/etc/firmware/aic8800D80/$name"
 test -e "/vendor/etc/firmware/$name" || ln -s "aic8800D80/$name" "/vendor/etc/firmware/$name"
done
rmmod aic8800_fdrv
rmmod aic_load_fw
insmod /opt/wifi-candidates/aic_load_fw.ko
sleep 3
insmod /opt/wifi-candidates/aic8800_fdrv.ko
sleep 5
wifi-usb
iw dev
ip -4 addr show
dmesg | tail -140
echo WIFI_PATH_REPAIR_END
