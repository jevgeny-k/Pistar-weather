"""Validate a fresh bulletin, prepare every segment, then play local private calls."""
from pathlib import Path
from array import array
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
sys.path.insert(0,'/opt/pistar-weather')
from weather import BASE,STATE,build_call,request

STAGING=Path('/tmp/pistar-bulletin')
manifest=json.loads((STAGING/'manifest.json').read_text())
age=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(manifest['generated_utc'])).total_seconds()
if not -60<=age<=1800:raise ValueError('Bulletin is stale; regenerate before transmission')
if manifest['profile']!={'engine':'silero','model':'v5_6_ru','speaker':'xenia','rate':1.08,'pitch':1.15}:
    raise ValueError('Unexpected voice profile')
clips=manifest['clips']
if len(clips)!=3:raise ValueError('Expected three bulletin parts')
packets=[]
for clip in clips:
    name=clip['file']
    if Path(name).name!=name or not name.endswith('.wav'):raise ValueError('Invalid filename')
    wav=STAGING/name
    if hashlib.sha256(wav.read_bytes()).hexdigest()!=clip['sha256']:raise ValueError('SHA256 mismatch')
    raw=wav.with_suffix('.raw');ambe=wav.with_suffix('.ambe72');decoded=wav.with_suffix('.decoded.raw')
    for level in ['-3','-6']:
        subprocess.run(['sox',str(wav),'-t','raw','-r','8000','-e','signed-integer','-b','16','-c','1','-L',str(raw),
            'gain','-6','highpass','100','lowpass','3400','gain','-n',level,'pad','0.5','0.5'],check=True)
        subprocess.run([str(BASE/'encode'),str(raw),str(ambe)],check=True)
        subprocess.run([str(BASE/'encode'),'-d',str(ambe),str(decoded)],check=True)
        s=array('h');s.frombytes(decoded.read_bytes());peak=max(abs(x) for x in s)
        if 1000<peak<32767:break
    else:raise ValueError('Audio level check failed')
    packet=STATE/('bulletin-'+clip['name']+'.dmr55')
    packet.write_bytes(build_call(ambe.read_bytes()))
    packets.append(packet)
    print('Prepared',clip['name'],'seconds',round(len(s)/8000,1),'peak',peak,flush=True)
for i,packet in enumerate(packets):
    if i:time.sleep(5)
    # Re-check age after any wait/encoding, before every transmission.
    if (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(manifest['generated_utc'])).total_seconds()>1800:
        raise ValueError('Bulletin expired')
    print('Transmitting',packet.name,flush=True)
    result=request({'op':'play','file':str(packet)})
    print(json.dumps(result),flush=True)
    if not result.get('ok'):raise RuntimeError('Playback interrupted')
print('FULL_BULLETIN_SENT',flush=True)
