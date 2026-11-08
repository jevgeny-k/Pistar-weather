"""Read-only startup checks. No RF test, configuration changes or modem resets."""
import configparser
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import time
import urllib.request

BASE=Path('/opt/pistar-weather/autonomous-v1')
STATE=Path('/run/pistar-weather')

def run(args):
    result=subprocess.run(args,capture_output=True,text=True,timeout=15)
    return result.returncode,result.stdout.strip()

def verify_bank(base):
    catalog=json.loads((base/'catalog.json').read_text())
    bank=json.loads((base/'bank-manifest.json').read_text())
    if bank['profile']!=catalog['profile']:raise ValueError('Voice profile mismatch')
    entries=catalog['entries']
    if len(entries)!=1604 or set(entries)!=set(bank['generated']):raise ValueError('Incomplete bank')
    bad=[]
    for key,e in entries.items():
        path=(base/e['wav']).resolve();record=bank['generated'][key]
        if path.parent!=(base/'bank').resolve():raise ValueError('Invalid bank path')
        if not path.is_file() or record['text_sha256']!=e['text_sha256'] or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:bad.append(key)
    if bad:raise ValueError('Damaged or missing phrases: '+', '.join(bad[:10]))
    return str(len(entries))+' phrases; all SHA256 checks passed'

def relay_status():
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(3);s.connect(str(STATE/'control.sock'))
        s.sendall(b'{"op":"status"}')
        return json.loads(s.recv(4096))

def main():
    from site_settings import configured_radio_id, load_site, require_radio_id
    site = load_site(required=True)
    radio_id = require_radio_id(configured_radio_id())
    checks={}
    def check(name,action,warning=False):
        try:checks[name]={'status':'ok','detail':action()}
        except Exception as exc:checks[name]={'status':'warning' if warning else 'failed','detail':str(exc)}
    def startup():
        for unit in ['mmdvmhost.timer','pistar-weather-relay.service','pistar-weather-autonomous.timer']:
            if run(['systemctl','is-enabled',unit])[0]:raise ValueError(unit+' not enabled')
        if run(['systemctl','is-enabled','pistar-weather-frozen.timer'])[0]==0:raise ValueError('Old frozen timer still enabled')
        return 'Modem, relay and fresh bulletin timer enabled; frozen timer disabled'
    check('autostart',startup)
    def connected():
        deadline=time.monotonic()+90
        while True:
            try:
                status=relay_status()
                active=all(run(['systemctl','is-active',u])[0]==0 for u in ['mmdvmhost','pistar-weather-relay','pistar-weather-autonomous.timer'])
                if active and status.get('connected') and status.get('host'):return 'Services active; master connected'
            except (OSError,ValueError):pass
            if time.monotonic()>=deadline:raise ValueError('Services or master not ready within 90 seconds')
            time.sleep(3)
    check('connection',connected)
    check('voice_bank',lambda:verify_bank(BASE))
    def configuration():
        config=configparser.ConfigParser(strict=False);config.read('/etc/mmdvmhost')
        wanted={('General','Id'):str(radio_id),('DMR Network','RemoteAddress'):'127.0.0.1',('DMR Network','RemotePort'):'62039'}
        for section, options in site.get('expected_mmdvm', {}).items():
            for key, value in options.items():
                wanted[section, key] = str(value)
        wrong=[s+'/'+k for (s,k),v in wanted.items() if config.get(s,k,fallback=None)!=v]
        if wrong:raise ValueError('Unexpected settings: '+', '.join(wrong))
        for name in ['runtime.py','assemble.py','play.py','readiness.py','autonomous.py']:
            compile((BASE/name).read_text(),str(BASE/name),'exec')
        return 'Configured site expectations, relay and Python files verified'
    check('configuration',configuration)
    def storage():
        _,text=run(['dmesg'])
        errors=[line for line in text.splitlines() if re.search(r'EXT4-fs error|I/O error|mmc.*(?:error|timed out|timeout)',line,re.I)]
        if errors:raise ValueError('\n'.join(errors[-8:]))
        return 'No SD I/O or EXT4 errors in current boot log'
    check('sd_card',storage)
    def power():
        code,text=run(['vcgencmd','get_throttled'])
        if code:raise ValueError('Unable to read power status')
        bits=int(text.split('=')[1],16)
        if bits:raise ValueError(text+'; present or historical undervoltage/throttling flags')
        return text
    check('power',power,warning=True)
    def filesystem():
        _,options=run(['findmnt','-no','OPTIONS','/'])
        if 'ro' not in options.split(','):raise ValueError('Root is currently writable: '+options)
        return options
    check('root_read_only',filesystem,warning=True)
    def wifi():
        expected = site.get('wifi_ssid')
        if not expected:
            raise ValueError('Optional Wi-Fi profile expectation is not configured')
        config=Path('/etc/wpa_supplicant/wpa_supplicant.conf').read_text()
        if 'ssid='+json.dumps(expected, ensure_ascii=False) not in config:raise ValueError('Configured Wi-Fi profile missing')
        return 'Configured Wi-Fi profile present; credentials omitted'
    check('wifi_profile',wifi,warning=True)
    def statics():
        expected = site.get('expected_static_groups')
        if expected is None:
            raise ValueError('Optional static group expectations are not configured')
        keyfile=Path('/etc/bmapi.key')
        if keyfile.stat().st_mode&0o077:raise ValueError('API key permissions too broad')
        key=keyfile.read_text().strip().split('=',1)[1]
        req=urllib.request.Request(f'https://api.brandmeister.network/v2/device/{radio_id}/talkgroup',headers={'Authorization':'Bearer '+key,'Accept':'application/json'})
        with urllib.request.urlopen(req,timeout=8) as response:data=json.load(response)
        actual={(int(x['talkgroup']),int(x['slot'])) for x in data}
        if actual!={tuple(map(int, item)) for item in expected}:raise ValueError('Server static groups differ from private expectations')
        return 'Server static groups match private expectations'
    check('brandmeister_statics',statics,warning=True)
    levels={entry['status'] for entry in checks.values()}
    result='failed' if 'failed' in levels else 'warning' if 'warning' in levels else 'ok'
    report={'checked_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'result':result,'rf_reception':'not verified; separate receiver or user confirmation required','checks':checks}
    STATE.mkdir(exist_ok=True)
    temporary=STATE/'boot-health.json.tmp';temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2));temporary.chmod(0o644);temporary.replace(STATE/'boot-health.json')
    print(json.dumps(report,ensure_ascii=False),flush=True)
    if result=='failed':raise SystemExit(1)

if __name__=='__main__':main()
