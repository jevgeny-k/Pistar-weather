from pathlib import Path
from array import array
import hashlib
import json
import shutil
import wave
import zipfile

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'outputs/pi-only-preparation'
catalog=json.loads((BASE/'catalog.json').read_text(encoding='utf-8'))
manifest=json.loads((BASE/'bank-manifest.json').read_text(encoding='utf-8'))
assert manifest['profile']==catalog['profile']
assert set(manifest['generated'])==set(catalog['entries'])
seconds=0
for key,entry in catalog['entries'].items():
    record=manifest['generated'][key];path=BASE/entry['wav']
    assert record['text_sha256']==entry['text_sha256'],key
    assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'],key
    with wave.open(str(path),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,8000),key
        assert w.getnframes()==record['frames'] and .1<w.getnframes()/8000<39,key
        pcm=array('h');pcm.frombytes(w.readframes(w.getnframes()))
        assert 1000<max(abs(n) for n in pcm)<32767,key
        seconds+=w.getnframes()/8000
source=BASE/'source';source.mkdir(exist_ok=True)
for p in Path(__file__).parent.glob('*.py'):shutil.copy2(p,source/p.name)
shutil.copy2(Path(__file__).parent/'OPERATIONS.md',BASE/'OPERATIONS.md')
archive=BASE/'pistar-autonomous-v1.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name in ('catalog.json','bank-manifest.json'):z.write(BASE/name,name)
    z.write(BASE/'OPERATIONS.md','OPERATIONS.md')
    for name in ('assemble.py','runtime.py','play.py','autonomous.py','readiness.py','retry_http.py','site_settings.py'):z.write(source/name,name)
    for p in sorted((BASE/'bank').glob('*.wav')):z.write(p,p.relative_to(BASE).as_posix())
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(BASE/'pistar-autonomous-v1.zip.sha256').write_text(digest+'  '+archive.name+'\n')
print('FULL_BANK_VERIFIED',len(catalog['entries']),round(seconds/60,1),'minutes',archive.stat().st_size,'bytes',digest)
