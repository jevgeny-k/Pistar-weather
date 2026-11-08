# Replay the last bulletin when weather is unavailable

After unsuccessful weather retrieval, replay the last bulletin whose complete local relay submission succeeded. The Russian Xenia notice says: "Свежие погодные данные недоступны. Повторяю предыдущую сводку."

The original report time and forecast remain unchanged. One atomically replaced ZIP lives at `/run/pistar-weather/last-bulletin.zip`, in RAM. It does not grow over time or write bulletin audio to the SD card. After reboot, one successful fresh transmission is required before fallback is available. Missing or damaged caches fail without an empty transmission. A replay never renews the cache age.

Only explicitly unavailable or stale weather selects this fallback. Codec, software, and radio failures still fail visibly. Space-weather sources retain their own unavailable-data announcements. Successful relay submission does not prove audible reception.

Install `bulletin_cache.py`, `retry_http.py`, updated `autonomous.py`, `runtime.py`, `play.py`, and both `fallback-notice` files as a consistent set. The notice is separate from the 1,604-entry phrase bank. Preserve its WAV checksum and metadata. `render_notice.py` can regenerate it using the existing laptop voice model and chosen profile; no model is required on the Pi.
