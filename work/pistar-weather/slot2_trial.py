"""Bounded TS2 isolation trial with persisted automatic restore; root only."""
from contextlib import contextmanager
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

CONFIG=Path('/etc/mmdvmhost')
STATE=Path('/opt/pistar-weather/slot2-trial.json')
TIMER='pistar-slot2-restore.timer'

def set_slot2(source,value):
    match=re.search(r'(?ms)^\[DMR Network\]\n.*?(?=^\[|\Z)',source)
    if not match:raise ValueError('DMR Network section missing')
    section,count=re.subn(r'(?m)^Slot2=[01]$', 'Slot2='+str(value),match.group(0))
    if count!=1:raise ValueError('Expected exactly one network Slot2 setting')
    return source[:match.start()]+section+source[match.end():]

def command(*args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=30)

@contextmanager
def writable():
    was_ro='ro' in command('findmnt','-no','OPTIONS','/').stdout.strip().split(',')
    command('mount','-o','remount,rw','/')
    try:yield
    finally:
        command('sync')
        if was_ro:command('mount','-o','remount,ro','/')

def write_config(text):
    path=CONFIG.with_suffix('.slot2-trial.tmp')
    original=CONFIG.stat()
    with path.open('w') as output:
        output.write(text);output.flush();os.fsync(output.fileno())
    os.chmod(path,original.st_mode&0o777);os.chown(path,original.st_uid,original.st_gid)
    path.replace(CONFIG)

def write_state(state):
    path=STATE.with_suffix('.tmp');path.write_text(json.dumps(state,indent=2));path.chmod(0o600);path.replace(STATE)

def weather_running():
    result=command('systemctl','show','pistar-weather-autonomous.service','-p','ActiveState','--value').stdout.strip()
    return result in {'active','activating','deactivating','reloading'}

def start():
    if STATE.exists() and json.loads(STATE.read_text()).get('active'):raise ValueError('A trial is already active')
    if weather_running():raise ValueError('Weather bulletin is running; start after it finishes')
    source=CONFIG.read_text()
    if set_slot2(source,1)!=source:raise ValueError('TS2 was already disabled; refusing to change baseline')
    now=time.time();until=now+3600
    stamp=dt.datetime.fromtimestamp(now,dt.timezone.utc).strftime('%Y%m%d-%H%M%S')
    deadline=dt.datetime.fromtimestamp(until,dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    state={'active':True,'started_utc':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),'until_epoch':until,'until_utc':deadline,'original_slot2':1,'original_config_sha256':hashlib.sha256(source.encode()).hexdigest(),'description':'Temporarily disable network TS2; preserve server static groups'}
    service='''[Unit]
Description=Restore network TS2 after bounded radio test
After=network.target
StartLimitIntervalSec=0

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/pistar-weather/slot2_trial.py restore
TimeoutStartSec=240
Restart=on-failure
RestartSec=30
NoNewPrivileges=yes
'''
    timer='''[Unit]
Description=Restore TS2 at the test deadline or after reboot

[Timer]
OnCalendar='''+deadline+'''
OnBootSec=150s
AccuracySec=1s
Unit=pistar-slot2-restore.service

[Install]
WantedBy=timers.target
'''
    with writable():
        backup=Path('/var/backups/pistar-weather/slot2-trial-'+stamp)
        backup.mkdir(mode=0o700);shutil.copy2(CONFIG,backup/'mmdvmhost');(backup/'mmdvmhost').chmod(0o600)
        state['backup']=str(backup/'mmdvmhost');write_state(state)
        Path('/etc/systemd/system/pistar-slot2-restore.service').write_text(service)
        Path('/etc/systemd/system/'+TIMER).write_text(timer)
        command('systemctl','daemon-reload')
        command('systemctl','enable','--now',TIMER)
        # Arm the restore before disabling the slot.
        write_config(set_slot2(source,0))
    command('systemctl','restart','mmdvmhost')
    print('SLOT2_TRIAL_STARTED',json.dumps(state),flush=True)

def restore(force=False):
    if not STATE.exists():print('NO_TRIAL');return
    state=json.loads(STATE.read_text())
    if not state.get('active'):print('TRIAL_ALREADY_RESTORED');return
    if not force and time.time()<state['until_epoch']:print('RESTORE_ARMED_FOR',state['until_utc']);return
    deadline=time.monotonic()+180
    while weather_running():
        if time.monotonic()>deadline:raise RuntimeError('Waiting for bulletin to finish; restore will retry in 30 seconds')
        time.sleep(5)
    source=CONFIG.read_text();updated=set_slot2(source,state['original_slot2'])
    with writable():
        if updated!=source:write_config(updated)
    # Keep active=true until the service restart succeeds, so a failure is retried.
    command('systemctl','restart','mmdvmhost')
    with writable():
        state['active']=False;state['restored_utc']=dt.datetime.now(dt.timezone.utc).isoformat();write_state(state)
        command('systemctl','disable','--now',TIMER)
    command('systemctl','start','--no-block','pistar-weather-bootcheck.service')
    print('SLOT2_RESTORED',json.dumps(state),flush=True)

if __name__=='__main__':
    if os.geteuid()!=0:raise SystemExit('Root required')
    if sys.argv[1]=='start':start()
    elif sys.argv[1]=='restore':restore('--force' in sys.argv)
    else:raise SystemExit('Expected start or restore [--force]')
