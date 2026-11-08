# Pi-Star voice weather service

Start with [CODEX-HANDOFF.md](CODEX-HANDOFF.md) to transfer and configure this project on a hotspot. It identifies current sources, deployment paths, prerequisites, verification steps, rollback, and the unresolved radio issue.

This repository collects work from November 7, 2026, including fixes after midnight on November 8. It provides Riga weather from Open-Meteo, NOAA space weather, Russian Silero Xenia speech, and local private DMR announcements through Pi-Star.

## Project layout

- `work/pistar-weather/`: current relay, DMR framing, laptop speech generator, fallback weather command, and tests.
- `work/pistar-autonomous/`: current autonomous runtime, phrase selection, assembly, playback, startup checks, and tests. Develop and deploy from here.
- `work/silero/`: voice profile and local model.
- `work/bulletin/`: historical inputs used by tests; never substitute these for fresh weather.
- `outputs/pi-only-preparation/`: complete 1,604-phrase bank, catalog, checksums, systemd units, operational notes, and anonymized operational notes.
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

The model, audio, generated transfer ZIP, and native encoder are present locally but ignored by Git. A Git clone alone is incomplete for deployment. Transfer the new bundle or copy these assets separately. No remote repository is configured. No license has been assigned to the original application code; third-party components retain their own licensing requirements.

See [VALIDATION.md](VALIDATION.md). Repository and package preparation do not change the hotspot.

## Private settings

No operator ID is embedded in public code. Before deployment, supply `/etc/pistar-weather/site.json` using `config/site.example.json` as a template. A missing ID blocks transmission. For local execution, explicitly set `PISTAR_SITE_CONFIG` to the private file. Never commit or bundle this file. Public Riga city-center defaults and Russian speech are demonstration content, not a private operator address. See [PRIVACY.md](PRIVACY.md).
