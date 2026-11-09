"""One bounded RAM-only pre/post snapshot on a new host queue overflow.

Stores DMR timing metadata, never IP addresses, radio IDs or UDP payloads.
A short private UART transcript may contain radio frames/configuration.
It is root-only, size-limited, and never uploaded automatically.
"""
import collections
import datetime as dt
import gzip
import json
from pathlib import Path
import resource
import selectors
import signal
import socket
import subprocess
import time

COLUMNS=['utc_epoch','monotonic','interface','direction','source_port','destination_port','sequence','flags','stream']
MAX_EVENTS=12000
UART_LIMIT=512*1024
STATE=Path('/run/pistar-weather-diagnostics')

def metadata(frame,interface,direction,wall,mono):
    if interface not in {'lo','wlan0'} or (interface=='lo' and direction!=4):return None
    if len(frame)<42 or frame[12:14]!=b'\x08\x00':return None
    ip=frame[14:];ihl=(ip[0]&15)*4
    if ip[0]>>4!=4 or ihl<20 or len(ip)<ihl+8 or ip[9]!=17:return None
    if int.from_bytes(ip[6:8],'big')&0x1fff:return None
    udp=ip[ihl:];length=int.from_bytes(udp[4:6],'big')
    if length!=63 or len(udp)<length:return None
    data=udp[8:length]
    if len(data)!=55 or data[:4]!=b'DMRD':return None
    return (wall,mono,interface,direction,int.from_bytes(udp[:2],'big'),int.from_bytes(udp[2:4],'big'),data[4],data[15],data[16:20].hex())

class Window:
    def __init__(self):self.rows=collections.deque(maxlen=MAX_EVENTS)
    def append(self,event):
        self.rows.append(event)
        while self.rows and event[1]-self.rows[0][1]>120:self.rows.popleft()
    def snapshot(self,now):return [row for row in self.rows if now-row[1]<=120]

class ErrorTail:
    def __init__(self):self.identity=None;self.position=0;self.initial=True
    def poll(self,path):
        try:info=path.stat()
        except FileNotFoundError:return None
        identity=(str(path),info.st_ino)
        if identity!=self.identity:
            self.position=info.st_size if self.initial else 0
            self.initial=False;self.identity=identity
        if info.st_size<self.position:self.position=0
        found=None
        with path.open(errors='replace') as source:
            source.seek(self.position)
            # Bound each pass even if another process writes a large log burst.
            for _ in range(4096):
                line=source.readline(4096)
                if not line:break
                if 'overflow in the DMR slot RF queue' in line and found is None:found=line[3:26]
            self.position=source.tell()
        return found

def atomic_json(path,data):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data),encoding='utf-8');temporary.chmod(0o600);temporary.replace(path)

def save_snapshot(directory,pre,post,reason,details):
    data={'columns':COLUMNS,'pre':pre[-MAX_EVENTS:],'post':post[-4000:],'reason':reason,'details':details}
    raw=gzip.compress(json.dumps(data,separators=(',',':')).encode(),compresslevel=3)
    if len(raw)>2*1024*1024:raise ValueError('Diagnostic snapshot exceeds RAM limit')
    path=directory/'snapshot.json.gz';temporary=path.with_suffix('.tmp');temporary.write_bytes(raw);temporary.chmod(0o600);temporary.replace(path)
    return len(raw)

def trace_limit():resource.setrlimit(resource.RLIMIT_FSIZE,(UART_LIMIT,UART_LIMIT))

def start_trace(directory):
    pid=int(subprocess.check_output(['systemctl','show','mmdvmhost','-p','MainPID','--value'],text=True,timeout=3).strip())
    if not pid:return None
    return subprocess.Popen(['strace','-ttt','-xx','-s','120','-e','trace=read,write','-P','/dev/ttyAMA0','-p',str(pid),'-o',str(directory/'uart.txt')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,preexec_fn=trace_limit)

def stop_trace(process):
    if process is None or process.poll() is not None:return
    process.send_signal(signal.SIGINT)
    try:process.wait(timeout=3)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)

def main():
    STATE.mkdir(mode=0o700,parents=True,exist_ok=True);STATE.chmod(0o700)
    # A snapshot is one-shot; keep prior evidence until explicitly removed.
    if (STATE/'snapshot.json.gz').exists():raise SystemExit('Existing snapshot retained; clear it explicitly before rearming')
    running=[True];manual=[False]
    signal.signal(signal.SIGTERM,lambda *_:running.__setitem__(0,False))
    signal.signal(signal.SIGINT,lambda *_:running.__setitem__(0,False))
    signal.signal(signal.SIGUSR1,lambda *_:manual.__setitem__(0,True))
    sel=selectors.DefaultSelector();sockets=[]
    for interface in ('lo','wlan0'):
        sock=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x0800))
        try:sock.bind((interface,0))
        except OSError:
            sock.close()
            if interface=='lo':raise
            continue
        sock.setblocking(False);sel.register(sock,selectors.EVENT_READ,interface);sockets.append(sock)
    window=Window();tail=ErrorTail();next_poll=0.;trigger=None;trace=None;pre=[];post=collections.deque(maxlen=4000);finish=None
    armed=dt.datetime.now(dt.timezone.utc).isoformat()
    atomic_json(STATE/'state.json',{'phase':'armed','armed_utc':armed})
    print('QUEUE_DIAGNOSTICS_ARMED_RAM_ONLY',flush=True)
    try:
        while running[0]:
            now=time.monotonic()
            if trigger is None and now>=next_poll:
                next_poll=now+.25
                today=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')
                error=tail.poll(Path('/var/log/pi-star/MMDVM-'+today+'.log'))
                if error or manual[0]:
                    trigger='host_queue_overflow' if error else 'operator_requested'
                    pre=window.snapshot(now);window.rows.clear();finish=now+30
                    details={'armed_utc':armed,'trigger_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'error_timestamp_utc':error}
                    try:trace=start_trace(STATE)
                    except (OSError,ValueError,subprocess.SubprocessError):details['uart_trace']='unavailable'
                    atomic_json(STATE/'state.json',{'phase':'capturing','reason':trigger,**details})
                    print('QUEUE_DIAGNOSTICS_TRIGGERED',trigger,flush=True)
            if trigger and now>=finish:break
            if trace and (STATE/'uart.txt').exists() and (STATE/'uart.txt').stat().st_size>=UART_LIMIT:stop_trace(trace)
            for key,_ in sel.select(.1):
                # A bounded batch keeps timer/error polling responsive.
                for _ in range(64):
                    try:frame,addr=key.fileobj.recvfrom(4096)
                    except BlockingIOError:break
                    event=metadata(frame,key.data,addr[2],time.time(),time.monotonic())
                    if event:
                        if trigger:post.append(event)
                        else:window.append(event)
        if trigger:
            stop_trace(trace);size=save_snapshot(STATE,pre,list(post),trigger,details)
            atomic_json(STATE/'state.json',{'phase':'complete','reason':trigger,'pre_events':len(pre),'post_events':len(post),'snapshot_bytes':size,**details})
            print('QUEUE_DIAGNOSTICS_COMPLETE',len(pre),len(post),size,flush=True)
    finally:
        stop_trace(trace);sel.close()
        for sock in sockets:sock.close()

if __name__=='__main__':main()
