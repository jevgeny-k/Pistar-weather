# Automatic startup checks

Added November 8, 2026 after a power-cycle test. `pistar-weather-bootcheck.timer` triggers 90 seconds after boot. Connection readiness may wait another 90 seconds; the service timeout is 180 seconds. The checker does not change configuration, reset the modem, or transmit RF.

Nine checks cover autostart, modem/relay/timer and master connection, all 1,604 phrase hashes, expected settings and Python syntax, SD/EXT4 errors in the current boot, power/throttling indicators, read-only root, the <WIFI_SSID> Wi-Fi profile, and BrandMeister static groups. Credentials are not included in its report.

The original first run returned `ok` for all nine checks, no detected SD/EXT4 errors, `throttled=0x0`, intact bank, read-only root, and TG <TG_A>/<TG_B> in TS2. These are historical results. The checker contains site-specific expectations; adapt them for another hotspot rather than changing that hotspot merely to satisfy the check.

```sh
cat /run/pistar-weather/boot-health.json
journalctl -u pistar-weather-bootcheck.service --no-pager
sudo systemctl start pistar-weather-bootcheck.service
```

The report is recreated under `/run` for the current boot. Script path: `/opt/pistar-weather/bootcheck.py`. Current sources and service/timer files are included in the new transfer bundle. They were added after the original bank ZIP.

An `ok` software report does not prove RF signal quality or audible reception on a radio.
