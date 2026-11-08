# Recorded BrandMeister static groups

Device <OWNER_DMR_ID> (OPERATOR_CALLSIGN), master 2441: official API v2 updates were read back as TG <TG_B> and <TG_A>, both TS2. TG 91 was removed and TG <TG_A> was moved from TS1 to TS2. Private weather remains in TS1. This is a historical record; inspect current server state before changes.

The current relay lets TS2 traffic pass in both directions without canceling a TS1 bulletin. Actual TS1 traffic still takes priority. Three checks passed on the Pi, including UDP slot-isolation checks. Previous source: `/var/backups/pistar-weather/proxy-before-slot-isolation.py`. Current source: repository-root `work/pistar-weather/proxy.py`. The laptop snapshot predates this fix.

The API key, when configured, is stored only on the Pi in `/etc/bmapi.key`, root-owned mode 0600. It is not in these archives or documents. Static subscriptions persist on BrandMeister. Do not modify server subscriptions as a side effect of installing weather software.

During an earlier simultaneous test, TS2 group traffic did not interrupt TS1 weather and MMDVMHost reported no private-call packet loss. This does not guarantee later RF reception.
