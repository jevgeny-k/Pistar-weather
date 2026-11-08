# Complete autonomous weather package

Download **pistar-weather-transfer.zip** and **pistar-weather-transfer.zip.sha256** from this release's assets. The automatic GitHub source archives do not include audio.

The transfer ZIP includes:

- All 1,604 Russian Xenia audio phrases (8 kHz, mono, PCM 16-bit).
- Catalog, text/audio SHA-256 records, and a complete transfer manifest.
- Current autonomous runtime, relay, readiness checks, and systemd units.
- The preserved ARM AMBE encoder, wrapper source, upstream source files, and notices.
- English deployment instructions and an empty site configuration template.

Verify the ZIP using its checksum, extract it, and read **CODEX-HANDOFF.md**. Install the documented Pi-side dependencies and supply your private `/etc/pistar-weather/site.json` before enabling transmission. No owner ID, API key, password, or live configuration is included. An unconfigured copy cannot transmit.

**Silero/PyTorch is not required on the hotspot.** The included prerecorded bank is used to assemble fresh weather reports. The optional Silero v5_6_ru model is only needed on a laptop to regenerate phrases and is downloaded by the generation scripts from the official upstream.

The preserved encoder is architecture-specific. This package is not an unattended installer and does not claim to resolve the historical intermittent RF/audio issue. Read the deployment checks and diagnostic notes.
