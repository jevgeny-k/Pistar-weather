"""Do not confuse authentication completion with the first heartbeat reply."""
import os
import socket
import struct
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import proxy
import modem_maintenance
from modem_maintenance import wait_ready
from test_slot_guard import relay_pair
from test_weather_priority import control

class Credentials:
    def __init__(self,uid):self.uid=uid
    def getsockopt(self,*args):return struct.pack('3i',1,self.uid,1)

class FastReadinessTests(unittest.TestCase):
    def test_other_protocol_login_cannot_confirm_dmr_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'host.log';path.touch();watch=modem_maintenance.LoginWatch(lambda:path)
            with path.open('a') as stream:stream.write('YSF, Logged into the master successfully\n')
            self.assertFalse(watch.seen())
            with path.open('a') as stream:stream.write('DMR, Logged into the master successfully\n')
            self.assertTrue(watch.seen())

    def test_old_process_stops_before_the_fresh_login_cursor_is_created(self):
        events=[];watch=object()
        def command(*args):events.append(args)
        def login():events.append('watch');return watch
        with patch.object(modem_maintenance,'command',command),patch.object(modem_maintenance,'LoginWatch',login):
            self.assertIs(modem_maintenance.restart_host(),watch)
        self.assertEqual(events,[('systemctl','stop','mmdvmhost.service'),'watch',('systemctl','start','mmdvmhost.service')])

    def test_nonroot_peer_is_rejected(self):
        with self.assertRaises(PermissionError):proxy.require_root_peer(Credentials(12345))
        proxy.require_root_peer(Credentials(0))

    @unittest.skipUnless(getattr(os,'geteuid',lambda:1)()==0,'Root Unix peer integration')
    def test_actual_root_peer_can_confirm_matching_host(self):
        with relay_pair(False) as (relay,master,host,upaddr,peer):
            relay.job=None;relay.connected=False
            result=control(relay,{'op':'confirm_host_login','host':list(relay.host)})
            self.assertTrue(result['ok']);self.assertTrue(relay.connected)

    def test_changed_host_is_rejected_without_updating_readiness(self):
        with relay_pair(False) as (relay,master,host,upaddr,peer),patch.object(proxy,'require_root_peer'):
            relay.job=None;relay.connected=False
            result=control(relay,{'op':'confirm_host_login','host':['127.0.0.1',1]})
            self.assertFalse(result['ok']);self.assertFalse(relay.connected)

    def test_unprivileged_confirmation_cannot_change_state(self):
        with relay_pair(False) as (relay,master,host,upaddr,peer),patch.object(proxy,'require_root_peer',side_effect=PermissionError('root required')):
            relay.job=None;relay.connected=False
            self.assertFalse(control(relay,{'op':'confirm_host_login','host':list(relay.host)})['ok'])
            self.assertFalse(relay.connected)

    def test_confirmation_waits_for_fresh_host_login(self):
        clock=[0.];calls=[]
        class Login:
            def seen(self):return clock[0]>=2
        def sleep(seconds):clock[0]+=seconds
        def confirm(host):calls.append((clock[0],host));return True
        wait_ready(Login(),status=lambda:{'connected':False,'host':['127.0.0.1',1]},sleep=sleep,clock=lambda:clock[0],confirm=confirm,timeout=10)
        self.assertEqual(calls,[(2.,['127.0.0.1',1])])

    def test_old_login_never_authorizes_confirmation(self):
        clock=[0.];calls=[]
        class Login:
            def seen(self):return False
        def sleep(seconds):clock[0]+=seconds
        with self.assertRaisesRegex(RuntimeError,'fresh master login'):
            wait_ready(Login(),status=lambda:{'connected':False,'host':['127.0.0.1',1]},sleep=sleep,clock=lambda:clock[0],confirm=lambda host:calls.append(host),timeout=4)
        self.assertFalse(calls)

    def test_older_relay_can_fall_back_to_first_pong(self):
        clock=[0.]
        class Login:
            def seen(self):return True
        def sleep(seconds):clock[0]+=seconds
        wait_ready(Login(),status=lambda:{'connected':clock[0]>=4,'host':['127.0.0.1',1]},sleep=sleep,clock=lambda:clock[0],confirm=lambda host:False,timeout=10)
        self.assertEqual(clock[0],4.)

if __name__=='__main__':unittest.main()
