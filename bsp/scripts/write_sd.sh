#!/usr/bin/env bash
# Destructive deployment, only after human authorization of the inserted card.
# Arguments: by-id path, expected USB serial, expected disk size in 512B sectors.
set -euo pipefail
export LC_ALL=C
test "$#" = 3 || { echo 'Usage: write_sd.sh BY_ID EXPECTED_SERIAL EXPECTED_SECTORS'; exit 2; }
byid=$1
expected_serial=$2
expected_sectors=$3
TASK=${TASK:-$HOME/embedded-bsp}
image=$TASK/output/release/sdcard.img
expected_hash=289f90f22cf5bbaa387004a837b192d8b94ba366875f9bb8fe475a1043636049
dev=$(readlink -f -- "$byid")
test -b "$dev"
test "$(lsblk -dn -o TYPE "$dev")" = disk
name=${dev##*/}
test "$(cat /sys/class/block/"$name"/removable)" = 1
test "$(cat /sys/class/block/"$name"/size)" = "$expected_sectors"
props=$(udevadm info --query=property --name="$dev")
grep -qx 'ID_BUS=usb' <<< "$props"
grep -qx "ID_SERIAL_SHORT=$expected_serial" <<< "$props"
test -z "$(ls -A /sys/class/block/"$name"/holders)"
rootdev=$(findmnt -rn -o SOURCE /)
test "$dev" != "$rootdev"
test "$dev" != "/dev/$(lsblk -dn -o PKNAME "$rootdev")"
test "$(stat -c %s "$image")" = 536870912
test "$(sha256sum "$image" | cut -d' ' -f1)" = "$expected_hash"
echo "TARGET=$dev BY_ID=$byid SERIAL=$expected_serial SECTORS=$expected_sectors"
lsblk -o NAME,MODEL,SERIAL,SIZE,TYPE,TRAN,RM,FSTYPE,MOUNTPOINT "$dev"
while read -r part; do
  if findmnt -rn -S "$part" >/dev/null; then
    sudo -n umount -- "$part"
  fi
done < <(lsblk -nrpo NAME "$dev")
test -z "$(lsblk -nr -o MOUNTPOINT "$dev" | tr -d '[:space:]')"
# Re-check the by-id immediately before opening the write target.
test "$(readlink -f -- "$byid")" = "$dev"
echo 'WRITE_BEGIN'
sudo -n dd if="$image" of="$byid" bs=4M conv=fsync status=progress
sudo -n blockdev --flushbufs "$dev"
echo 'READBACK_BEGIN_536870912_BYTES'
readback=$(sudo -n dd if="$byid" bs=4M count=128 iflag=direct status=progress | sha256sum | cut -d' ' -f1)
echo "READBACK_SHA256=$readback"
test "$readback" = "$expected_hash"
echo 'READBACK_MATCH'
sudo -n blockdev --rereadpt "$dev"
sudo -n udevadm settle
while read -r part; do
  if findmnt -rn -S "$part" >/dev/null; then
    sudo -n umount -- "$part"
  fi
done < <(lsblk -nrpo NAME "$dev")
sudo -n sfdisk -d "$dev"
sudo -n blkid "${dev}1" "${dev}2"
sudo -n fsck.vfat -n "${dev}1"
sudo -n e2fsck -fn "${dev}2"
test "$(sudo -n blkid -s PARTUUID -o value "${dev}2")" = d0e414b9-02
sync
echo 'SD_DEPLOYMENT_VERIFIED_NOT_BOARD_BOOT_TESTED'
