"""Play a prepared fresh bank bulletin through the existing local private relay."""
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
from readiness import wait_for_ready

def play(directory,cached=False):
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text())
    stamp=dt.datetime.fromisoformat(manifest['generated_utc'])
    if cached:
        fallback=manifest.get('fallback',{})
        if fallback.get('original_generated_utc')!=manifest['generated_utc'] or not fallback.get('notice_sha256'):raise ValueError('Cached replay needs an explicit notice')
        stamp=dt.datetime.fromisoformat(fallback['activated_utc'])
    elif manifest.get('fallback'):raise ValueError('Cached report requires explicit replay mode')
    def fresh():
        if not -60<=(dt.datetime.now(dt.timezone.utc)-stamp).total_seconds()<=1800:raise ValueError('Bulletin expired')
    fresh();wait_for_ready(request);fresh();packets=[]
    if not 1<=len(manifest['clips'])<=12:raise ValueError('Invalid part count')
    for i,clip in enumerate(manifest['clips']):
        name=clip['file']
        if Path(name).name!=name or not name.endswith('.wav'):raise ValueError('Invalid audio path')
        wav=directory/name
        if hashlib.sha256(wav.read_bytes()).hexdigest()!=clip['sha256']:raise ValueError('Damaged audio')
        raw=wav.with_suffix('.raw');ambe=wav.with_suffix('.ambe72');decoded=wav.with_suffix('.decoded.raw')
        subprocess.run(['sox','-D',str(wav),'-t','raw','-r','8000','-e','signed-integer','-b','16','-c','1','-L',str(raw),'gain','-6','highpass','100','lowpass','3400','gain','-n','-3','pad','0.5','0.5'],check=True)
        subprocess.run([str(BASE/'encode'),str(raw),str(ambe)],check=True)
        subprocess.run([str(BASE/'encode'),'-d',str(ambe),str(decoded)],check=True)
        samples=array('h');samples.frombytes(decoded.read_bytes())
        if not 8000<len(samples)<41*8000 or not 1000<max(abs(v) for v in samples)<32767:raise ValueError('Bad encoded audio')
        packet=STATE/('autonomous-'+str(i)+'.dmr55');packet.write_bytes(build_call(ambe.read_bytes()));packets.append(packet)
    token=None
    if request({'op':'status'}).get('weather_priority'):
        reserved=request({'op':'begin_bulletin'})
        if not reserved.get('ok'):raise RuntimeError('Could not reserve weather priority')
        token=reserved['token']
    try:
        for i,packet in enumerate(packets):
            if i:time.sleep(5)
            fresh();result=request({'op':'play','file':str(packet)});print(json.dumps(result),flush=True)
            if not result.get('ok'):raise RuntimeError('Playback interrupted')
    finally:
        if token:
            released=request({'op':'end_bulletin','token':token})
            if not released.get('ok'):raise RuntimeError('Could not release weather priority')
    print('AUTONOMOUS_BULLETIN_SENT',flush=True)

if __name__=='__main__':play(sys.argv[1])
