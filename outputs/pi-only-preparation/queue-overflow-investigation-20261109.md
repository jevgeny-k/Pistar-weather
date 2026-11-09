# Queue overflow and recurrent silent RF: November 9

## Observed recurrence

The operator again confirmed inaudible weather and PTT repeater timeout after the weather-priority policy had been running for approximately five hours. The host had reported complete local delivery of the report. A host-only restart later restored both audible weather and working PTT, confirmed by the operator. The RF fault remains unresolved.

The daily log first recorded TS2 queue overflow at20:23:27 UTC, between weather bulletins. There were319 such messages before recovery. Preceding events included a network watchdog expiry, late entry and a long network call. Further queue overflows also occurred after the host restart, before the operator confirmed working reception. The error is a useful diagnostic trigger, but is not a reliable detector of silent RF by itself.

## What the source and captures establish

- In the installed host source, both `CDMRSlot::writeQueueRF()` and `writeQueueNet()` use the same `overflow in the DMR slot RF queue` message. This is the5000-byte host playout queue, not a direct statement that the modem's UART FIFO overflowed. See [installed DMRSlot.cpp](https://github.com/g4klx/MMDVM-Host/blob/218a017/DMRSlot.cpp).
- A55-second UART snapshot in the confirmed bad state contained210 status replies,889 TS2 frame writes, DMR mode and a TX flag throughout. TS1 free space stayed28; TS2 free space ranged5..28 and was usually16..17. No overflow/lockout status flags were reported. This excludes a persistent completely blocked UART/FIFO in that snapshot; it does not establish RF modulation quality or exclude an earlier transient.
- A separate60-second packet-metadata capture in the bad state saw993 incoming TS2 packets, mean interval60.479ms, maximum482.682ms, one sequence gap, no duplicates or reorder, and a maximum19 packets in a one-second bin. For992 matched network-to-host packets, median relay latency was0.238ms and maximum0.617ms. The capture boundary contains one additional incoming packet. There was no sustained network flood or relay stall in this observed minute. The onset of the earlier overflow was not captured.
- CPU temperature was53.5C, power/throttling flags were zero, system memory was available and Wi-Fi power save was already off. These checks do not measure the HAT's own temperature, supply quality or RF output.
- Host elapsed-time accounting uses `CLOCK_MONOTONIC`; the inspected [StopWatch.cpp](https://github.com/g4klx/MMDVM-Host/blob/218a017/StopWatch.cpp) does not support blaming a wall-clock adjustment for this capture without further evidence.

A separate recovery audition failed the codec guard before RF. Repeatable SoX preparation and its offline verification are documented in [codec-repeatability.md](codec-repeatability.md); that change does not explain simultaneous PTT failure.

## Bounded onset recorder

The optional `queue_diagnostics.py` watcher records up to120 seconds of recent DMR timing metadata in RAM. It watches only new host queue-overflow messages after arming. On the first error, it freezes the recent window, records up to30 more seconds, and starts a short size-limited private UART trace. It then exits, retaining one snapshot. `SIGUSR1` can trigger the same capture manually when an operator reports silence without a new overflow.

UDP snapshots contain timing, interface/direction, ports, sequence, flags and stream identifiers. They contain no IP addresses, radio IDs, audio payload or authentication packets. The UART trace can contain coded voice and modem configuration, so the entire diagnostic directory is root-only and must remain private. Nothing is uploaded automatically.

Limits:12000 pre-trigger events,4000 post-trigger events, a compressed snapshot no larger than2MiB, UART file no larger than512KiB and trace duration about30 seconds. Files are under `/run/pistar-weather-diagnostics/`, directory0700 and files0600. Output does not grow across repeated events: the process stops after the first capture and refuses to overwrite an existing snapshot. The existing volatile-journal limit remains in force. A reboot clears the RAM evidence and arms the enabled watcher again.

The installed recorder passed six Linux tests for privacy filtering, short-frame rejection, time/count bounds, historical-error exclusion, log rotation and snapshot bounds. A real manual smoke capture completed successfully:1967 pre-events,500 post-events, a44233-byte compressed snapshot and a122KiB UART trace. Its private archive was copied to the laptop and SHA-256 verified; the watcher was then cleared and rearmed for a real new overflow. The final idle-window expiry correction also passed all six tests.

## Optional installation and rearming

The transfer builder places these optional files under `diagnostics/`, separate from normal runtime/systemd deployment. Install the script at `/opt/pistar-weather/queue_diagnostics.py` and the unit under `/etc/systemd/system/` only when diagnostics are authorized. It requires Linux packet sockets, root packet-capture/ptrace permissions and `strace`. It does not transmit, restart the host, edit radio settings or attempt automatic RF recovery.

Read `state.json`: `armed`, `capturing` or `complete`. After a completed capture, preserve and verify the private snapshot/UART files before removing only those known evidence files and rearming the service. Do not clear evidence during capture. Stop/disable the optional service to remove the watcher. Keep root filesystem write access limited to installation/maintenance.

## Remaining uncertainty

The first overflow's packet/queue history is still missing. The new recorder is intended to obtain it. A host restart restores reception but reinitializes modem state too, so it does not isolate the host from firmware. RF timing/modulation failure cannot be ruled in or out by these software captures alone. No firmware flash, speculative modem calibration or periodic restart workaround was installed.
