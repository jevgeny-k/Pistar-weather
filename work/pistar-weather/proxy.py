#!/usr/bin/env python3
"""Transparent Homebrew UDP relay; private announcements go ONLY to MMDVMHost.

No codec or weather fetch runs in the forwarding process. An AF_UNIX control
socket is accessible only to the service owner. Existing BM credentials remain
in MMDVMHost; the relay never records authentication packets.
"""
import argparse
import json
import logging
import os
from pathlib import Path
import selectors
import secrets
import socket
import time

from site_settings import configured_radio_id, load_site, require_radio_id

RADIO_ID = configured_radio_id()
LOG = logging.getLogger('pistar-weather')


def validate_packets(raw):
    require_radio_id(RADIO_ID)
    if not raw or len(raw) % 55 or len(raw) > 55 * 1000:
        raise ValueError('Invalid packet file size (maximum 60 seconds)')
    packets = [raw[i:i+55] for i in range(0, len(raw), 55)]
    streams = set()
    for p in packets:
        if p[:4] != b'DMRD' or int.from_bytes(p[5:8], 'big') != RADIO_ID:
            raise ValueError('Unexpected source ID')
        if int.from_bytes(p[8:11], 'big') != RADIO_ID or not p[15] & 0x40:
            raise ValueError('Only private calls to the owner are allowed')
        if p[15] & 0x80:
            raise ValueError('Announcement must use slot 1')
        streams.add(p[16:20])
    if len(streams) != 1 or packets[0][15] != 0x61 or packets[-1][15] != 0x62:
        raise ValueError('Missing LC header or terminator')
    return packets


