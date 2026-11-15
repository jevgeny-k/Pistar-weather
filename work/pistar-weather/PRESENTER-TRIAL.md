# Attributed presenter-reference audition

This is an optional, explicitly synthetic voice experiment, not a production voice change. The autonomous Baya bank and its selected playback profile remain installed on the hotspot.

## Reference and analysis

The reference is the archived [Irina Polyakova forecast dated February 4, 2012](https://www.youtube.com/watch?v=BHBP-j-eW1Q). Her presenter role is described by [Meteo-TV](https://meteo-tv.ru/weather-faces/irina-polyakova/). Attribution does not imply participation or endorsement.

The opening advertisement must be excluded. The analysis uses the actual forecast from 40 to 100 seconds; initial measurements including the advertisement were discarded. On that excerpt, pYIN estimates a 10th-to-90th percentile pitch range of 7.4 semitones and energy-based pauses have a median of 0.285 seconds. ASR suggests roughly 175–180 words per minute. Background music and ASR errors limit these estimates; these numbers are descriptive, not exact speaking targets.

`analyze_presenter.py` measures local audio without uploading it. `prepare_presenter_reference.py` extracts a short word-aligned reference. Inspect the transcript against the recording before treating it as a reliable conditioning transcript; automatic transcription contains errors. Raw broadcast audio, captions, transcripts, signed download URLs and local model caches stay outside Git.

## Local generation experiment

`f5_presenter_trial.py` uses [F5-TTS Russian](https://huggingface.co/Misha24-10/F5-TTS_RUSSIAN), revision `ea166adeae4c80ec5ee423a671e2bdb83906cf84`, checkpoint `F5TTS_v1_Base_v2/model_last_inference.safetensors` (1,348,435,761 bytes; SHA-256 `f11e788c8d2d86b8d6e3e2e7a12c583932d2494b015b544793c1924360b474d3`). The vocabulary comes from `F5TTS_v1_Base/vocab.txt` at the same revision. The model card specifies CC BY-NC 4.0; review model and reference rights before redistribution or commercial use.

The isolated preparation environment uses F5-TTS 1.1.10, CPU Torch/Torchaudio 2.6.0 and Vocos. No account is required for these public downloads. On the preparation laptop, eager Trainer and Transformers ASR imports were changed to lazy imports inside the isolated environment to avoid loading unused training/recognition dependencies. This compatibility workaround is not installed on the Pi.

The trial quantizes Linear layers dynamically to int8 and uses 32 inference steps with seed 2026. The fixed Riga text is an audition script, not a current weather report. Generated WAV and metadata go to `outputs/f5-presenter/`. Generation is resource intensive on a 4 GB laptop; running this model on the 1 GB Pi has not been validated. A future autonomous version would use an approved prerecorded phrase bank generated beforehand.

## Radio validation

Use the existing `audition_dialogs.py` helper with the generated directory. Its default isolates playback from the Baya tempo/pitch profile, verifies checksums and duration, and requires two identical native encode/decode runs before transmission. An audition uses the shared weather lock and existing private site configuration. Do not install F5, its checkpoint or the source recording on the Pi. Audible quality still requires listener feedback; successful codec or relay checks alone do not prove reception.

Status: the synthetic sample was generated successfully (5.963 seconds; 873.8 seconds of generation on the preparation laptop). WAV SHA-256: `15103bbd2fa8af1a12ee3d6ab77f9cbbd77c54e25e9bca59d6fcab7e1af01b61`. Two native codec passes on the Pi produced identical artifacts, and the existing private relay accepted the audition for local modem delivery. Listener feedback is pending; this does not establish audible reception or preferred voice quality. Production remains on Baya.

## Clean-reference correction

The listener initially heard no audition. After bounded diagnostics and a protected MMDVMHost restart, the same sample became audible and was rejected for poor quality and noise. It is not an approved replacement for Baya. Neither background music nor int8 quantization has been established as the cause of those artifacts.

The next reference is [Julia Menshova's own-channel monologue](https://www.youtube.com/watch?v=6p8_hfoLm44), beginning at 60 seconds. A word-aligned 5.07-second excerpt contains one speaker. Its SHA-256 is `8b63d57dcec5aafaf18e61eea77a0f536a2c05825bbf1b5fe98242d41e2c78e2`. Raw source audio, its ASR transcript and the excerpt remain private.

`screen_reference_audio.py` runs the [Audio Magic ONNX conversion of Google's YAMNet](https://huggingface.co/audiomagic/yamnet-onnx), revision `f25b741c2f0bdc6d7e6db24b5fddda23347dbafd`. ONNX SHA-256: `d3835ffbbd4a1bb3e777f0ca217b5007907f5171dd5d17c4236b95b2af8f908e`. It consumes mono 16 kHz waveform and uses the accompanying AudioSet class map. The exact new excerpt scored mean Speech 0.99624 and mean Music 0.0000422 (maximum Music 0.0001337). Scores are model outputs, not calibrated probabilities or proof of perceptual quality. In particular, the rejected old excerpt also received low music scores; the previous assumption that music caused the noise remains unproven.

The renderer now requires attribution and screening metadata matching the exact reference WAV hash. It rejects mean Music above 0.02, any Music frame above 0.10, or mean Speech below 0.5. These are conservative experimental screening thresholds, not a validated guarantee against all background sounds. Use `--reference` and `--output` for separate trials. Full-precision inference is now the default; `--int8` explicitly selects the previous quantization experiment. Progress is logged every four flow evaluations.

The clean-reference, full-precision trial completed: 4.395 seconds of audio in 912.06 seconds of inference. WAV SHA-256: `ae0c24ea2283e18ef0931eddd390940a5a6acccf7894b2875ca77ec912e6128b`. The output scored mean Speech 0.98804 and mean Music 0.0005176 (maximum 0.0044678). These scores do not establish that synthesis noise is absent.

`transcribe_audition.py` checks the generated manifest against local Whisper base/int8 transcription and writes private `asr-check.json`. It decodes PCM through SoundFile and resamples explicitly to avoid the local PyAV API incompatibility. The trial scored word error rate 0.3077, passing the loose experimental 0.35 threshold, with errors around an adjective and the final imperative. This provides limited intelligibility evidence; it is not a claim of clean diction or listener approval.

Two actual native codec runs on the Pi produced identical artifacts (270 AMBE frames). The existing private relay accepted the new audition (96 packets) for local modem delivery. Listener feedback is pending. Production remains unchanged. All inference and source-analysis tools are preparation-laptop utilities; the Pi still uses its autonomous prerecorded bank.
