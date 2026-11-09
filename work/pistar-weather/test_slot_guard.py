"""Exercise opt-in cross-slot priority with real UDP and a controlled clock."""
from contextlib import contextmanager
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
import proxy

RADIO_ID=1  # Synthetic identity; no configured master or RF is used.
def packet(flags):
    return b'DMRD\x00'+RADIO_ID.to_bytes(3,'big')*2+RADIO_ID.to_bytes(4,'big')+bytes([flags])+b'TEST'+bytes(35)

@contextmanager
def relay_pair(enabled=True, weather_priority=False):
    with tempfile.TemporaryDirectory() as folder, patch.object(proxy,'RADIO_ID',RADIO_ID):
        master=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);master.bind(('127.0.0.1',0));master.settimeout(.1)
        host=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);host.bind(('127.0.0.1',0));host.settimeout(.1)
        relay=proxy.Relay(master.getsockname(),('127.0.0.1',0),Path(folder)/'control.sock',folder,idle=0,serialize_slots=enabled,weather_priority=weather_priority)
        client,peer=socket.socketpair();peer.settimeout(.1)
        try:
            host.sendto(b'RPTLtest',relay.down.getsockname());relay.step(0)
            _,upaddr=master.recvfrom(1024)
            master.sendto(b'MSTPONGtest',upaddr);relay.step(0);host.recv(1024)
            relay.job=dict(client=client,packets=[packet(0x61),packet(0x01),packet(0x62)],index=0,due=0,deadline=1000)
            yield relay,master,host,upaddr,peer
        finally:
            relay.close();master.close();host.close();client.close();peer.close()

class SlotGuardTests(unittest.TestCase):
    def test_waits_twelve_seconds_after_ts2_before_starting(self):
        clock=[100.0]
        with patch.object(proxy.time,'monotonic',lambda:clock[0]),relay_pair() as (relay,master,host,upaddr,peer):
            master.sendto(packet(0xa1),upaddr);relay.step(0)
            self.assertEqual(host.recv(1024),packet(0xa1));self.assertEqual(relay.job['index'],0)
            clock[0]=111.99;relay.step(0);self.assertEqual(relay.job['index'],0)
            clock[0]=112.;relay.step(0)
            self.assertEqual(host.recv(1024),packet(0x61));self.assertEqual(relay.job['index'],1)
            self.assertEqual(relay.job['due'],112.06)
            with self.assertRaises(socket.timeout):master.recv(1024)

    def test_new_network_ts2_ends_weather_then_forwards_the_call(self):
        with relay_pair() as (relay,master,host,upaddr,peer):
            relay.job['index']=1;relay.job['due']=float('inf');relay.job['deadline']=float('inf')
            master.sendto(packet(0xa1),upaddr);relay.step(0)
            self.assertEqual(host.recv(1024),packet(0x62));self.assertEqual(host.recv(1024),packet(0xa1))
            self.assertIsNone(relay.job);self.assertFalse(json.loads(peer.recv(4096))['ok'])
            with self.assertRaises(socket.timeout):master.recv(1024)

    def test_new_radio_ts2_still_goes_upstream_and_ends_weather(self):
        with relay_pair() as (relay,master,host,upaddr,peer):
            relay.job['index']=1;relay.job['due']=float('inf');relay.job['deadline']=float('inf')
            host.sendto(packet(0xa1),relay.down.getsockname());relay.step(0)
            self.assertEqual(master.recv(1024),packet(0xa1));self.assertEqual(host.recv(1024),packet(0x62))
            self.assertIsNone(relay.job);self.assertFalse(json.loads(peer.recv(4096))['ok'])

    def test_busy_wait_expires_instead_of_leaking_a_queued_job(self):
        with patch.object(proxy.time,'monotonic',lambda:100.0),relay_pair() as (relay,master,host,upaddr,peer):
            relay.job['deadline']=99.;relay.step(0)
            self.assertIsNone(relay.job)
            self.assertIn('Timed out',json.loads(peer.recv(4096))['message'])

    def test_default_mode_keeps_independent_ts2(self):
        with relay_pair(False) as (relay,master,host,upaddr,peer):
            relay.job['index']=1;relay.job['due']=float('inf');relay.job['deadline']=float('inf')
            master.sendto(packet(0xa1),upaddr);relay.step(0)
            self.assertEqual(host.recv(1024),packet(0xa1));self.assertIsNotNone(relay.job)
            self.assertEqual(relay.idle,0)

if __name__=='__main__':unittest.main()
