import fcntl
from pathlib import Path
import tempfile
import unittest
from modem_maintenance import maintain,wait_ready,LoginWatch

class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.path=self.root/'lock';self.path.touch();self.now=0.;self.restarts=[]
    def tearDown(self):self.temp.cleanup()
    def sleep(self,seconds):self.now+=seconds
    def run_maintenance(self,**overrides):
        args=dict(lock_path=self.path,status=lambda:{'ok':True,'busy':False,'priority_active':False},weather=lambda:False,
                  diagnostics=lambda:False,restart=lambda:self.restarts.append(self.now),ready=lambda _:None,
                  sleep=self.sleep,clock=lambda:self.now,timeout=30,log=lambda *args,**kwargs:None)
        args.update(overrides);return maintain(**args)

    def test_existing_weather_lock_defers_restart(self):
        with self.path.open('r+') as held:
            fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
            def sleep(seconds):
                self.assertFalse(self.restarts);self.sleep(seconds)
                if self.now>=10:fcntl.flock(held,fcntl.LOCK_UN)
            self.run_maintenance(sleep=sleep)
        self.assertEqual(self.restarts,[10.])

    def test_pid_and_relay_reservation_and_capture_all_defer(self):
        self.run_maintenance(weather=lambda:self.now<5,diagnostics=lambda:self.now<10,
                             status=lambda:{'busy':False,'priority_active':self.now<15})
        self.assertEqual(self.restarts,[15.])

    def test_lock_is_held_until_reconnection_finishes(self):
        def ready(_):
            with self.path.open('r+') as other:
                with self.assertRaises(BlockingIOError):fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.run_maintenance(ready=ready)
        with self.path.open('r+') as other:fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_timeout_never_restarts_during_weather(self):
        with self.assertRaisesRegex(RuntimeError,'no restart performed'):
            self.run_maintenance(weather=lambda:True,timeout=10)
        self.assertFalse(self.restarts)

    def test_starting_relay_socket_is_waited_for_before_restart(self):
        def status():
            if self.now<5:raise ConnectionRefusedError('relay starting')
            return {'busy':False,'priority_active':False}
        self.run_maintenance(status=status)
        self.assertEqual(self.restarts,[5.])

    def test_permanently_unavailable_relay_never_restarts_host(self):
        def status():raise ConnectionRefusedError('relay unavailable')
        with self.assertRaisesRegex(RuntimeError,'no restart performed'):
            self.run_maintenance(status=status,timeout=10)
        self.assertFalse(self.restarts)

    def test_restart_failure_releases_lock_without_retry_storm(self):
        def failed():self.restarts.append(self.now);raise RuntimeError('restart failed')
        with self.assertRaisesRegex(RuntimeError,'restart failed'):self.run_maintenance(restart=failed)
        self.assertEqual(len(self.restarts),1)
        with self.path.open('r+') as other:fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_old_login_does_not_satisfy_readiness(self):
        path=self.root/'host.log';path.write_text('DMR, Logged into the master successfully\n');watch=LoginWatch(lambda:path)
        self.assertFalse(watch.seen())
        def sleep(seconds):
            self.sleep(seconds)
            with path.open('a') as stream:stream.write('DMR, Logged into the master successfully\n')
        wait_ready(watch,status=lambda:{'connected':True,'host':['127.0.0.1',1]},sleep=sleep,clock=lambda:self.now,timeout=10)
        self.assertEqual(self.now,2.)

    def test_missing_or_unconfirmed_login_fails_without_false_success(self):
        watch=LoginWatch(lambda:self.root/'missing.log')
        with self.assertRaisesRegex(RuntimeError,'fresh master login'):
            wait_ready(watch,status=lambda:{'connected':True,'host':['127.0.0.1',1]},sleep=self.sleep,clock=lambda:self.now,timeout=4)

if __name__=='__main__':unittest.main()
