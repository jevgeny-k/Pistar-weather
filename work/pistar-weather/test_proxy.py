"""Real UDP loopback integration test: local speech must never reach upstream."""
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from proxy import Relay, validate_packets
RADIO_ID = 1  # Synthetic test identity.


def packet(flags=0x61):
    return b'DMRD\x00'+RADIO_ID.to_bytes(3,'big')*2+RADIO_ID.to_bytes(4,'big')+bytes([flags])+b'TEST'+bytes(35)


@patch('proxy.RADIO_ID', RADIO_ID)
class Isolation(unittest.TestCase):
    def test_private_validation(self):
        validate_packets(packet()+packet(0x62))
        for flags in [0x21,0xe1]:
            with self.assertRaises(ValueError): validate_packets(packet(flags)+packet(0x62))
        bad=bytearray(packet()); bad[8:11]=(91).to_bytes(3,'big')
        with self.assertRaises(ValueError): validate_packets(bytes(bad)+packet(0x62))

    def test_relay_isolation_and_normal_forwarding(self):
        with tempfile.TemporaryDirectory() as folder:
            master=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); master.bind(('127.0.0.1',0)); master.settimeout(2)
            host=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); host.bind(('127.0.0.1',0)); host.settimeout(2)
            relay=Relay(master.getsockname(),('127.0.0.1',0),Path(folder)/'control.sock',folder,idle=.05)
            stop=threading.Event()
            def run():
                while not stop.is_set(): relay.step(.005)
            t=threading.Thread(target=run); t.start()
            try:
                host.sendto(b'RPTLtest',relay.down.getsockname())
                data,upaddr=master.recvfrom(1024); self.assertEqual(data,b'RPTLtest')
                master.sendto(b'MSTPONGtest',upaddr); self.assertEqual(host.recv(1024),b'MSTPONGtest')
                raw=packet()+packet(0x62); p=Path(folder)/'test.dmr55'; p.write_bytes(raw)
                control=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); control.settimeout(2)
                control.connect(str(Path(folder)/'control.sock'))
                control.sendall(json.dumps({'op':'play','file':str(p)}).encode())
                self.assertEqual(host.recv(1024),packet())
                self.assertEqual(host.recv(1024),packet(0x62))
                self.assertTrue(json.loads(control.recv(1024))['ok']); control.close()
                master.settimeout(.15)
                with self.assertRaises(socket.timeout): master.recv(1024)
                # RF traffic still travels to the real master after the announcement.
                host.sendto(b'RPTPINGtest',relay.down.getsockname())
                self.assertEqual(master.recv(1024),b'RPTPINGtest')
            finally:
                stop.set(); t.join(); relay.close(); host.close(); master.close()


if __name__=='__main__': unittest.main()
