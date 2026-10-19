#!/bin/sh
set -eu
echo WIFI_DRIVER_BEGIN
test "$(uname -r)" = 6.1.111-rt42-bsp-wifi1
test "$(cat /sys/bus/usb/devices/1-1.1/idVendor)" = a69c
case "$(cat /sys/bus/usb/devices/1-1.1/idProduct)" in 8d80|8d81) ;; *) exit 1;; esac
modprobe cfg80211
test -d /sys/module/aic_load_fw || insmod /opt/wifi-candidates/aic_load_fw.ko
test -d /sys/module/aic8800_fdrv || insmod /opt/wifi-candidates/aic8800_fdrv.ko
sleep 5
wifi-usb
iw dev
iw reg get
ip -4 addr show
dmesg | tail -160
echo WIFI_DRIVER_END
