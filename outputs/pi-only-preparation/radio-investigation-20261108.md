# Intermittent silent DMR transmission: November 8 investigation

Audible reception sometimes stops after two or three quarter-hour bulletins. The radio also reports repeater timeout on PTT. Restarting MMDVMHost has restored reception, but software delivery logs alone cannot identify this RF state. The fault remains unresolved.

## Confirmed pacing defect

The relay previously scheduled each packet at actual send time plus 60 ms and polled on a fixed interval. Scheduling lateness accumulated during other-slot traffic. A simulated 240-frame run accumulated 1.912 seconds of drift before the fix. Deadlines now stay on the original 60 ms timeline; selector waiting follows the next deadline. The first packet anchors the timeline only after channel idle, avoiding an initial burst.

A captured 348-packet fragment improved from a mean interval of 65.636 ms and 1.956 seconds total drift to 60.001 ms and 0.356 ms total drift. The corrected test was heard on the radio. This proves the timing correction, not a permanent fix for the silent-modem state.

Bad and working instances of one fragment produced identical 402-frame UART payloads. During the bad state the modem continued status replies, reported TX, and drained its FIFO without reported overflow or lockout. These are internal indicators, not measurements of RF quality. Temperatures and power flags did not indicate overheating or undervoltage in the inspected sample.

## Bounded TS2 isolation trial

With explicit operator agreement, network TS2 was disabled for one hour while local TS1 weather continued. All four scheduled reports were confirmed audible. Automatic restoration completed and both network slots were enabled again. Static subscriptions were preserved. The baseline restart and pacing change confound this result; it suggests further investigation of TS2 interaction rather than proving its cause.

`work/pistar-weather/slot2_trial.py` is a root-only diagnostic helper, not an installed recurring workaround. It backs up the private configuration on the target, arms persistent automatic restoration before changing only network Slot2, waits for bulletins to finish, and retries a failed restore. Its state and backups must remain private. Do not run another isolation trial without operator agreement.

## Upstream evidence and limits

The installed MMDVMHost revision was `218a017`; modem firmware was MMDVM_HS Dual Hat 1.6.1, revision `7e16099`, dual ADF7021 / 14.7456 MHz. [MMDVM_HS issue 170](https://github.com/juribeparada/MMDVM_HS/issues/170) describes a similar silent TX / PTT-timeout symptom and recovery after host restart. It had no confirmed fix at inspection. Similar symptoms do not prove the same cause. TXHang=10 remains an inconclusive trial, not a deployment requirement.

No firmware was flashed, periodic restart workaround installed, or RF recovery watchdog claimed. Further diagnosis needs receiver confirmation or independent RF measurement. A later report with no TX lights was separately explained by an HTTP 503 weather-fetch failure; HTTP retries and explicit cached replay address that case.
