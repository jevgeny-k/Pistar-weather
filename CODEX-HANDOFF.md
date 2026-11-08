# Codex handoff: deploy the Pi-Star voice weather service

## Objective and current limits

Install or update the autonomous weather service on the intended Pi-Star hotspot, preserve its working radio/network configuration, and verify fresh-data assembly, local private playback, scheduling, and startup checks. Write all new documentation and source comments in English. The spoken weather remains Russian.

This document prepares deployment; it does not claim that the current hotspot has been inspected or changed. The recorded configuration dates from November 7-8, 2026. Intermittent loss of audible reception remains unresolved. Read the diagnostic notes before claiming success.

## Files to receive

The preferred transfer is `dist/pistar-weather-transfer.zip` and its adjacent `.sha256` file. They are generated locally and are ignored by Git. The bundle includes current runtime/relay sources, the complete bank, the historical native encoder, systemd units, this handoff, English instructions, and a new `TRANSFER-MANIFEST.json`. It excludes secrets, virtual environments, Torch, old source snapshots, and original historical ZIPs.

If receiving the whole repository instead, keep ignored assets: in particular `outputs/pi-only-preparation/bank/` and `assets/encode`. A Git clone alone does not contain them. Build a new package from repository root:

```sh
python tools/build_transfer.py
```

The builder checks all 1,604 bank hashes, bundles the current code, and checks every archived file against the new transfer manifest. It refuses to overwrite an existing package; use a different output filename for another build. Original import manifests, personalized snapshots, and historical ZIPs have been removed from this public project. Only the new anonymous bundle is intended for transfer. Use its `TRANSFER-MANIFEST.json` for integrity checks.

## Private site configuration: required before transmission

This public project contains no operator ID, callsign, SSH address, Wi-Fi profile name, frequency plan, or static-group membership. The example configuration contains only public defaults for the Riga phrase-bank demonstration.

Obtain the target's intended settings through the authorized private deployment context. Do not infer an owner identity from this repository. Do not bypass an SSH host-key mismatch or log credentials.

Copy `config/site.example.json` to a private file and fill in `radio_id` and `upstream_host`. On the Pi, install it at `/etc/pistar-weather/site.json`, root-owned, group-readable by the service account (typically group `pi-star`), mode 0640. The directory must permit the service account to traverse it. Do not include API keys in this JSON; the optional BrandMeister key remains in its existing root-only `/etc/bmapi.key`.

- `radio_id`: integer owner ID; required for packet generation and relay startup. There is no live default. A missing ID blocks transmission.
- `upstream_host` / `upstream_port`: the target's actual master; the host has no default.
- `wifi_ssid`: optional expected Wi-Fi profile; blank means the boot checker reports this check as unconfigured.
- `expected_static_groups`: optional list of `[talkgroup, slot]` pairs. `null` means no expectation/API query; an empty list means explicitly expect no static groups.
- `expected_mmdvm`: optional section-to-key dictionaries for the intended frequency plan, whitelist, color code, and other local checks. These are verification expectations, not configuration changes.
- `latitude`, `longitude`, `timezone`: weather-query settings. Public defaults are rounded Riga city-center coordinates. The prerecorded speech bank remains a Riga demonstration; another city/language may require regenerating city phrases.

For local laptop execution, set `PISTAR_SITE_CONFIG` to the private file's absolute path. The ignored `config/site.json` is a convenient local filename, but is not auto-discovered. The default runtime path is `/etc/pistar-weather/site.json`. The transfer builder uses an explicit allowlist and includes only `site.example.json`.

The architecture still uses private calls on TS1, a relay at `127.0.0.1:62039`, and fresh bulletins every quarter hour without catch-up. Preserve the actual target's radio/network settings. An earlier TXHang trial is documented as an unresolved diagnostic experiment, not an installation requirement.

## Deployment map

Paths below are relative to the extracted new bundle:

| Bundle file(s) | Pi destination |
| --- | --- |
| `relay/proxy.py`, `relay/weather.py`, `relay/site_settings.py`, `relay/encode` | `/opt/pistar-weather/` |
| `relay/bootcheck.py` | `/opt/pistar-weather/bootcheck.py` |
| `autonomous/` contents | `/opt/pistar-weather/autonomous-v1/` |
| `relay/pistar-weather-relay.service` | `/etc/systemd/system/` |
| `systemd/*.service`, `systemd/*.timer` | `/etc/systemd/system/` |
| Private operator file (provided separately) | `/etc/pistar-weather/site.json` |
| Wrapper described below | `/usr/local/bin/pistar-weather-autonomous` |

