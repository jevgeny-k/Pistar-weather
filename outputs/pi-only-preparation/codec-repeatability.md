# Repeatable vocoder input

During the November 9 RF investigation, one recovery audition was rejected by the existing decoded-audio guard before transmission. This is distinct from the silent-RF/PTT-timeout fault.

Three offline runs on an identical stored WAV produced different raw PCM and AMBE hashes. Decoded peaks were29458,32352 and26184, despite unchanged input and processing parameters. SoX automatic dithering made the conversion nondeterministic before the nonlinear speech codec.

Autonomous playback now passes `-D` to SoX to disable automatic dithering. Voice, gain, filters, sample rate, duration, checksum validation and strict decoded-audio acceptance bounds remain unchanged. This is a reproducibility correction, not proof that every possible future phrase will pass or that the RF fault is fixed.

All four stored parts were encoded/decoded twice without dithering; raw, AMBE and decoded artifacts matched exactly. All passed the existing audio checks. The reusable `verify_codec_repeatability.py` then exercised the actual updated playback code twice on a second fresh four-part report, with all relay access stubbed and packet output redirected to a temporary directory. Every artifact again matched and ownership was released. No RF was transmitted by these checks.

Run the helper with the Pi playback interpreter and a prepared bulletin directory. It copies inputs to temporary storage, runs real SoX/native encode/decode, and never contacts the relay. `--cached` is only for an explicitly prepared fallback manifest with its spoken notice. Successful offline validation does not establish audible reception.