class Relay:
    def __init__(self, upstream, listen, control, state_dir, idle=5.0, serialize_slots=False, weather_priority=False):
        self.sel = selectors.DefaultSelector()
        self.upstream = upstream
        self.control_path = Path(control)
        self.state_dir = Path(state_dir).resolve()
        self.weather_priority = weather_priority
        self.reservation = None
        self.priority_draining = set()
        self.network_active = {}
        self.suppressed = {}
        self.serialize_slots = serialize_slots
        # Experimental guard: let TXHang=10 expire before a weather part.
        self.idle = max(idle, 12.0) if (serialize_slots or weather_priority) else idle
        self.host = None
        self.last_voice = 0.0
        self.connected = False
        self.job = None
        self.running = True
        self.down = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.down.bind(listen)
        self.up = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.up.connect(upstream)  # kernel accepts packets only from this master
        self.control = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if self.control_path.exists(): self.control_path.unlink()
        self.control.bind(str(control))
        os.chmod(control, 0o600)
        self.control.listen(4)
        for sock, tag in [(self.down, 'down'), (self.up, 'up'), (self.control, 'accept')]:
            sock.setblocking(False)
            self.sel.register(sock, selectors.EVENT_READ, tag)

    def reply(self, client, data):
        try: client.sendall((json.dumps(data)+'\n').encode())
        except OSError: pass
        client.close()

    def finish(self, ok, reason):
        job, self.job = self.job, None
        if job:
            LOG.info('%s: %s', 'Completed' if ok else 'Stopped', reason)
            self.reply(job['client'], {'ok': ok, 'message': reason, 'sent': job['index']})

    def expire_priority(self, now):
        if self.reservation and now >= self.reservation['until']:
            if not self.reservation.get('released') and self.job:
                self.finish(False, 'Weather priority lease expired')
            self.reservation = None
            self.priority_draining.clear()
            LOG.info('Weather priority released')
        for mapping, ttl in ((self.network_active, 2.0), (self.suppressed, 180.0)):
            for key, stamp in list(mapping.items()):
                if now-stamp > ttl: del mapping[key]

    @staticmethod
    def remember(mapping, key, now):
        mapping[key] = now
        if len(mapping) > 256: del mapping[min(mapping, key=mapping.get)]

    def forward_network_voice(self, data):
        if len(data) != 55 or not data.startswith(b'DMRD'): return True
        now = time.monotonic()
        key = (data[15] & 0x80, data[5:11], data[16:20])
        terminal = data[15] & 0x20 and data[15] & 0x0f == 2
        # Once a call is skipped, never resume its tail after the bulletin.
        blocked = key in self.suppressed or bool(self.reservation and key not in self.priority_draining)
        if blocked:
            if terminal: self.suppressed.pop(key, None)
            else: self.remember(self.suppressed, key, now)
            return False
        if terminal:
            self.network_active.pop(key, None)
            self.priority_draining.discard(key)
        else: self.remember(self.network_active, key, now)
        return True

    def voice_activity(self):
        self.last_voice = time.monotonic()
        if self.job and self.job['index'] and not self.reservation:
            # Yield to real traffic. Terminator is local downlink only.
            self.down.sendto(self.job['packets'][-1], self.host)
            self.finish(False, 'Real radio/network traffic took priority')

    def control_request(self, client):
        self.sel.unregister(client)
        try:
            request = json.loads(client.recv(4096))
            self.expire_priority(time.monotonic())
            if request.get('op') == 'begin_bulletin':
                if not self.weather_priority: raise ValueError('Weather priority is disabled')
                if self.reservation and not self.reservation.get('released'): raise ValueError('Bulletin already reserved')
                token = secrets.token_hex(16)
                self.priority_draining = set(self.network_active) if not self.reservation else set()
                self.reservation = dict(token=token, until=time.monotonic()+840, released=False)
                LOG.info('Weather priority reserved; draining %d existing calls', len(self.priority_draining))
                self.reply(client, {'ok': True, 'token': token}); return
            if request.get('op') == 'end_bulletin':
                if not self.reservation or request.get('token') != self.reservation['token']: raise ValueError('Invalid reservation token')
                self.reservation['released'] = True
                self.reservation['until'] = time.monotonic()+12
                self.priority_draining.clear()
                self.reply(client, {'ok': True}); return
            if request.get('op') == 'status':
                self.reply(client, {'ok': True, 'connected': self.connected,
                    'host': self.host, 'busy': bool(self.job),
                    'idle_seconds': round(time.monotonic()-self.last_voice, 1),
                    'serialize_slots': self.serialize_slots, 'guard_seconds': self.idle,
                    'weather_priority': self.weather_priority, 'priority_active': bool(self.reservation),
                    'suppressed_streams': len(self.suppressed)})
                return
            if request.get('op') != 'play': raise ValueError('Unknown command')
            if self.job: raise ValueError('Already playing/queued')
            if not self.host or not self.connected: raise ValueError('MMDVMHost not logged in')
            path = Path(request['file']).resolve()
            if path.parent != self.state_dir: raise ValueError('File outside runtime directory')
            packets = validate_packets(path.read_bytes())
            self.job = dict(client=client, packets=packets, index=0,
                            due=time.monotonic(), deadline=time.monotonic()+180)
            LOG.info('Queued private call to %s, %s frames', RADIO_ID, len(packets))
        except (ValueError, KeyError, OSError) as e:
            self.reply(client, {'ok': False, 'message': str(e)})

    def step(self, timeout=0.02):
        now = time.monotonic()
        self.expire_priority(now)
        if self.job and now > self.job['deadline']:
            self.finish(False, 'Timed out waiting for a free channel')
        job = self.job
        if job and self.host and self.connected:
            wake = job['due']
            if job['index'] == 0:
                wake = max(wake, self.last_voice + self.idle)
            # Wake at the audio deadline, even between network events.
            timeout = min(timeout, max(0.0, wake - now))
        for key, _ in self.sel.select(timeout):
            sock, tag = key.fileobj, key.data
            try:
                if tag == 'accept':
                    client, _ = sock.accept(); client.setblocking(False)
                    self.sel.register(client, selectors.EVENT_READ, 'request')
                elif tag == 'request': self.control_request(sock)
                elif tag == 'down':
                    data, addr = self.down.recvfrom(2048)
                    if addr[0] != '127.0.0.1': continue
                    if self.host != addr:
                        self.finish(False, 'MMDVMHost reconnected')
                        self.connected = False
                        self.host = addr
                    if len(data) >= 16 and data.startswith(b'DMRD') and (self.serialize_slots or self.weather_priority or not data[15] & 0x80): self.voice_activity()
                    # ONLY packets actually received from MMDVMHost go upstream.
                    self.up.send(data)
                elif tag == 'up':
                    data = self.up.recv(2048)
                    if not self.forward_network_voice(data): continue
                    if data.startswith((b'MSTNAK', b'MSTCL')): self.connected = False
                    if data.startswith(b'MSTPONG'): self.connected = True
                    if len(data) >= 16 and data.startswith(b'DMRD') and (self.serialize_slots or self.weather_priority or not data[15] & 0x80): self.voice_activity()
                    if self.host: self.down.sendto(data, self.host)
            except (BlockingIOError, ConnectionRefusedError): pass
        now = time.monotonic()
        job = self.job
        if job and self.host and self.connected and now >= job['due']:
            if job['index'] == 0:
                if now-self.last_voice < self.idle: return
                # Anchor the stream once the channel really becomes idle.
                job['due'] = now
                if self.reservation: self.priority_draining.clear()
            # Injection has no code path to self.up: never sent to BrandMeister.
            self.down.sendto(job['packets'][job['index']], self.host)
            job['index'] += 1
            # Keep the stream on its original 60 ms timeline; adding scheduler
            # lateness to every deadline makes each announcement progressively slow.
            job['due'] += 0.060
            if job['index'] == len(job['packets']):
                self.last_voice = now
                self.finish(True, 'Private call delivered to local MMDVMHost')

    def close(self):
        self.finish(False, 'Relay stopped')
        for key in list(self.sel.get_map().values()):
            try: key.fileobj.close()
            except OSError: pass
        self.sel.close()
        self.control_path.unlink(missing_ok=True)


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--upstream')
    a.add_argument('--port', type=int)
    a.add_argument('--listen-port', type=int, default=62039)
    a.add_argument('--state-dir', default='/run/pistar-weather')
    a.add_argument('--serialize-slots', action='store_true',
                   default=os.environ.get('PISTAR_WEATHER_SERIALIZE_SLOTS') == '1',
                   help='Experimental: weather yields to traffic on either slot')
    a.add_argument('--weather-priority', action='store_true',
                   default=os.environ.get('PISTAR_WEATHER_PRIORITY') == '1',
                   help='Reserve the whole weather bulletin over new network calls')
    args = a.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    require_radio_id(RADIO_ID)
    site = load_site(required=True)
    upstream_host = args.upstream or site.get('upstream_host')
    if not upstream_host:
        a.error('Set upstream_host in the private site configuration')
    upstream = (socket.gethostbyname(upstream_host), args.port or int(site.get('upstream_port', 62031)))
    relay = Relay(upstream, ('127.0.0.1', args.listen_port),
                  Path(args.state_dir)/'control.sock', args.state_dir,
                  serialize_slots=args.serialize_slots, weather_priority=args.weather_priority)
    LOG.info('Cross-slot weather guard: %s; quiet interval %.1fs', relay.serialize_slots, relay.idle)
    LOG.info('Relay ready; upstream %s; local private recipient %s', upstream, RADIO_ID)
    try:
        while True: relay.step()
    finally: relay.close()


if __name__ == '__main__': main()
