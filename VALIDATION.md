# Local validation

The original import was verified before anonymization. That private import manifest and personalized history are no longer part of the public project.

The anonymous project uses private configuration for owner identity and startup expectations. Packet generation and relay startup must reject a missing radio ID. Tests use synthetic identities and temporary configuration files, never an operator's live ID.

Validation includes autonomous runtime/bank/readiness tests, bulletin logic tests, private configuration tests, source syntax checks, and an operator-metadata scan over the public working tree, fresh Git history, and generated transfer ZIP. The transfer builder validates all 1,604 phrase hashes and every bundled file against its transfer manifest.

The actual hotspot has not been changed or RF-tested during anonymization. Full DMR framing and UDP integration tests require their dependencies and a compatible operating system. Existing historical software delivery logs do not prove audible reception.

The anonymous version passed 18 local tests: 11 autonomous runtime/bank/readiness checks, 3 bulletin checks, and 4 private-configuration checks. The last group verifies rejection of missing/invalid IDs and rejection before DNS/network access. Full DMR/UDP tests were not run because `bitarray` and `dmr_utils3` are not installed in the available laptop environment.
