#!/bin/sh
# Restore the original direct BrandMeister link. Keep weather tools for inspection.
set -eu
mount -o remount,rw /
cp -p /var/backups/pistar-weather/mmdvmhost /etc/mmdvmhost
systemctl disable --now pistar-weather-relay.service || true
systemctl restart mmdvmhost
sync
mount -o remount,ro /
echo 'Restored direct BrandMeister connection.'
