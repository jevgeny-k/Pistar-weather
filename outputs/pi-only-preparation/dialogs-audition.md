# Local Dialogs-RU voice audition

The operator requested Russian female voices available without accounts or cloud synthesis. The public model `frappuccino/dialogs-ru-vits2` was downloaded at revision `af7eabc15d087fce701de7261190ccb747c3bc7a`. The checkpoint `averaged_G_615000.pth` is 529,555,187 bytes with SHA-256 `b565b7b5311bd29102f15d2700c69ea71569605bc756fb5bb49d98afdc5e1e43`. The model metadata reported unrestricted downloading. See the [upstream model card](https://huggingface.co/frappuccino/dialogs-ru-vits2) for its OpenRAIL terms and experimental model limitations.

The model source files and weights belong in `work/dialogs-ru`. The local audition used an isolated Python environment, CPU PyTorch 2.6.0, NumPy 1.26.4, SciPy and librosa. The short Russian sample texts contain explicit stress marks. Automatic accent placement and text normalization were disabled for these manually prepared samples.

`work/pistar-weather/dialogs_compare.py` generates labelled Masha and Sveta samples with speaker IDs 0 and 1 and emotion ID 1 (`happy`). The clips lasted approximately 8.85 and 8.77 seconds. Their manifest records source text, hashes, model revision and emotion settings. Generated audio and model weights remain outside Git.

`work/pistar-weather/audition_dialogs.py` runs on the hotspot against the transferred sample directory. It verifies hashes, resamples to 8 kHz and checks both samples through two actual native codec runs with relay calls stubbed. Passing `--now` then plays the two samples locally under the existing weather lock. Its isolated player uses the original sample voices for comparison. The production voice bank is selected independently.

Both samples passed deterministic native codec checks and were delivered through the local relay. The operator heard them and preferred Baya. The selected production voice is Baya with tempo 1.20 and pitch +150 cents.
