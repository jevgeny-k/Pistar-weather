# Autonomous evening cat feeding reminder

The reminder says: `Не забудь покормить котиков, котики голодают.` It uses the installed weather voice, Silero Baya, with the same live playback profile. It does not use the rejected F5 auditions or the proposed, untested Qwen voice.

## Schedule and coexistence

`pistar-cat-reminder.timer` triggers daily at **21:00, 21:30 and 22:00 Europe/Riga**. The timezone is explicit because the hotspot system timezone differs. Systemd handles Riga seasonal clock changes. `Persistent=false` prevents missed reminders from being replayed when the device returns after a shutdown. The enabled timer survives reboot.

The oneshot service runs as the weather service user, uses the existing private relay/site configuration and shares the weather/maintenance lock. It is ordered after the weather and protected maintenance services. At simultaneous quarter-hour triggers, weather retains priority; the reminder follows when weather finishes. Actual audio can therefore start later than the scheduled time. The reminder cannot interrupt a bulletin or overlap a modem restart.

## Preparation and installation

Run `render_reminder.py` once in the existing laptop Silero environment. It writes a natural-rate Baya WAV and checksum manifest to ignored `outputs/cat-reminder/`. The final recording is 3.1875 seconds; SHA-256 `095bf32732805c1a0113840482e549fd27844c3f96c98ed972da97f878e7ec2a`. Audio is not tracked in Git; retain the generated assets or regenerate them with this script.

Upload `reminder.py`, the WAV/manifest and both systemd units to a user-owned `/tmp/cat-reminder-staging/` on the intended hotspot. Run `reminder.py --check --assets /tmp/cat-reminder-staging` with the existing Pi Python as the service user. This validates the actual native codec twice without RF, including the selected weather tempo/pitch effects. Validate both unit files and all three calendar expressions with systemd tools.

The companion `install_cat_reminder.sh` is a first-install helper: it refuses existing target files, records their prior absence, briefly remounts root writable, installs assets in `/opt/pistar-weather/reminders-v1/`, verifies installed playback as the service user, enables the timer, and restores the previous root mount mode. Directories are 0755 and files 0644, root owned. Existing weather profile checksums are preserved. Root-only preparation is not accepted as an access test.

For a later text/audio change, upload the replacement runner/WAV/manifest to the same staging directory and run `update_cat_reminder.sh`. It checks the staged audio as the service user, backs up the existing reminder, and replaces files under the shared playback lock. Each file is installed through a temporary filename and renamed. The runner reads and validates its manifest/audio only after acquiring that lock. The timer and radio/weather settings are preserved. Only the updated reminder is backed up; there is no scheduled backup or log growth.

Runtime needs only the Pi's existing Python, SoX, native codec and relay. Each invocation verifies the stored WAV checksum, resamples into a short-lived RAM directory, creates a current playback manifest and calls the existing player. The live weather profile is applied once. The laptop, TTS model, network weather fetch and model/API tokens are not required for reminders. No additional persistent logs or indefinite cache are created.

## Verification and recovery

Installation on November 17, 2026 passed staged and installed-user codec repeatability checks. Systemd accepted the three calendar expressions and units. The timer is enabled and active; its first evening trigger corresponds to 19:00 UTC / 21:00 Riga on that date. An initial shorter phrase was transmitted successfully by the installed systemd service and the listener confirmed clear reception. The requested expanded text was then generated and checked separately. The unrelated existing Plymouth KillMode warning does not originate from these new units.

The expanded phrase passed staged and installed codec repeatability checks (183 AMBE frames). The existing bounded headroom retry selected -6 dB after a saturated -3 dB decoded peak; both passes matched. Its installed systemd service completed with Result=success / status 0 and the relay accepted 72 packets for local modem delivery. Audible reception of the expanded phrase has not been separately confirmed. Root was restored read-only, and all three timer calendar entries remained configured.

To inspect, use `systemctl list-timers pistar-cat-reminder.timer`, `systemctl status pistar-cat-reminder.timer` and the service's journal. `systemctl start pistar-cat-reminder.service` sends an unscheduled reminder. For an offline check, run the installed `reminder.py --check` as the service user.

To stop reminders, disable and stop only `pistar-cat-reminder.timer`. Before removing installed files, preserve any desired generated audio. The first-install backup records prior absence of the reminder directory/units; restoring that state requires removing only those new files and reloading systemd. Do not restore or overwrite unrelated radio/weather settings.

Software delivery to MMDVMHost does not prove audible reception. The hotspot's previously documented intermittent RF silence remains a separate unresolved limitation.
