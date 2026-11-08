"""One atomic, checked bulletin ZIP in RAM; explicitly labelled cached replay."""
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import wave
import zipfile

UTC=dt.timezone.utc
MAX_BYTES=8*1024*1024

def stamp(text):
    value=dt.datetime.fromisoformat(text)
    if value.tzinfo is None:raise ValueError('Timestamp needs a timezone')
    return value.astimezone(UTC)

def validate(manifest,read):
    stamp(manifest['generated_utc'])
    clips=manifest['clips']
    if not 1<=len(clips)<=12:raise ValueError('Invalid cached part count')
    seen=set();total=0
    for clip in clips:
        name=clip['file']
        if Path(name).name!=name or '/' in name or '\\' in name or not name.endswith('.wav') or name in seen:raise ValueError('Invalid cached filename')
        seen.add(name);data=read(name);total+=len(data)
        if total>MAX_BYTES:raise ValueError('Cached bulletin too large')
        if hashlib.sha256(data).hexdigest()!=clip['sha256']:raise ValueError('Cached audio checksum mismatch')
        with wave.open(io.BytesIO(data),'rb') as audio:
            if (audio.getnchannels(),audio.getsampwidth(),audio.getframerate())!=(1,2,8000) or not .5<audio.getnframes()/8000<=39:raise ValueError('Invalid cached audio format or duration')
    return seen

def store(directory,cache):
    directory=Path(directory);cache=Path(cache)
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest.get('fallback'):raise ValueError('Do not renew the age of a cached report')
    if not -60<=(dt.datetime.now(UTC)-stamp(manifest['generated_utc'])).total_seconds()<=1800:raise ValueError('Only cache a freshly prepared bulletin')
    names=validate(manifest,lambda name:(directory/name).read_bytes())
    cache.parent.mkdir(parents=True,exist_ok=True)
    handle,path=tempfile.mkstemp(prefix='.last-bulletin-',suffix='.zip',dir=str(cache.parent));os.close(handle)
    temporary=Path(path)
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json',json.dumps(manifest))
            archive.writestr('bulletin.txt',(directory/'bulletin.txt').read_text(encoding='utf-8'))
            for name in sorted(names):archive.write(directory/name,name)
        with temporary.open('r+b') as saved:os.fsync(saved.fileno())
        os.chmod(temporary,0o600);temporary.replace(cache)
    finally:temporary.unlink(missing_ok=True)
    print('LAST_BULLETIN_SAVED',manifest['generated_utc'],flush=True)

def restore(cache,directory,base,reason):
    cache=Path(cache);directory=Path(directory);base=Path(base)
    if not cache.exists():raise FileNotFoundError('No previous bulletin in RAM; fresh data needed once after reboot')
    with zipfile.ZipFile(cache) as archive:
        if sum(item.file_size for item in archive.infolist())>MAX_BYTES+65536:raise ValueError('Cache archive too large')
        manifest=json.loads(archive.read('manifest.json'))
        names=validate(manifest,archive.read)
        if set(archive.namelist())!=names|{'manifest.json','bulletin.txt'} or len(archive.namelist())!=len(names)+2:raise ValueError('Unexpected cache archive entries')
        for name in names:(directory/name).write_bytes(archive.read(name))
        text=archive.read('bulletin.txt').decode('utf-8')
    notice=json.loads((base/'fallback-notice.json').read_text(encoding='utf-8'))
    notice_data=(base/'fallback-notice.wav').read_bytes()
    if hashlib.sha256(notice_data).hexdigest()!=notice['sha256']:raise ValueError('Fallback notice damaged')
    with wave.open(io.BytesIO(notice_data),'rb') as audio:
        if (audio.getnchannels(),audio.getsampwidth(),audio.getframerate())!=(1,2,8000):raise ValueError('Bad fallback notice audio')
        notice_pcm=audio.readframes(audio.getnframes())
    first=directory/manifest['clips'][0]['file']
    with wave.open(str(first),'rb') as audio:old_pcm=audio.readframes(audio.getnframes())
    merged=notice_pcm+b'\x00\x00'*1600+old_pcm
    if len(merged)/16000<=39:
        filename='fallback-first.wav';path=directory/filename
        with wave.open(str(path),'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(8000);audio.writeframes(merged)
        manifest['clips'][0]=dict(file=filename,seconds=len(merged)/16000,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    else:
        filename='fallback-notice.wav';(directory/filename).write_bytes(notice_data)
        manifest['clips'].insert(0,dict(file=filename,seconds=len(notice_pcm)/16000,sha256=notice['sha256']))
        if len(manifest['clips'])>12:raise ValueError('Too many cached parts including notice')
    now=dt.datetime.now(UTC)
    if stamp(manifest['generated_utc'])>now+dt.timedelta(seconds=60):raise ValueError('Cached report timestamp is in the future')
    manifest['fallback']={'original_generated_utc':manifest['generated_utc'],'activated_utc':now.isoformat(),'reason':str(reason),'notice_sha256':notice['sha256']}
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (directory/'bulletin.txt').write_text(notice['text']+'\n\n'+text,encoding='utf-8')
    print('CACHED_BULLETIN_SELECTED',manifest['generated_utc'],'age_minutes',round((now-stamp(manifest['generated_utc'])).total_seconds()/60),flush=True)

def generate(directory,base,cache,prepare):
    # Import here so the ZIP helpers can be tested without the network planner.
    from runtime import WeatherUnavailable
    try:prepare(base,directory)
    except WeatherUnavailable as exc:
        restore(cache,directory,base,exc)
        return True
    return False
