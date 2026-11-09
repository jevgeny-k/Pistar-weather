# Experimental cross-slot weather guard — November 9

The intermittent RF/audio fault recurred after an operator-reported long working interval. PTT also gave repeater timeout. A host-only restart restored audible reception. Current weather generation, HTTP fetches, temperatures and modem status did not identify the failed RF state. This is not a confirmed firmware fix.

The daily log contained 234 local weather-part headers, 34 of which began while TS2 was logged active. This coarse log correlation motivates a reversible experiment; it does not prove causation.

## Opt-in behavior

Enable `--serialize-slots`, or set `PISTAR_WEATHER_SERIALIZE_SLOTS=1` in a systemd relay drop-in. The source default stays off. With the flag enabled, weather waits for at least 12 seconds without real DMR traffic on either slot. This interval is selected for the inspected target's TXHang=10; it is not a universal calibration value. Incoming real traffic on either slot interrupts an active weather part with its local terminator and then forwards normally. Announcement audio is never forwarded upstream.

This reduces simultaneous local weather and group activity; it cannot promise zero RF overlap when a new call arrives while buffered weather frames are draining. It does not stop overlap between ordinary non-weather traffic on two slots.

Busy waiting is bounded by the existing 180-second relay deadline per part. A new call can truncate a report; sustained activity can skip it. The next quarter-hour timer still runs. There is no automatic replay/restart loop. Existing TS2 groups, modem settings, identity and voice bank are preserved. Ordinary independent TS2 behavior remains the default when the flag is absent.

## Validation and observation

All 22 relay/framing/configuration tests passed on Linux, including five new real-UDP tests for the idle guard, both traffic directions, interruption order, bounded queue expiry, no injection upstream and default-mode compatibility. The original pacing tests still pass. This does not establish long-term RF reliability. Receiver confirmation and sustained observation are required after installation.

## Reversible deployment

Back up current relay source, retain enabled timer states, and install while no bulletin is running. Install the source and an opt-in `[Service]` drop-in with `Environment=PISTAR_WEATHER_SERIALIZE_SLOTS=1`, reload systemd and restart the relay/host while idle. Wait for an actual new master login before testing; after a host-only restart an old relay peer can temporarily look ready.

To stop the experiment, remove only the dedicated environment drop-in, reload systemd and restart the relay/host while idle. The same source then uses its previous independent-slot behavior, including the corrected 60 ms packet schedule. Keep backups private. Return the root filesystem to its prior read-only state and retain bounded RAM logs. No firmware flash or periodic reset workaround is included.

Installed on the inspected target with a private backup and dedicated opt-in drop-in. The receiver confirmed the short test was audible. Its logged TS1 header began at14:41:37.348 UTC, after the preceding TS2 end at14:41:25.234 UTC (12.114 seconds). The test had been queued at14:40:06 UTC and waited rather than overlapping the ongoing conversation. This is one confirmed trial, not proof of sustained reliability. The quarter-hour timer remains enabled; root is read-only and logs remain bounded in RAM.
