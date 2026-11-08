# Intermittent loss of audible reception

At about 00:47 Europe/Riga on November 8, 2026, the user reported lost audio again. The 00:45 bulletin had been assembled, encoded, and delivered completely to MMDVMHost. These events do not prove a healthy RF signal.

Recorded measurements: SoC 50.6-51.6 C, PMIC 43.7 C, `get_throttled=0x0`, load 0.02/0.04/0.00, 767 MB RAM and 26 GB SD space available. No SD/EXT4 or undervoltage errors were detected. MMDVM_HS_Dual_Hat chip temperatures were unavailable through the inspected interfaces. A 0.8700 V core reading at about 600 MHz describes the SoC, not the 5 V supply.

Only MMDVMHost was restarted, without a GPIO modem reset. After the master connected, the first part of the last bulletin (342 packets) was replayed, and the user confirmed audible reception.

Restarting MMDVMHost and reinitializing the modem was sufficient for this episode. This does not isolate the failure to MMDVMHost: startup also reconfigures the modem. The root cause remains unknown. Scheduled preventive restarts were not added because they can interrupt ordinary traffic. Software startup checks cannot guarantee RF reception.
