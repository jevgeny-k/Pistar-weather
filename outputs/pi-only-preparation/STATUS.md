# Recorded autonomous hotspot status

This is a historical record from November 7-8, 2026, not a live status report. Recheck the device before changing it.

The complete bank contains 1,604 phrases, totaling 67.4 minutes; the original installation ZIP is about 58.5 MB. It was installed under `/opt/pistar-weather/autonomous-v1`. Xenia voice: +8% rate, +15% pitch. The Pi downloads five Open-Meteo/NOAA sources and assembles speech without Torch or a laptop.

`pistar-weather-autonomous.timer` was enabled for fresh bulletins every quarter hour. `pistar-weather-frozen.timer` was stopped and disabled; frozen parts remain as a backup under `/opt/pistar-weather/frozen-replay-v1`. Missed runs are not caught up. Concurrent executions are locked out and ordinary radio traffic has priority.

After reboot, the phrase bank, WhiteList=<OWNER_DMR_ID>, modem/relay startup, and timer persisted. A startup race was corrected by `readiness.py`, waiting up to 90 seconds for a connected master before playback. A connection error must not cause stale audio transmission. Current `play.py` and `readiness.py` are in `work/pistar-autonomous/` at repository root; the installation ZIP predates the fix. Previous Pi playback source: `/var/backups/pistar-weather/play-before-startup-wait.py`.

`pistar-weather-bootcheck.timer` runs 90 seconds after boot. The first report had nine successful checks; see `STARTUP-CHECK.md`. Original installation hashes and all phrase hashes were checked. Runtime tests included stale/future data, out-of-range values, and observation/forecast separation.

A recorded full call delivered four parts of 20.12, 11.59, 9.71, and 22.10 seconds through MMDVMHost. Each relay response had `ok: true`, ending with `AUTONOMOUS_BULLETIN_SENT`. Software success does not confirm audible reception. Later intermittent audio loss and a TXHang trial are documented in `radio-silence-20261108.md` and `txhang-trial.md`; no proven fix is claimed.

Stop the schedule with `sudo systemctl stop pistar-weather-autonomous.timer`. Inspect current state using the root handoff before deployment.
