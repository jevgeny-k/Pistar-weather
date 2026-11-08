# RAM log limits

The recorded Pi-Star system uses a 64 MB tmpfs for `/var/log` and a 32 MB tmpfs for `/run`; both use RAM. Root on the SD card is normally read-only.

The installed `/etc/systemd/journald.conf.d/20-pistar-ram-limits.conf` contained:

```ini
[Journal]
Storage=volatile
RuntimeMaxUse=4M
RuntimeKeepFree=20M
RuntimeMaxFileSize=1M
RuntimeMaxFiles=4
MaxRetentionSec=1day
```

Journald was restarted to apply these settings. Archived journal files rotate automatically; recorded usage immediately after configuration was 3.4 MB. Inspect the target system's RAM and existing logging policy before applying these limits elsewhere.

`/run/pistar-weather/boot-health.json` is a single replaced report. Temporary bulletin WAV/RAW/AMBE files are removed after execution. The permanent phrase bank is not duplicated by calls. Configuration backups are not created on a recurring schedule.
