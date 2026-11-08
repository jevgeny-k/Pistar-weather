# Instructions for Codex

Read `CODEX-HANDOFF.md` before preparing or deploying this service.

- Write documentation, comments, docstrings, and maintenance instructions in English.
- Preserve Russian speech content and matching test expectations unless the user requests a voice-language change. These strings are application data.
- Use `work/` as current source code. Historical ZIPs and snapshot copies are not authoritative deployment sources.
- Never replace current sources with files from an older archive.
- Keep credentials on the hotspot. Do not commit passwords, API keys, full live configurations, or private backups.
- Preserve hotspot identity, frequencies, modem configuration, Wi-Fi, and credentials unless the task explicitly requires changes.
- Distinguish software delivery from audible radio reception. Intermittent loss of audio remains unresolved.
- Do not regenerate the phrase bank to translate documentation. Text and audio hashes must remain aligned.
- Record deployment results and outstanding checks in English.
- Keep all operator IDs, callsigns, Wi-Fi profiles, private network addresses, and live radio configuration out of public source and documentation. Use private `site.json`; only `config/site.example.json` may be committed.
- Missing `radio_id` must disable packet generation and playback. Tests must use synthetic IDs.
- Never include private backups or old Git histories in a transfer archive.
