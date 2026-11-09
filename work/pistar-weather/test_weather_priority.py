"""Whole-bulletin ownership, complete-call suppression and bounded recovery."""
import json
import selectors
import socket
import unittest
from unittest.mock import patch
import proxy
from test_slot_guard import relay_pair,packet

def control(relay,message):
    client,peer=socket.socketpair()
    try:
        relay.sel.register(client,selectors.EVENT_READ,'request')
        peer.sendall(json.dumps(message).encode());relay.control_request(client)
        return json.loads(peer.recv(4096))
    finally:client.close();peer.close()

def other_stream(flags=0xa1):
    data=bytearray(packet(flags));data[16:20]=b'NEW1';return bytes(data)

class WeatherPriorityTests(unittest.TestCase):
    def test_existing_call_drains_new_calls_wait_and_control_packets_pass(self):
        clock=[100.]
        with patch.object(proxy.time,'monotonic',lambda:clock[0]),relay_pair(False,True) as (relay,master,host,upaddr,peer):
            relay.job=None
            master.sendto(packet(0xa1),upaddr);relay.step(0);self.assertEqual(host.recv(1024),packet(0xa1))
            token=control(relay,{'op':'begin_bulletin'})['token']
            master.sendto(other_stream(),upaddr);relay.step(0)
            with self.assertRaises(socket.timeout):host.recv(1024)
            master.sendto(b'MSTPONGtest',upaddr);relay.step(0);self.assertEqual(host.recv(1024),b'MSTPONGtest')
            clock[0]=101.;master.sendto(packet(0xa2),upaddr);relay.step(0);self.assertEqual(host.recv(1024),packet(0xa2))
            self.assertEqual(relay.last_voice,101.)
            relay.job=dict(client=peer,packets=[packet(0x61),packet(0x62)],index=0,due=0,deadline=1000)
            try:
                clock[0]=112.99;relay.step(0);self.assertEqual(relay.job['index'],0)
                clock[0]=113.;relay.step(0);self.assertEqual(host.recv(1024),packet(0x61))
                self.assertFalse(relay.priority_draining)
            finally:relay.job=None
            self.assertTrue(control(relay,{'op':'end_bulletin','token':token})['ok'])

    def test_new_network_call_does_not_interrupt_weather(self):
        with relay_pair(False,True) as (relay,master,host,upaddr,peer):
            relay.job['index']=1;relay.job['due']=float('inf');relay.job['deadline']=float('inf')
            control(relay,{'op':'begin_bulletin'})
            master.sendto(other_stream(),upaddr);relay.step(0)
            self.assertIsNotNone(relay.job);self.assertEqual(relay.job['index'],1)
            with self.assertRaises(socket.timeout):host.recv(1024)
            with self.assertRaises(socket.timeout):master.recv(1024)

    def test_skipped_call_tail_stays_silent_after_release(self):
        clock=[100.]
        with patch.object(proxy.time,'monotonic',lambda:clock[0]),relay_pair(False,True) as (relay,master,host,upaddr,peer):
            relay.job=None;token=control(relay,{'op':'begin_bulletin'})['token']
            master.sendto(other_stream(),upaddr);relay.step(0)
            control(relay,{'op':'end_bulletin','token':token})
            clock[0]=113.;relay.step(0);self.assertIsNone(relay.reservation)
            master.sendto(other_stream(0x81),upaddr);relay.step(0)
            with self.assertRaises(socket.timeout):host.recv(1024)
            master.sendto(other_stream(0xa2),upaddr);relay.step(0);self.assertFalse(relay.suppressed)
            master.sendto(packet(0xa1),upaddr);relay.step(0);self.assertEqual(host.recv(1024),packet(0xa1))

    def test_wrong_token_cannot_end_a_bulletin(self):
        with relay_pair(False,True) as (relay,master,host,upaddr,peer):
            relay.job=None;control(relay,{'op':'begin_bulletin'})
            self.assertFalse(control(relay,{'op':'end_bulletin','token':'wrong'})['ok'])
            self.assertIsNotNone(relay.reservation)

    def test_reservation_survives_the_gap_between_weather_parts(self):
        with relay_pair(False,True) as (relay,master,host,upaddr,peer):
            control(relay,{'op':'begin_bulletin'})
            relay.finish(True,'Part complete')
            self.assertTrue(json.loads(peer.recv(4096))['ok'])
            self.assertIsNotNone(relay.reservation)
            master.sendto(other_stream(),upaddr);relay.step(0)
            with self.assertRaises(socket.timeout):host.recv(1024)

    def test_disabled_mode_rejects_reservation(self):
        with relay_pair(False,False) as (relay,master,host,upaddr,peer):
            self.assertFalse(control(relay,{'op':'begin_bulletin'})['ok'])
            self.assertIsNone(relay.reservation)

    def test_crashed_sender_lease_expires_without_a_restart(self):
        clock=[100.]
        with patch.object(proxy.time,'monotonic',lambda:clock[0]),relay_pair(False,True) as (relay,master,host,upaddr,peer):
            relay.job=None;control(relay,{'op':'begin_bulletin'})
            clock[0]=941.;relay.step(0);self.assertIsNone(relay.reservation)
            master.sendto(packet(0xa1),upaddr);relay.step(0);self.assertEqual(host.recv(1024),packet(0xa1))

    def test_stream_tracking_is_bounded(self):
        with relay_pair(False,True) as (relay,master,host,upaddr,peer):
            relay.job=None;control(relay,{'op':'begin_bulletin'})
            for number in range(600):
                data=bytearray(packet(0xa1));data[16:20]=number.to_bytes(4,'big')
                self.assertFalse(relay.forward_network_voice(bytes(data)))
            self.assertEqual(len(relay.suppressed),256)

if __name__=='__main__':unittest.main()
