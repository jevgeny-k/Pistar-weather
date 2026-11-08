from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import wave
import zipfile
from assemble import assemble

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'outputs/pi-only-preparation'
with tempfile.TemporaryDirectory() as tmp:
    copy=Path(tmp)/'bank-test'
    shutil.copytree(BASE,copy)
    result=copy/'test.wav'
    assemble(copy,copy/'pilot-plan.json',result)
    assert result.read_bytes()==(BASE/'pilot-assembled.wav').read_bytes()
    with wave.open(str(result),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,8000)
    plan=json.loads((copy/'pilot-plan.json').read_text())
    bank=json.loads((copy/'bank-manifest.json').read_text())
    key=plan['ids'][0]
    record=bank['generated'].pop(key)
    (copy/'bank-manifest.json').write_text(json.dumps(bank))
    try:assemble(copy,copy/'pilot-plan.json',result)
    except ValueError as exc:assert 'missing' in str(exc)
    else:raise AssertionError('Missing phrase accepted')
    bank['generated'][key]=record
    (copy/'bank-manifest.json').write_text(json.dumps(bank))
    phrase=copy/'bank'/f'{key}.wav'
    phrase.write_bytes(phrase.read_bytes()+b'changed')
    try:assemble(copy,copy/'pilot-plan.json',result)
    except ValueError as exc:assert 'checksum' in str(exc)
    else:raise AssertionError('Damaged audio accepted')
print('PASS: deterministic audio, format, missing phrase and corruption checks')
source=BASE/'source'
source.mkdir(exist_ok=True)
for name in ('catalog.py','assemble.py','render_seed.py','verify_prepare.py'):
    shutil.copy2(Path(__file__).parent/name,source/name)
with zipfile.ZipFile(BASE/'pi-pilot.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in ('catalog.json','bank-manifest.json','pilot-plan.json'):
        z.write(BASE/name,name)
    z.write(source/'assemble.py','assemble.py')
    for p in sorted((BASE/'bank').glob('*.wav')):z.write(p,p.relative_to(BASE).as_posix())
catalog=json.loads((BASE/'catalog.json').read_text(encoding='utf-8'))
bank=json.loads((BASE/'bank-manifest.json').read_text(encoding='utf-8'))
print('CATALOG',len(catalog['entries']),'RENDERED',len(bank['generated']))
print('PILOT_SHA256',hashlib.sha256((BASE/'pilot-assembled.wav').read_bytes()).hexdigest())
