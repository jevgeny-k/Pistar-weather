# Operator-requested six-hour host restart

On November 10 the operator requested a six-hour modem restart workaround if fresh logs did not identify the recurring silent-RF fault. The latest weather report completed software delivery, the daily host log contained no errors or warnings, CPU temperature was 51.6 C and power/throttling flags were zero. A bounded private diagnostic snapshot was preserved before recovery. No new cause was established.

The workaround restarts **only MMDVMHost**, which also reinitializes the attached modem as in the previously successful manual recoveries. It does not reboot the Pi, power-cycle or flash the modem, change calibration, or detect missing RF audio. A fault can still recur between scheduled restarts; this is not a root-cause fix.

## Weather exclusion

The helper opens the existing autonomous weather lock without truncating or recreating it. It waits for that exclusive lock, a running weather PID, relay playback/reservation and an active diagnostic capture to finish. It holds the lock throughout restart and reconnection. If weather does not release the channel within 15 minutes, the helper fails without restarting it. There is no rapid retry loop.

The mandatory weather-service drop-in adds `After=pistar-modem-maintenance.service`. New timer-driven weather jobs therefore wait while maintenance is starting. A job waiting on this ordering has no PID, so the helper does not deadlock waiting for a weather job that has not begun. The file lock also covers ordinary standalone autonomous invocations. Legacy direct relay clients that do not use the autonomous lock are outside this scheduling guarantee.

After restart, the helper requires a **new** successful master-login entry in the host log and connected relay status. An old `connected` flag or old login line does not satisfy readiness. The lock remains held until reconnection succeeds or maintenance fails. Ordering alone does not require maintenance to succeed forever; a failed helper cannot permanently block future weather jobs.

## Timer and durability

The opt-in timer uses `OnActiveSec=6h` and `OnUnitInactiveSec=6h`, with one-minute scheduling accuracy. Subsequent intervals follow completion of the maintenance service, including any weather deferral. After reboot the enabled timer starts a new six-hour interval; it does not replay missed restarts. Existing Pi-Star daily maintenance remains unchanged and may independently restart the host.

Installation files are shipped under the optional `maintenance/` directory in a new transfer build. They are not part of default radio deployment. Enable this workaround only when explicitly requested by the operator.

Install the helper at `/opt/pistar-weather/modem_maintenance.py`, both maintenance units under `/etc/systemd/system/`, and the ordering file at `/etc/systemd/system/pistar-weather-autonomous.service.d/40-modem-maintenance-ordering.conf`. Back up the current weather unit/state privately, validate all units, reload systemd, and enable/start `pistar-modem-maintenance.timer`. An authorized immediate recovery can start the maintenance service manually. Keep the ordering drop-in installed while the timer is enabled.

To remove the workaround, stop/disable the maintenance timer, let an active maintenance operation finish, then remove only its dedicated weather ordering drop-in and reload systemd. Preserve the normal weather timer and newer unrelated settings. No periodic write-access remount is needed: runtime lock/log operations remain in RAM, and installation returns root to read-only mode. Logs are limited to a few journal messages per maintenance run under the existing volatile-journal cap.

## Validation and first live run

Seven Linux tests passed. They exercised a real held weather file lock, PID/reservation/capture deferral, lock retention through reconnection, timeout without restart, failure without retry storms, rejection of old login evidence and readiness failure without false success.

In the first live check, maintenance ran from 15:57:35 to 15:58:07 UTC. A weather start requested during that operation remained queued with no weather PID. Weather began only after the fresh login/readiness confirmation. The timer was enabled persistently and scheduled its next run for approximately 21:58 UTC (23:58 Riga), subject to weather deferral and timer accuracy. Receiver confirmation is recorded separately from software delivery.

When an extra manual recovery occurs before the first automatic tick, both startup and completion timer anchors still apply. The earlier `OnActiveSec` deadline can remain next even after `OnUnitInactiveSec` moves. Inspect `systemctl list-timers`; do not infer the next actual run solely from the last manual restart. The observed manual recovery at18:04 UTC left the first automatic deadline at22:00 UTC. The configured periodic interval was not shortened.

## Faster readiness update

The current relay/helper pair can confirm readiness immediately after a fresh DMR master login through a root-only local Unix request. This avoids the extra first-heartbeat wait; ordinary weather clients cannot invoke it. Update both source files consistently and retain the existing weather lock/order guards. The old host is stopped before the fresh log cursor is created, and a starting/unavailable relay socket causes deferral before any restart. See `faster-maintenance-readiness.md` for validation and the 22.4-second live measurement. The six-hour timer configuration is unchanged.
