"""Render two local Dialogs-RU happy-voice auditions without changing the bank."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
MODEL=ROOT/'work/dialogs-ru'
OUT=ROOT/'outputs/dialogs-voices'
sys.path.insert(0,str(MODEL))
os.environ['DIALOGS_LOCAL_CKPT']=str(MODEL)


def main():
    import numpy as np
    from scipy.io.wavfile import write
    import torch
    torch.set_num_threads(2)
    checkpoint=MODEL/'averaged_G_615000.pth'
    with checkpoint.open('rb') as source:
        digest=hashlib.file_digest(source,'sha256').hexdigest()
    if digest!='b565b7b5311bd29102f15d2700c69ea71569605bc756fb5bb49d98afdc5e1e43':
        raise ValueError('Unexpected Dialogs-RU checkpoint')
    from tts import DialogsTTS
    engine=DialogsTTS()
    OUT.mkdir(exist_ok=True)
    records=[]
    for number,speaker,label in ((1,0,'Г+олос п+ервый, М+аша.'),(2,1,'Г+олос втор+ой, Св+ета.')):
        text=(label+' Д+обрый день! Это пр+обный прогн+оз пог+оды для Р+иги. '
              'Над+еюсь, теп+ерь мен+я сл+ышно хорош+о. Жел+аю вам прекр+асного дн+я!')
        started=time.monotonic()
        torch.manual_seed(2026+speaker)
        rate,audio,used=engine.synthesize(text,speaker_id=speaker,emotion_id=1,
                                         normalize=False,auto_stress=False)
        audio=np.asarray(audio,dtype=np.float32).reshape(-1)
        if not np.isfinite(audio).all() or not 1<len(audio)/rate<35:
            raise ValueError('Invalid audition audio')
        peak=float(np.max(np.abs(audio)))
        if peak<.001:raise ValueError('Silent audition')
        pcm=np.clip(np.rint(audio*(.70/peak)*32767),-32767,32767).astype(np.int16)
        path=OUT/('%02d-%s-happy.wav'%(number,'masha' if speaker==0 else 'sveta'))
        write(path,rate,pcm)
        record=dict(file=path.name,speaker_id=speaker,emotion='happy',emotion_id=1,
                    text=text,used_text=used,seconds=len(pcm)/rate,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        records.append(record)
        print('DIALOGS_AUDITION_READY',path.name,round(record['seconds'],2),
              'seconds; generation',round(time.monotonic()-started,2),flush=True)
    (OUT/'manifest.json').write_text(json.dumps(dict(model='frappuccino/dialogs-ru-vits2',
        revision='af7eabc15d087fce701de7261190ccb747c3bc7a',checkpoint_sha256=digest,
        clips=records),ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
