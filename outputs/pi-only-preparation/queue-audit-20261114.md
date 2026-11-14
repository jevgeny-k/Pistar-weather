# Queue audit and recurrent RF failure

The operator reported progressively shortened announcements, missing parts, complete silence and repeater timeout. These symptoms recurred with static subscriptions removed and with a reduced RF output setting. The cause remains unresolved.

A bounded 140-second UART capture covered a full repeated bulletin before host recovery. The operator confirmed that this repeat produced no audible parts and that PTT timed out. All 348, 210, 180 and 378 generated voice bursts were found in order in successful UART submissions. The comparison checked the 216 voice bits per burst and excluded the central 48 signalling bits.

The trace contained 536 modem status replies, zero negative acknowledgements and zero overflow/lockout flags. Each part ended with 51 identical terminal frames. Reported slot-one free capacity ranged from 5 to 28. Both slots returned to 28 free positions and the TX flag cleared between parts. This capture demonstrates complete UART submission during a confirmed RF failure. It does not measure physical modulation or the occupancy of the shared output bit buffer inside the modem.

The firmware checks available slot-FIFO space before processing a pending abort reset. That ordering remains a potential edge case. The observed non-full slot queues do not establish it as the cause of this incident.

A protected host restart restored four audible parts. About 50 minutes later, the operator heard only two parts while the host logged four complete calls. Another recovery audition produced six receiver activations while the host logged four calls. Full speech reception was not confirmed for that audition. Recovery cannot be inferred from master login or software delivery alone.

Private UART captures, generated packet files and host logs were archived locally with verified SHA-256 checksums. Capture files remain bounded in RAM on the hotspot. The existing one-shot recorder was rearmed after evidence preservation. Raw evidence, live configurations and operator identifiers are excluded from this repository.
