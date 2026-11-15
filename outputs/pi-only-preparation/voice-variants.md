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

## Baya deployment validation

The Baya bank was completed and installed on November 14, 2026, with rate 1.0 and pitch 1.0. All 1,604 phrase files passed text/audio hash, format, duration and level checks. The bank contains 84.68 minutes of prerecorded audio. The voice-only ZIP is 73,240,835 bytes with SHA-256 `004680ea621290f84e7f86cf91b10ae61d448c07c0316087bb4d57a3a8d9a8eb`.

The hotspot verified the archive and every installed phrase, prepared a fresh four-part report and ran the actual playback codec twice with all relay requests stubbed. Both passes produced identical raw, AMBE and decoded artifacts. The staged bank replaced the active bank under the weather lock. Current runtime sources were copied from the live installation, and the previous complete voice/runtime directory was preserved privately for rollback. The existing timer was restored and the root filesystem returned to read-only mode.

The operator explicitly postponed the audible RF audition. No additional live test was started. Receiver audibility and the preferred voice sound remain unverified for this deployment.

## Service-user permissions correction

The resumed audition on November 15 exposed a deployment error. A restrictive root umask left the extracted bank and top-level directory inaccessible to the weather service user. The earlier root-only preparation and codec checks passed, but scheduled service starts failed with permission denied before playback.

Set public runtime/bank directories to mode 0755 and their Python, JSON, WAV and operational documentation files to mode 0644. Apply these modes only inside the intended voice/runtime directory. Preserve the permissions of private credentials and backups. The private installer now sets these modes explicitly and runs staged preparation and codec checks as the configured service user before activation.

After correction, preparation through the installed wrapper as the service user succeeded. A real systemd service run subsequently reached the first RF call. Complete report delivery and receiver feedback must be checked independently of that first-call observation.

## Selected energetic playback

The operator heard Baya and requested a more energetic delivery. After two radio auditions, the operator selected tempo 1.20 and pitch +150 cents, approximately a 9% pitch increase. The synthesis bank retains its original voice profile. The selected playback transformation runs locally through SoX on the hotspot.

Copy `config/baya-playback.json` beside the installed `play.py` as `playback-profile.json`. The playback code validates the profile and transforms the checked source WAV before the existing codec pipeline. The source cache stores the assembled audio, so both fresh and fallback playback apply the profile once per transmission. The fallback notice receives the same treatment. A bank without a playback profile uses the existing processing path.

Staged verification ran as the weather service user. A fresh four-part report passed two actual native codec runs with relay requests stubbed, producing identical raw, AMBE and decoded results. The reviewed player and selected profile were installed together under the weather lock, with a private backup and explicit readable file modes. The root filesystem returned to read-only mode and the quarter-hour timer was restored.

## Bounded codec headroom recovery

A subsequent scheduled Baya report hit the decoded-audio peak limit. The second and fourth parts of a reproduced report reached a decoded peak of 32767 with the existing -3 dB normalization. Encoding those parts at -6 dB produced peaks of 24578 and 20341 and passed the original audio guard.

The player now retries a saturated part at normalization targets -6 and -9 dB after the initial -3 dB attempt. Each attempt uses the same checked source audio and runs both encoding and decoding. Duration checks, the minimum usable level and rejection of saturated decoded output remain enforced. Persistent saturation fails after three attempts. Quiet or invalid-duration audio fails immediately. Four focused regression tests cover these paths.
