"""Operator-requested host restart, mutually exclusive with weather playback."""
import datetime as dt
import fcntl
import json
from pathlib import Path
import socket
import subprocess
import time

LOCK=Path('/run/pistar-weather/autonomous.lock')
CONTROL=Path('/run/pistar-weather/control.sock')
DIAGNOSTICS=Path('/run/pistar-weather-diagnostics/state.json')

def command(*args):return subprocess.check_output(args,text=True,timeout=60).strip()

def relay_status():
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(3);client.connect(str(CONTROL))
        client.sendall(b'{"op":"status"}');data=json.loads(client.recv(4096))
    if not data.get('ok'):raise RuntimeError('Relay status unavailable')
    return data

def weather_running():
    # Queued systemd jobs have no PID; waiting for those would deadlock After=.
    return int(command('systemctl','show','pistar-weather-autonomous.service','-p','MainPID','--value') or '0')>0

def diagnostics_capturing():
    try:return json.loads(DIAGNOSTICS.read_text()).get('phase')=='capturing'
    except FileNotFoundError:return False
    except (OSError,ValueError):return True

class LoginWatch:
    def __init__(self,path=None):
        self.path=path or (lambda:Path('/var/log/pi-star/MMDVM-'+dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')+'.log'))
        self.identity=None;self.position=0;self.found=False
        try:
            current=self.path();info=current.stat();self.identity=(str(current),info.st_ino);self.position=info.st_size
        except FileNotFoundError:pass

    def seen(self):
        if self.found:return True
        try:current=self.path();info=current.stat()
        except FileNotFoundError:return False
        identity=(str(current),info.st_ino)
        if identity!=self.identity or info.st_size<self.position:self.position=0;self.identity=identity
        with current.open(errors='replace') as source:
            source.seek(self.position)
            for _ in range(4096):
                line=source.readline(4096)
                if not line:break
                if 'Logged into the master successfully' in line:self.found=True
            self.position=source.tell()
        return self.found

def restart_host():
    login=LoginWatch()
    command('systemctl','restart','mmdvmhost.service')
    return login

def wait_ready(login,status=relay_status,sleep=time.sleep,clock=time.monotonic,timeout=90):
    deadline=clock()+timeout
    while clock()<deadline:
        state=status()
        if login.seen() and state.get('connected') and state.get('host'):return
        sleep(2)
    raise RuntimeError('Host restarted but a fresh master login was not confirmed')

def maintain(lock_path=LOCK,status=relay_status,weather=weather_running,diagnostics=diagnostics_capturing,
             restart=restart_host,ready=wait_ready,sleep=time.sleep,clock=time.monotonic,timeout=900,log=print):
    deadline=clock()+timeout;announced=False
    # Never create a root-owned file here: the existing lock belongs to weather.
    with Path(lock_path).open('r+') as lock:
        while clock()<deadline:
            acquired=False
            try:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);acquired=True
                except BlockingIOError:pass
                if acquired:
                    state=status()
                    if not weather() and not diagnostics() and not state.get('busy') and not state.get('priority_active'):
                        log('MODEM_MAINTENANCE_RESTARTING_HOST',flush=True)
                        login=restart();ready(login)
                        log('MODEM_MAINTENANCE_READY',flush=True)
                        return
                if not announced:
                    log('MODEM_MAINTENANCE_DEFERRED_WEATHER_OR_CAPTURE',flush=True);announced=True
            finally:
                if acquired:fcntl.flock(lock,fcntl.LOCK_UN)
            sleep(5)
    raise RuntimeError('Maintenance deferred too long; no restart performed')

if __name__=='__main__':maintain()
