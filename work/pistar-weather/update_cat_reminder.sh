#!/bin/sh
set -eu
stage=/tmp/cat-reminder-staging
target=/opt/pistar-weather/reminders-v1
test -d "$target"
sudo -u pi-star env PYTHONDONTWRITEBYTECODE=1 /opt/pistar-weather/venv/bin/python "$stage/reminder.py" --check --assets "$stage"
previous_options=$(findmnt -no OPTIONS /)
restore_mount() {
    sync
    case ",$previous_options," in *,ro,*) mount -o remount,ro / ;; esac
}
trap restore_mount EXIT
# Updates and playback use the same existing lock without truncating it.
exec 9<>/run/pistar-weather/autonomous.lock
flock -x 9
mount -o remount,rw /
backup=/var/backups/pistar-weather/cat-reminder-before-$(date -u +%Y%m%d-%H%M%S)
install -d -m 700 "$backup"
cp -a "$target" "$backup/"
for name in reminder.py reminder.wav manifest.json; do
    install -m 644 "$stage/$name" "$target/.$name.next"
    mv "$target/.$name.next" "$target/$name"
done
flock -u 9
exec 9>&-
sudo -u pi-star env PYTHONDONTWRITEBYTECODE=1 /opt/pistar-weather/venv/bin/python "$target/reminder.py" --check
systemctl is-enabled pistar-cat-reminder.timer
systemctl is-active pistar-cat-reminder.timer
printf 'REMINDER_UPDATED backup=%s\n' "$backup"
