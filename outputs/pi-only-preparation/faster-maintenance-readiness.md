# Faster authenticated maintenance readiness

The measured protected host recovery originally took about 30–32 seconds. The host finished its own master login before the relay's `connected` flag became true: the relay waited for the first periodic `MSTPONG`, roughly ten seconds later. The installed host's initial ten-second login retry timer and native modem initialization are unchanged.

Protocol reference: [DMRDirectNetwork.cpp at the reported host revision](https://github.com/g4klx/MMDVM-Host/blob/218a017/DMRDirectNetwork.cpp). The successful DMR master-login log follows the final configuration/options acknowledgement. No synthetic acknowledgement, password handling or native host/firmware patch is needed.

## Readiness confirmation

The maintenance helper fully stops the old host, snapshots the login-log cursor, then starts the new host. This excludes a late login from the old process. Only a new `DMR, Logged into the master successfully` line qualifies; another protocol's login does not.

After that evidence, if the relay still awaits its first heartbeat, the helper sends `confirm_host_login` through the existing private Unix control socket. The relay checks kernel `SO_PEERCRED` credentials for UID 0 and requires the supplied host peer to match its current peer. It then marks connection readiness without waiting for another heartbeat. Ordinary non-root weather clients cannot invoke this confirmation. A changed peer is rejected.

If confirmation is unavailable or declined, the helper falls back to the existing heartbeat check. Confirmation is attempted only once per recovery; rejected peer evidence is not repeatedly promoted to readiness. Fresh login evidence remains mandatory. The ordinary weather lock, running-PID/reservation/capture guards, weather ordering and six-hour timer policy are unchanged.

The live installation test exposed a separate startup race: a simple service can be considered started before its Unix socket is listening. That attempt failed before restarting the host; queued weather continued. The helper now defers safely while relay status is unavailable, within its existing bounded wait, instead of immediately failing. Persistent unavailability still causes no restart.

## Results

All 55 Linux relay/framing/configuration/maintenance tests passed, including real root-peer confirmation, rejection of non-root or changed-peer confirmation, old/other-protocol login rejection, compatibility fallback, stop-before-log-cursor ordering and transient/permanent socket unavailability.

The final full stop/start/authentication check took **22.392819 seconds**, measured between maintenance restart/ready messages using journal monotonic timestamps. The relay logged root confirmation after the fresh master login. Weather started afterward; the operator confirmed normal audible speech. This is one measured recovery, not a latency guarantee under all network conditions. It improves recovery latency, not the unresolved RF fault itself.

Deploy `proxy.py` and `modem_maintenance.py` as a consistent reviewed pair after a private backup. Install while weather is idle, retain its lock/order protection, and wait for the relay control socket before the live check. No radio/network identity, calibration, voice-bank or timer-frequency changes are needed. To revert, restore the backed-up pair while idle; partial upgrades retain the conservative heartbeat fallback.
