# Pi-Star voice weather service

Start with [CODEX-HANDOFF.md](CODEX-HANDOFF.md) to transfer and configure this project on a hotspot. It identifies current sources, deployment paths, prerequisites, verification steps, rollback, and the unresolved radio issue.

This repository collects work from November 7, 2026, including fixes after midnight on November 8. It provides Riga weather from Open-Meteo, NOAA space weather, Russian Silero Xenia speech, and local private DMR announcements through Pi-Star.

## Download the complete hotspot package

Download [pistar-weather-transfer.zip](https://github.com/jevgeny-k/Pistar-weather/releases/latest/download/pistar-weather-transfer.zip) and its [SHA-256 checksum](https://github.com/jevgeny-k/Pistar-weather/releases/latest/download/pistar-weather-transfer.zip.sha256) from [GitHub Releases](https://github.com/jevgeny-k/Pistar-weather/releases/latest).

The release ZIP contains **all 1,604 prerecorded audio phrases**, the catalog and audio/text hashes, current runtime and relay code, the preserved ARM AMBE encoder, systemd units, and English deployment instructions. Extract it and start with `CODEX-HANDOFF.md`. GitHub's automatically generated **Source code** archives contain only tracked source files; use the named transfer ZIP for installation.

The hotspot assembles fresh reports from the included phrase bank. It does **not** run Silero or PyTorch. You still need the documented Pi-side dependencies and a private `site.json` with your owner ID and upstream master before transmission can work. No private settings or API keys are included.

The optional **Silero v5_6_ru** model is approximately 148 MB and is used on a laptop only to create new phrases. Existing generation scripts download it from the [official model URL](https://models.silero.ai/models/tts/ru/v5_6_ru.pt) when missing. See [THIRD-PARTY.md](THIRD-PARTY.md) for provenance and upstream license references. It is not needed to use the released audio bank.

## Project layout

- `work/pistar-weather/`: current relay, DMR framing, laptop speech generator, fallback weather command, and tests.
- `work/pistar-autonomous/`: current autonomous runtime, phrase selection, assembly, playback, startup checks, and tests. Develop and deploy from here.
- `work/silero/`: voice profile and local model.
- `work/bulletin/`: historical inputs used by tests; never substitute these for fresh weather.
- `outputs/pi-only-preparation/`: catalog, checksums, systemd units, operational notes, and the local 1,604-phrase bank. The audio is distributed in the release ZIP.
- `assets/encode`: locally preserved native encoder, ignored by Git.
- `config/site.example.json`: public template; supply real operator settings separately.
- `outputs/weather-bulletin/` and `outputs/silero-voices/`: historical audio examples.
- `tools/build_transfer.py`: deployment bundle builder using current sources and the complete bank.
- `PRIVACY.md`: distribution boundary and private configuration guidance.

Keep the `work/` and `outputs/` layout: tools compute paths relative to the repository root. Personalized histories, manifests, old snapshots, and archives were moved outside this repository. The public repository starts from a new anonymous Git history. New documentation, source comments, and deployment instructions are English. Russian speech strings, catalog text, test expectations, and recorded bulletin transcripts are application data and remain Russian.

## Development checks

Python 3.12 was used on the laptop. Windows needs `tzdata` for `zoneinfo`.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s work/pistar-autonomous -p "test_*.py"
.\.venv\Scripts\python.exe -m unittest discover -s work/pistar-weather -p test_bulletin.py
```

The autonomous runtime uses the standard library and the prepared bank. Playback additionally needs the Pi-side virtual environment with `bitarray` and `dmr_utils3`, SoX, and a compatible native AMBE encoder. Torch is only needed to regenerate speech on the laptop. See the historical [dependency lock](requirements-laptop-lock.txt).

## Assets and version control

The model, audio, generated transfer ZIP, and native encoder are ignored by Git to keep source history small. Audio and the encoder are distributed through GitHub Releases. A Git clone alone is incomplete for deployment; download the named release ZIP above. To rebuild a bundle from a clone, restore `autonomous/bank/` from that ZIP into `outputs/pi-only-preparation/bank/`, and `relay/encode` into `assets/encode`, then run `python tools/build_transfer.py`. No license has been assigned to the original application code; third-party components retain their own licensing requirements.

See [VALIDATION.md](VALIDATION.md). Repository and package preparation do not change the hotspot.

## Private settings

No operator ID is embedded in public code. Before deployment, supply `/etc/pistar-weather/site.json` using `config/site.example.json` as a template. A missing ID blocks transmission. For local execution, explicitly set `PISTAR_SITE_CONFIG` to the private file. Never commit or bundle this file. Public Riga city-center defaults and Russian speech are demonstration content, not a private operator address. See [PRIVACY.md](PRIVACY.md).

## November 8 reliability changes

Current `main` adds corrected 60 ms relay pacing, bounded retries for transient HTTP failures, and explicitly announced replay of the last successful bulletin from a single RAM cache. See [fallback behavior](outputs/pi-only-preparation/FALLBACK.md), [radio investigation](outputs/pi-only-preparation/radio-investigation-20261108.md), and [validation](VALIDATION.md). Intermittent silent RF transmission remains under investigation.

These changes postdate the original v0.1.0 release asset. To include them, use current source plus the phrase-bank/encoder assets from that release and rebuild with `tools/build_transfer.py`; the builder includes both fallback-notice assets. The existing release ZIP has not been replaced by this source update.

An optional [cross-slot weather guard](outputs/pi-only-preparation/cross-slot-guard-20261109.md) is available for an ongoing reliability trial. It makes weather yield to traffic on either slot and may truncate or skip reports on busy groups. It is off by default and does not claim to fix modem firmware.

[Whole-bulletin weather priority](outputs/pi-only-preparation/weather-priority.md) is now available as an alternative to yielding to TS2. It skips new network calls during the entire report, including gaps, and restores groups afterward. Both policies remain opt-in; choose one explicitly.
