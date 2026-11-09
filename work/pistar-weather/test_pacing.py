"""Exercise real relay.step() with simulated TS2 arrivals and processing jitter."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class Clock:
    def __init__(self):self.value=0.
    def now(self):return self.value

class Master:
    def __init__(self,clock):self.clock=clock
    def recv(self,size):
        self.clock.value+=.002
        return b'DMRD'+bytes(11)+b'\xa1'+bytes(39)  # other slot

class Selector:
    def __init__(self,clock,master):self.clock=clock;self.master=master;self.next=.017
    def select(self,timeout):
        delay=max(0,self.next-self.clock.value)
        if delay<=timeout+1e-12:
            self.clock.value+=delay;self.next+=.017
            return [(SimpleNamespace(fileobj=self.master,data='up'),None)]
        self.clock.value+=timeout
        return []

class Host:
    def __init__(self,clock):self.clock=clock;self.times=[]
    def sendto(self,data,addr):
        if data.startswith(b'voice'):self.times.append(self.clock.value)

class Client:
    def sendall(self,data):pass
    def close(self):pass

def simulate(module,wait_for_idle=False):
    clock=Clock();master=Master(clock);host=Host(clock)
    relay=module.Relay.__new__(module.Relay)
    relay.sel=Selector(clock,master);relay.up=master;relay.down=host
    relay.host=('127.0.0.1',1234);relay.connected=True;relay.idle=.05
    relay.serialize_slots=False;relay.weather_priority=False
    relay.reservation=None;relay.priority_draining=set();relay.network_active={};relay.suppressed={}
    relay.last_voice=.1 if wait_for_idle else -1.
    relay.job={'client':Client(),'packets':[b'voice'+bytes([i%256]) for i in range(240)],'index':0,'due':0.,'deadline':100.}
    with patch.object(module.time,'monotonic',clock.now):
        for _ in range(100000):
            if relay.job is None:break
            relay.step()
        else:raise AssertionError('Relay failed to progress')
    return host.times

class Pacing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import proxy
        cls.new=proxy
    def test_no_cumulative_drift_with_other_slot_traffic(self):
        new=simulate(self.new)
        expected=(len(new)-1)*.06
        self.assertLess(abs(new[-1]-new[0]-expected),.004)
        print('SIMULATED_DRIFT_SECONDS',round(new[-1]-new[0]-expected,6))
    def test_idle_wait_does_not_burst_old_deadlines(self):
        new=simulate(self.new,wait_for_idle=True)
        self.assertGreaterEqual(new[0],.15)
        self.assertLess(max(abs((b-a)-.06) for a,b in zip(new,new[1:])),.004)

if __name__=='__main__':unittest.main()
