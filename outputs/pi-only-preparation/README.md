# Autonomous Pi-Star weather preparation

The full 1,604-phrase bank was generated and installed on November 7, 2026. Read `STATUS.md`, `OPERATIONS.md`, and the repository-root `CODEX-HANDOFF.md` before deployment. This folder also retains early pilot artifacts, which are historical examples rather than current weather.

The original pilot contained 20 phrases and a 21.91-second demonstration. The current `bank/` is complete. `catalog.json` describes texts, phrase identifiers, and supported values; `bank-manifest.json` records text/audio hashes and the voice profile. Audio format: WAV, 8,000 Hz, mono, 16-bit PCM. The authoritative deployment sources are in `work/` at repository root; obsolete source snapshots are no longer distributed.

The catalog supports temperature -50 to +50 C in 0.5-degree steps, feels-like temperature -60 to +60 C, wind 0 to 70 m/s, gusts 0 to 90 m/s, humidity and precipitation probability 0 to 100%, and pressure 900 to 1,100 hPa. Values outside these ranges must not be silently clipped.

The pilot assembled identically on the laptop and Pi (SHA-256 `f34f8e2dda1349bf7f3c40e2dec72576c8717099e62c01edbbca2886caea3958`). Missing/corrupt audio was rejected. The pilot's temporary installation was `/tmp/pistar-autonomous-pilot`; the later permanent installation is `/opt/pistar-weather/autonomous-v1`.

The obsolete bank ZIP and personalized laptop snapshot were removed from the anonymous distribution. Use the current transfer bundle. Private live configuration backups remain root-only on the Pi and are not included here.