`relay/encode.c` is retained for inspection/rebuilding. The included `encode` is a historical Linux ARM binary. It must match the Pi architecture and required libraries; verify with `uname -m`, `file`, and `ldd` where available. Do not execute an incompatible binary. Native encoder building requires the separately obtained `md380_vocoder` headers/library; those build inputs are not fully vendored here. Existing functional Pi encoder/environment should be preserved when compatible.

The obsolete one-off installer and personalized old archives have been removed. Follow this handoff with the current bundle.

## 1. Inspect and back up the actual target

Read the current hostname, architecture, Python version, free space, mount state, unit definitions, and service/timer status. Inspect only the relevant non-secret MMDVMHost fields. Useful read-only commands:

```sh
hostname
uname -m
python3 --version
df -h / /tmp /run
findmnt -no OPTIONS /
systemctl status mmdvmhost pistar-weather-relay.service --no-pager
systemctl list-timers --all --no-pager
systemctl cat pistar-weather-relay.service pistar-weather-autonomous.service
```

Before replacing anything, make a timestamped, root-owned mode-0700 backup under `/var/backups/pistar-weather/` of the existing `/etc/mmdvmhost`, modified systemd units, command wrapper, relay/runtime sources, and journald drop-in if changing it. Record previous enabled/active timer states and hashes. Preserve an existing bank rather than needlessly duplicate it. Keep private backups on the Pi. If root is read-only, remount writable only for the installation/backup window and restore its previous mount mode afterward.

Record the direct BrandMeister address/port before enabling the relay. Keep frequencies, owner ID, whitelist, modem, Wi-Fi, and credentials unchanged for this same-device update. Do not change BrandMeister subscriptions or firmware as a side effect.

## 2. Upload and verify before installation

Create a user-owned staging directory under `/home/pi-star/`, not a RAM filesystem: the expanded phrase bank needs significant space. Copy the ZIP and checksum over the established SSH connection, for example:

```sh
ssh pi-star@HOTSPOT 'mkdir -p /home/pi-star/weather-staging'
scp dist/pistar-weather-transfer.zip dist/pistar-weather-transfer.zip.sha256 pi-star@HOTSPOT:/home/pi-star/weather-staging/
```

Replace `HOTSPOT` with the verified address. On the Pi, run `sha256sum -c pistar-weather-transfer.zip.sha256` from that staging directory. Inspect the member names and reject absolute paths, `..`, or unexpected links before extracting into a new, empty subdirectory. Never extract an unreviewed archive as root over `/`.

Check `TRANSFER-MANIFEST.json`: for each relative file path, verify that it stays inside the extracted directory, exists, and has the specified size/SHA-256. Reject mismatches. Verify catalog/profile equality, exactly 1,604 phrase IDs, matching catalog/bank entry sets, and every audio/text hash. `bootcheck.verify_bank()` can check the extracted `autonomous/` directory; only call that function, not the full site-specific startup checker yet.

## 3. Check runtime prerequisites

The recorded Pi playback interpreter is `/opt/pistar-weather/venv/bin/python`. It must import `bitarray`, `dmr_utils3`, `site_settings`, and `zoneinfo`, including timezone data for `Europe/Riga`. The runtime also needs SoX and the native encoder at `/opt/pistar-weather/encode` with encode/decode support. Relay and boot-check units use system Python 3; ensure it can parse the supplied sources. Use Python 3.9 or newer with the required standard library support; Python 3.12 was used for laptop validation.

On an already configured Pi, inspect and retain these working dependencies. On a fresh device, provision a Linux-native virtual environment, install `bitarray` and `dmr_utils3`, provide OS timezone data and SoX, and verify a compatible encoder. Never copy the Windows virtual environment. The preserved `requirements-laptop-lock.txt` describes the laptop speech generator, not Pi runtime dependencies. Autonomous operation does not need Torch, the Silero model, or Piper. Piper is only needed if restoring the separate old fallback command.

Test imports and encode/decode with a bank sample, writing output only into staging. Check WAV format, decoded length and peak level. `play.py` shows the exact SoX/encoder commands and acceptance bounds. These offline checks must not invoke `now` or submit packets to the relay.

## 4. Install current code without mixing versions

After prerequisites and staging checks pass, stop the fresh and frozen weather timers and any active bulletin service before replacing files. Record their previous states. Avoid restarting MMDVMHost during ordinary radio traffic.

Install a consistent set of the five current autonomous runtime modules, the `site_settings.py` helper, catalog, bank manifest, and full bank into `/opt/pistar-weather/autonomous-v1/`. When updating an existing installation, retain a recoverable previous version and replace the runtime set together while the weather service is stopped. Do not overlay an older ZIP afterward. Install current relay/playback support files and `bootcheck.py` according to the deployment map. Code, bank, and service files should be readable by `pi-star` and not writable by untrusted accounts; the encoder and wrapper must be executable. Do not chown or replace the existing virtual environment recursively.

