"""Pi-portable phrase assembler. Standard library only; no neural runtime."""
from array import array
import hashlib
import json
from pathlib import Path
import sys
import wave


def assemble(base,plan_path,out_path):
    base=Path(base)
    catalog=json.loads((base/'catalog.json').read_text(encoding='utf-8'))
    bank=json.loads((base/'bank-manifest.json').read_text(encoding='utf-8'))
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8'))
    if bank['profile']!=catalog['profile']:raise ValueError('Mixed voice profiles')
    clips=[]
    for key in plan['ids']:
        entry=catalog['entries'][key];record=bank['generated'].get(key)
        if not record:raise ValueError('Phrase missing from bank: '+key)
        if record['text_sha256']!=entry['text_sha256']:raise ValueError('Phrase text changed: '+key)
        path=(base/entry['wav']).resolve()
        if path.parent!=(base/'bank').resolve():raise ValueError('Invalid phrase path')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Bad phrase checksum: '+key)
        with wave.open(str(path),'rb') as w:
            if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,8000):raise ValueError('Unsupported phrase audio format')
            clips.append((w.readframes(w.getnframes()),entry['pause_ms']))
    with wave.open(str(out_path),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(8000)
        for pcm,pause_ms in clips:
            out.writeframes(pcm)
            out.writeframes(b'\x00\x00'*(8000*pause_ms//1000))
    with wave.open(str(out_path),'rb') as w:seconds=w.getnframes()/8000
    print('ASSEMBLED',out_path,round(seconds,2),'seconds; no TTS runtime used',flush=True)
    return seconds


if __name__=='__main__':assemble(*sys.argv[1:])
