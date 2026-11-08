# Third-party components and released assets

## Prerecorded speech bank

The 1,604 phrases were generated using [Silero Models](https://github.com/snakers4/silero-models), Russian model `v5_6_ru`, voice `xenia`. Processing increased speech rate by 8% and pitch by 15%; the deployed bank is mono, 8,000 Hz, 16-bit PCM WAV. Phrase text and audio hashes are recorded in the catalog and bank manifest. These are generated weather phrases, not recordings of the operator's voice.

The optional model is downloaded from `https://models.silero.ai/models/tts/ru/v5_6_ru.pt`. Upstream publishes its main model license at [LICENSE](https://github.com/snakers4/silero-models/blob/master/LICENSE) (CC BY-NC-SA 4.0); consult upstream terms for the particular model and intended use. This release does not redistribute the model or assign a new license to third-party materials.

## AMBE encoder

`relay/encode` is the preserved Linux ARM binary used by the original project. The project wrapper source is `relay/encode.c`. It uses [nostar/md380_vocoder](https://github.com/nostar/md380_vocoder), based on [md380tools](https://github.com/travisgoodspeed/md380tools). The upstream source header identifies Doug McLain as copyright holder and states GPL version 2 or later. The release includes upstream source references/files and a GPL license copy under `third_party/md380_vocoder/`.

The upstream build obtains MD380 firmware/RAM images separately; their rights and platform constraints are separate from the wrapper's source license. The exact original compiler invocation was not recorded. Rebuild and verify the encoder when the preserved binary is incompatible with the target. Upstream describes ARM support and excludes original Pi Zero/Pi 1; do not assume this binary works on every Pi or a different OS.

## Other runtime dependencies

Python, SoX, `bitarray`, `dmr_utils3`, and optional laptop PyTorch dependencies are installed separately and retain their own licenses. Open-Meteo and NOAA provide weather data; follow their attribution and service terms. No private credentials are included in the release.