The command wrapper must contain:

```sh
#!/bin/sh
exec /opt/pistar-weather/venv/bin/python /opt/pistar-weather/autonomous-v1/autonomous.py "$@"
```

Install reviewed systemd units and the private site file first. The supplied relay unit reads its identity and master from that private file. Also install `site_settings.py` beside `bootcheck.py` under `/opt/pistar-weather/`. For a same-device update, keep an already-correct loopback DMR Network destination. For a fresh relay setup, change only DMR Network `RemoteAddress` and `RemotePort` to the local relay address/port after backing up the direct upstream. Do not copy the historical configuration summary over `/etc/mmdvmhost`.

Run `systemd-analyze verify` on installed unit files where supported, then `systemctl daemon-reload`. The relay unit creates `/run/pistar-weather` owned by `pi-star`, mode 0700, and preserves it across service stops. Playback needs that directory and the same service account to access the control socket. Start/enable the relay, then restart MMDVMHost only if code/network changes require it and the channel is idle. Wait until the relay reports a connected master and a known local host.

## 5. Validate fresh data without RF first

Run as the service owner:

```sh
sudo -u pi-star /usr/local/bin/pistar-weather-autonomous prepare
```

Confirm fresh Open-Meteo data, correct Riga local time, valid phrase selection, a complete readable bank, and successful assembly. Expired weather must stop generation; absent/stale NOAA data must be announced as unavailable. Never substitute the imported historical bulletin when fresh generation fails. Offline fixtures in `work/bulletin/` are for tests only.

From a full repository checkout, run the existing autonomous tests and DMR/relay tests in a Linux environment with their dependencies. The transfer bundle is intentionally a runtime bundle and does not include the development fixtures/tests. In particular, verify both directions of TS2 forwarding and TS1 interruption behavior after any relay adaptation.

## 6. Verify one call, then enable the schedule

Once deployment includes authorization to transmit on the intended hotspot, use a single fresh manual call before enabling repeated transmissions:

```sh
sudo -u pi-star /usr/local/bin/pistar-weather-autonomous now
```

Confirm freshness, successful encode/decode checks, short parts with gaps, `ok: true` relay results, and `AUTONOMOUS_BULLETIN_SENT`. Confirm the local private recipient and that bulletin packets are not forwarded upstream. Obtain audible confirmation on the intended radio. Logs alone do not establish audible reception.

For the recorded requested quarter-hour schedule, keep `pistar-weather-frozen.timer` disabled and enable/start `pistar-weather-autonomous.timer`. It uses `Persistent=false` so missed calls are not replayed. Inspect `systemctl list-timers` and the service journal. Enable/start `pistar-weather-bootcheck.timer` after adapting its site-specific expectations. `OnBootSec=90s` may trigger promptly when first started on an already-running Pi.

If timer installation is authorized but RF confirmation is unavailable, clearly report that limit and follow the deployment task's explicit scheduling instructions; do not claim reception was tested. No recurring frozen playback should be enabled.

## 7. Finish and record the result

Review `docs/LOGGING.md` before optionally installing the recorded volatile-journal limits; preserve the site's current policy unless needed. Keep logs bounded and temporary bulletin artifacts in RAM. Synchronize writes and restore the root filesystem's previous read-only mode. Run the boot checker once, inspect `/run/pistar-weather/boot-health.json`, and explain any site-specific warnings rather than hiding them.

A reboot test, if part of the deployment task, should confirm bank persistence, modem/relay startup, current timer state, readiness waiting, private configuration readability, and a new boot-health report. Do not power-cycle the device as a substitute for an orderly reboot.

Write an English deployment report with a non-identifying target label, package SHA-256, installed source hashes, backup path, prerequisite versions, modified settings, previous/final timer states, offline/prepare/transmission results, receiver confirmation, root mount mode, and unresolved issues. Keep the report private if it includes identifying settings; never include secrets in a shared report.

## Known radio issue and rollback

Read `docs/radio-silence-20261108.md` and `docs/txhang-trial.md`. Audio previously disappeared after several cycles despite clean delivery logs. A manual MMDVMHost restart restored audible reception in one reported episode. A later TXHang=10 trial has no recorded proof of a lasting fix. Do not silently add periodic restarts, flash firmware, or declare the fault resolved based on software status.

To stop new calls, stop/disable the fresh timer as appropriate and stop an active weather service. Restore backed-up sources/units and previous enabled states for a failed update. If reverting the relay topology, restore only the saved direct DMR Network address/port, stop/disable the relay, and restart MMDVMHost while idle. Preserve newer unrelated settings. The legacy `rollback.sh` copies an entire old MMDVMHost configuration and can overwrite later changes; inspect it rather than execute it blindly. Restore root read-only mode and verify ordinary radio operation after rollback.
