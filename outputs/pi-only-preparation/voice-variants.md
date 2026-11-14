# Autonomous voice-bank variants

The first female voice in the original comparison was Silero Baya. Its original profile uses rate 1.0 and pitch 1.0. The operator requested this voice for autonomous playback on the hotspot.

Prepare a separate output directory containing a copy of `catalog.json` and `pilot-plan.json`. Change the copied catalog profile to the desired speaker, rate and pitch. Preserve entry IDs, Russian text, text hashes and audio paths. Keep the existing deployed bank until the complete replacement has been verified.

Run the existing offline generators against the new directory:

```sh
python work/pistar-autonomous/render_seed.py --all --output outputs/pi-baya
python work/pistar-autonomous/render_notice.py --output outputs/pi-baya
```

Both generators read the selected voice from the copied catalog. The notice must use the same profile as the phrase bank. Verify all 1,604 phrase hashes, text hashes, audio formats and durations, together with the fallback notice, before installation. Existing commands without `--output` continue to use the original catalog location.

Install the verified bank, catalog, bank manifest and fallback notice together while holding the weather lock. Preserve the current runtime sources and a private backup of the previous voice. Validate fresh assembly and encoding on the hotspot, then obtain receiver confirmation. After installation the hotspot fetches current data, assembles prerecorded phrases and encodes/transmits locally. Runtime operation requires no laptop or neural synthesis.

Changing the voice does not establish a fix for the documented intermittent RF failure. Raw deployment configurations and receiver identifiers remain private.
