# Baya presenter-style audition

The operator requested a delivery resembling a television weather presenter. The installed Silero v5_6_ru package supports SSML prosody and pauses, word-focus markup, emphasis and exclamation intonation. Its public [model documentation](https://github.com/snakers4/silero-models#v5) and [SSML reference](https://github.com/snakers4/silero-models/wiki/SSML) describe the available controls. A named television-presenter preset is not part of the installed interface.

The audition generator `work/pistar-weather/silero_presenter.py` uses Baya to synthesize one coherent sample paragraph with short SSML pauses and model-level emphasis on selected weather words. It uses the installed package's `**word**` emphasis syntax with intensity 2. Synthesis rate and pitch are medium. The spoken text explicitly identifies the forecast as a trial.

The resulting source clip is approximately 16.81 seconds at 48 kHz. The manifest records the SSML, intensity, model hash and WAV hash. Generated audio remains outside Git.

The hotspot audition helper accepts `--use-playback-profile` to include the selected production tempo and pitch during this Baya comparison. Its default comparison mode remains independent of that profile. The Baya audition used the accepted tempo 1.20 and pitch +150 cents, passed two native codec checks with identical artifacts and was submitted through the local private relay.

The production service assembles prerecorded phrases. A coherent paragraph audition evaluates the model's delivery in that context. Applying the style throughout autonomous reports requires preparing suitable phrase-bank recordings and checking assembled reports separately. Receiver preference is pending at the time of this record.
