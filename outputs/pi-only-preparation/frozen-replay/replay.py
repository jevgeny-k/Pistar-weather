"""Replay an explicitly frozen bulletin; never fetch or regenerate data."""
from pathlib import Path
import fcntl
import hashlib
import json
import socket
import sys
import time
sys.path.insert(0,'/opt/pistar-weather')
from proxy import validate_packets

BASE=Path(__file__).resolve().parent
STATE=Path('/run/pistar-weather')
def request(data):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(200);s.connect(str(STATE/'control.sock'))
        s.sendall(json.dumps(data).encode())
        return json.loads(s.recv(4096))
def main():
    manifest=json.loads((BASE/'manifest.json').read_text())
    prepared=[]
    for clip in manifest['clips']:
        path=BASE/clip['file']
        if path.parent!=BASE or Path(clip['file']).name!=clip['file']:raise ValueError('Bad snapshot path')
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=clip['sha256']:raise ValueError('Snapshot checksum mismatch')
        validate_packets(data);prepared.append(data)
    if '--check' in sys.argv:
        print('FROZEN_REPLAY_VALID',len(prepared),'parts; no transmission');return
    with open(STATE/'autonomous.lock','w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:print('SKIPPED: another bulletin is running');return
        status=request({'op':'status'})
        if status.get('busy') or not status.get('connected'):
            print('SKIPPED: relay busy or disconnected');return
        paths=[]
        for i,data in enumerate(prepared):
            target=STATE/('frozen-replay-'+str(i)+'.dmr55')
            target.write_bytes(data);paths.append(target)
        for i,path in enumerate(paths):
            if i:time.sleep(5)
            result=request({'op':'play','file':str(path)})
            print(json.dumps(result),flush=True)
            if not result.get('ok'):raise RuntimeError('Playback stopped; no retry this interval')
        print('FROZEN_REPLAY_SENT',flush=True)
if __name__=='__main__':main()
