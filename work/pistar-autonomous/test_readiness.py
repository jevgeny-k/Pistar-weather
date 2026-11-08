import unittest
from readiness import wait_for_ready

class ReadinessTests(unittest.TestCase):
    def test_startup_then_connection(self):
        responses=iter([OSError('socket not created'),{'connected':False,'host':['127.0.0.1',1]},{'connected':True,'host':['127.0.0.1',1]}])
        now=[0]
        def request(*args,**kwargs):
            result=next(responses)
            if isinstance(result,Exception):raise result
            return result
        wait_for_ready(request,timeout=10,sleep=lambda seconds:now.__setitem__(0,now[0]+seconds),clock=lambda:now[0])
        self.assertEqual(now[0],4)
    def test_never_connected_times_out(self):
        now=[0]
        with self.assertRaisesRegex(RuntimeError,'not ready'):
            wait_for_ready(lambda *args,**kwargs:{'connected':False},timeout=5,sleep=lambda seconds:now.__setitem__(0,now[0]+seconds),clock=lambda:now[0])
        self.assertEqual(now[0],5)

if __name__=='__main__':unittest.main()
