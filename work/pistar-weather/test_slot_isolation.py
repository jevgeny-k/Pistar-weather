"""Real UDP: TS2 forwards while TS1 bulletin survives; TS1 still interrupts."""
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from proxy import Relay
RADIO_ID = 1  # Synthetic test identity.

def packet(flags):
    return b'DMRD\x00'+RADIO_ID.to_bytes(3,'big')*2+RADIO_ID.to_bytes(4,'big')+bytes([flags])+b'TEST'+bytes(35)

@patch('proxy.RADIO_ID', RADIO_ID)
class Slots(unittest.TestCase):
    def test_other_slot_does_not_interrupt_either_direction(self):
        with tempfile.TemporaryDirectory() as folder:
            master=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);master.bind(('127.0.0.1',0));master.settimeout(1)
            host=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);host.bind(('127.0.0.1',0));host.settimeout(1)
            relay=Relay(master.getsockname(),('127.0.0.1',0),Path(folder)/'control.sock',folder,idle=0)
            peers=[]
            try:
                host.sendto(b'RPTLtest',relay.down.getsockname());relay.step(.05)
                _,upaddr=master.recvfrom(1024)
                master.sendto(b'MSTPONGtest',upaddr);relay.step(.05);host.recv(1024)
                # Hold an active local announcement, so incoming packets really
                # exercise the cancellation path without relying on timing.
                client,peer=socket.socketpair();peers.extend([client,peer])
                relay.job=dict(client=client,packets=[packet(0x61),packet(0x62)],index=1,due=float('inf'),deadline=float('inf'))
                master.sendto(packet(0xa1),upaddr);relay.step(.05)
                self.assertEqual(host.recv(1024),packet(0xa1));self.assertIsNotNone(relay.job)
                host.sendto(packet(0xa1),relay.down.getsockname());relay.step(.05)
                self.assertEqual(master.recv(1024),packet(0xa1));self.assertIsNotNone(relay.job)
                self.assertEqual(relay.last_voice,0)
                master.sendto(packet(0x21),upaddr);relay.step(.05)
                self.assertEqual(host.recv(1024),packet(0x62))
                self.assertEqual(host.recv(1024),packet(0x21))
                self.assertIsNone(relay.job)
                self.assertFalse(json.loads(peer.recv(4096))['ok'])
            finally:
                relay.close();master.close();host.close()
                for p in peers:p.close()

if __name__=='__main__':unittest.main()
