# Historical TXHang=10 trial

At about 00:58 Europe/Riga on November 8, 2026, the user reported audio disappearing after two or three cycles following an MMDVMHost restart. This is a user observation, not a confirmed failure counter.

A potentially similar firmware report was recorded at https://github.com/juribeparada/MMDVM_HS/issues/170 . It described dual ADF7021, 14.7456 MHz, firmware 1.6.1, clean network logs, and recovery after restarting MMDVMHost. Its author reported fewer, but not zero, failures with a longer TXHang. Similarity is not proof of the same cause or a verified fix.

The reversible trial changed only `[DMR] TXHang` in `/etc/mmdvmhost` from 4 to 10. With five-second inter-part gaps this may reduce transmitter cycling within a bulletin. Evaluate actual audible reception across at least four cycles; successful logs are insufficient evidence.

Previous configuration: root-only `/var/backups/pistar-weather/mmdvmhost-before-txhang10-20261107-225755`. MMDVMHost was restarted and root restored read-only. Firmware was unchanged and periodic restarts were not added. A targeted rollback should restore only `[DMR] TXHang=4` and restart MMDVMHost, rather than overwrite newer settings with a whole older configuration.
