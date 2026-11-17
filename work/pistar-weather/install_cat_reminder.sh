#!/bin/sh
set -eu
stage=/tmp/cat-reminder-staging
target=/opt/pistar-weather/reminders-v1
test ! -e "$target"
test ! -e /etc/systemd/system/pistar-cat-reminder.service
test ! -e /etc/systemd/system/pistar-cat-reminder.timer
previous_options=$(findmnt -no OPTIONS /)
restore_mount() {
    sync
    case ",$previous_options," in *,ro,*) mount -o remount,ro / ;; esac
}
trap restore_mount EXIT
mount -o remount,rw /
backup=/var/backups/pistar-weather/cat-reminder-before-$(date -u +%Y%m%d-%H%M%S)
install -d -m 700 "$backup"
printf '%s\n' 'Reminder directory and both systemd units were absent before installation.' > "$backup/previous-state.txt"
systemctl is-enabled pistar-weather-autonomous.timer >> "$backup/previous-state.txt"
sha256sum /opt/pistar-weather/autonomous-v1/playback-profile.json > "$backup/weather-profile.sha256"
install -d -m 755 "$target"
install -m 644 "$stage/reminder.py" "$stage/reminder.wav" "$stage/manifest.json" "$target/"
install -m 644 "$stage/pistar-cat-reminder.service" "$stage/pistar-cat-reminder.timer" /etc/systemd/system/
sudo -u pi-star env PYTHONDONTWRITEBYTECODE=1 /opt/pistar-weather/venv/bin/python "$target/reminder.py" --check
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/pistar-cat-reminder.service /etc/systemd/system/pistar-cat-reminder.timer
systemctl enable --now pistar-cat-reminder.timer
sha256sum -c "$backup/weather-profile.sha256"
systemctl is-enabled pistar-cat-reminder.timer
systemctl is-active pistar-cat-reminder.timer
systemctl list-timers pistar-cat-reminder.timer --no-pager
printf 'REMINDER_INSTALLED backup=%s\n' "$backup"
