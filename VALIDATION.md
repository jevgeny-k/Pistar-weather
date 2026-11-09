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
