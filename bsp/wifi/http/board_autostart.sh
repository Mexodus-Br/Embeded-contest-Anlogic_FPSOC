#!/bin/sh
set -eu
wifi-sta status
wifi-http status
wifi-sta autostart-on
wifi-http autostart-on
sync
echo WIFI_AUTO_APPROVALS_SAVED_COLD_BOOT_NOT_YET_TESTED
