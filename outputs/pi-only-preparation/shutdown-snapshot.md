# Historical pre-shutdown snapshot

At about 00:03 Europe/Riga on November 8, 2026, a root-only backup was saved on the Pi at `/var/backups/pistar-weather/shutdown-20261107-220254` (UTC in directory name). `snapshot.json` recorded 24 configuration/program files, their SHA-256 values, BrandMeister groups, and autostart status. The API key remained on the Pi.

All 1,604 bank files were present. `mmdvmhost.timer`, `pistar-weather-relay.service`, and `pistar-weather-autonomous.timer` were enabled. The old frozen timer was disabled. The current timer was stopped before shutdown without disabling autostart.

Recorded configuration: fresh weather in TS1 every 15 minutes; TG <TG_A> and <TG_B> static in TS2; TG 91 removed; WhiteList=<OWNER_DMR_ID>. Data was synchronized and root remounted read-only before `shutdown -h now`. Later diagnostic notes supersede this snapshot where they record later changes.
