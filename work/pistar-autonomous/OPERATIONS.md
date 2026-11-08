# Autonomous weather operations

Voice: Silero v5_6_ru, Xenia, speech rate +8%, pitch +15%. The laptop neural model generated the bank once. The Pi fetches fresh Open-Meteo and NOAA data, selects prerecorded phrases, assembles WAV files, encodes AMBE, and transmits locally. The laptop and an LLM are not needed during operation; internet access on the Pi is required.

Installation: `/opt/pistar-weather/autonomous-v1`. The 1,604-phrase bank lives on the SD card. Temporary bulletins use `/tmp` and are removed after execution. Normal root filesystem operation is read-only.

```sh
pistar-weather-autonomous prepare  # Fetch and assemble without transmitting
pistar-weather-autonomous now      # Fetch, assemble, and transmit
sudo systemctl stop pistar-weather-autonomous.timer  # Stop scheduled calls
```

Transmission is a local private DMR call to <OWNER_DMR_ID>, TS1, CC1. Bulletin packets are not sent to BrandMeister. Ordinary TS1 traffic takes priority; TS2 traffic passes through independently. Speech parts are shorter than 40 seconds with five-second gaps. Concurrent runs are locked out.

The latest recorded schedule runs at :00, :15, :30, and :45. Missed runs are not replayed. The frozen-recording timer is disabled. Earlier documents describing no schedule refer to earlier development stages. The old `pistar-weather` fallback command remains separate and uses Piper/Irina.

Observations older than 90 minutes are rejected. Prepared bulletins older than 30 minutes are rejected before each transmission. Stale NOAA information is announced as unavailable; forecasts are distinguished from observations. Missing/corrupt phrases stop assembly. Out-of-range numbers use an explicit unavailable phrase rather than clipping to the supported range. Insufficient weather forecast data prevents transmission.

The original installation ZIP predates startup-readiness fixes and boot checks. Deploy current sources using `CODEX-HANDOFF.md`, not the ZIP alone. Preserve the laptop snapshot as a separate fallback.
