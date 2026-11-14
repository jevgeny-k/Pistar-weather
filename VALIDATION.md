# Local validation

The original import was verified before anonymization. That private import manifest and personalized history are no longer part of the public project.

The anonymous project uses private configuration for owner identity and startup expectations. Packet generation and relay startup must reject a missing radio ID. Tests use synthetic identities and temporary configuration files, never an operator's live ID.

Validation includes autonomous runtime/bank/readiness tests, bulletin logic tests, private configuration tests, source syntax checks, and an operator-metadata scan over the public working tree, fresh Git history, and generated transfer ZIP. The transfer builder validates all 1,604 phrase hashes and every bundled file against its transfer manifest.

The actual hotspot has not been changed or RF-tested during anonymization. Full DMR framing and UDP integration tests require their dependencies and a compatible operating system. Existing historical software delivery logs do not prove audible reception.

The anonymous version passed 18 local tests: 11 autonomous runtime/bank/readiness checks, 3 bulletin checks, and 4 private-configuration checks. The last group verifies rejection of missing/invalid IDs and rejection before DNS/network access. Full DMR/UDP tests were not run because `bitarray` and `dmr_utils3` are not installed in the available laptop environment.

## November 8 reliability updates

Added deterministic relay pacing tests, bounded HTTP retry tests, six RAM-cache integrity/fallback tests, and four Slot2 restoration tests. The live target passed ten retry/cache tests and a forced-fallback assembly plus all four encode/decode checks with network submission stubbed out (no RF). Its real cache remained unchanged. A fresh four-part submission populated the RAM cache; this is software-delivery evidence only.

The source port preserves anonymous site configuration and synthetic test identities. The phrase bank was not regenerated. Read `outputs/pi-only-preparation/radio-investigation-20261108.md` for measured timing and the unresolved RF limit.

The anonymized source port passed all 38 tests on the Pi in an isolated temporary directory: 21 autonomous checks and 17 relay/framing/configuration/restore checks. No test submitted packets to the real relay or changed live settings. On Windows, all 21 autonomous checks passed; full DMR integration there was limited by missing bitarray and AF_UNIX support. A new transfer bundle was built and verified with all 1,604 bank entries and the fallback notice.

## November 9 opt-in experiment

Added an opt-in cross-slot weather guard after a further confirmed silent-RF/PTT-timeout recurrence. All 22 relay/framing/configuration tests passed on the Pi, including five real-UDP guard tests and the existing pacing/isolation checks. Tests used a temporary directory, synthetic IDs and local sockets; they did not transmit through the live relay. Source default remains independent slots. See the diagnostic note for behavior, tradeoffs and rollback; a lasting RF fix has not been demonstrated.

## Whole-bulletin weather priority

At the operator's request, added an opt-in ownership lease spanning all weather parts. All30 relay tests passed on the Pi; full codec dry runs separately verified ownership release on success and simulated failure without RF. Current source preserves anonymous private-site settings. See `outputs/pi-only-preparation/weather-priority.md` for policy, bounded resource use, deployment and rollback. Audible confirmation and sustained reliability remain separate checks.

Autonomous playback now disables SoX automatic dithering for reproducible AMBE input. Two full offline codec runs on each of two four-part reports produced identical raw/AMBE/decoded hashes and passed the existing acceptance checks. The verification helper stubs every relay operation and redirects packet output to temporary storage. See `outputs/pi-only-preparation/codec-repeatability.md`; this does not resolve the separate RF/PTT fault.

Optional queue-onset diagnostics are described in `outputs/pi-only-preparation/queue-overflow-investigation-20261109.md`. Six Linux tests and a real bounded root-only RAM capture passed; evidence was copied privately, checksum verified and the recorder rearmed. The recorder is not an RF audio detector and does not restart the host automatically. Transfer bundles place it under an optional `diagnostics/` directory.

Recorder correction: a real root-only loopback integration test exposed that ETH_P_IP plus outgoing-only filtering omitted local weather copies on the Pi kernel. Capture now uses ETH_P_ALL followed by the same privacy filter. All seven diagnostic tests passed, including exactly-one-copy detection on an isolated local UDP socket with no RF. Older captures remain valid external-network/UART evidence but must not be treated as local weather pacing evidence.

## November 10 six-hour maintenance workaround

The operator explicitly requested this workaround after another silent report without a new host error. Seven Linux tests passed for shared-lock exclusion, PID/reservation/capture deferral, bounded failure and fresh-login readiness. A live test showed weather queued with no PID during maintenance and starting only after maintenance readiness. See `outputs/pi-only-preparation/modem-maintenance.md`. This is not an RF fault detector or a root-cause fix.

## Faster maintenance readiness

All 55 Linux relay/framing/configuration/maintenance tests passed for the updated relay/helper pair. A full live stop/start/new-login check measured 22.392819 seconds using journal monotonic timestamps; the operator confirmed audible speech afterward. Readiness now uses a root-only local confirmation after a new DMR login instead of waiting for the first periodic heartbeat. It does not skip native authentication or change the weather exclusion/six-hour schedule. See `outputs/pi-only-preparation/faster-maintenance-readiness.md` for trust boundaries, the live startup-race correction and fallback behavior.
