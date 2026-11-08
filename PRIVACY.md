# Anonymous distribution and private configuration

Share only this project directory or its newly generated transfer ZIP. Do not share its parent workspace: original personalized backups and audit helper files are stored outside the project.

Operator IDs, callsigns, local host addresses, Wi-Fi profile names, frequency plans, static-group membership, workstation usernames, SSH host keys, old import manifests, personalized snapshots, and original archives have been removed from this distribution. HTTP User-Agent strings use a generic application name. The Git repository has a new anonymous history; previous history is retained only in a separate private backup.

`config/site.example.json` is the only site file permitted in the public bundle. A real `site.json` belongs on the target under `/etc/pistar-weather/` or in an explicitly selected ignored local file. It is never discovered by the transfer builder. API keys and SSH credentials are not part of site settings or this distribution. The optional BrandMeister key remains root-only on the hotspot and is sent only to the configured official API operation; do not log it.

The public weather fixtures, Russian phrase bank, city name, rounded demonstration coordinates, and timezone refer to Riga. They describe the example weather service, not a home address. The bank and audio checksums remain aligned. A different city/language can require additional voice assets.

The public configuration has no usable owner ID or upstream master. Packet generation, validation, and relay startup fail until the operator supplies the private settings. Supplying the real ID is required for deployment; keep that deployment context private. Do not put identities back into shared examples, error messages, logs, or reports.

The native encoder and speech model are third-party binaries retained locally. Text and identity scans do not constitute a full third-party binary security audit. Inspect licensing and verify compatible runtime dependencies before deployment.
