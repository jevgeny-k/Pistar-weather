"""Generate three comparison clips locally; no changes to the working Pi TTS."""
from pathlib import Path
import hashlib
import json
import os
import time
import urllib.request
import wave

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'work'/'silero'
OUT=ROOT/'outputs'/'silero-voices'
WORK.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
os.environ['TORCH_HOME']=str(WORK/'torch-cache')
os.environ['XDG_CACHE_HOME']=str(WORK/'cache')
MODEL=WORK/'v5_6_ru.pt'
URL='https://models.silero.ai/models/tts/ru/v5_6_ru.pt'


def download():
    if MODEL.exists(): return
    print('Downloading official Silero v5_6_ru model',flush=True)
    temp=MODEL.with_suffix('.download')
    with urllib.request.urlopen(URL,timeout=60) as src, temp.open('wb') as dst:
        while chunk:=src.read(1024*1024): dst.write(chunk)
    temp.replace(MODEL)


def main():
    download()
    import torch
    torch.set_num_threads(2)
    print('Torch',torch.__version__,'model SHA256',hashlib.sha256(MODEL.read_bytes()).hexdigest(),flush=True)
    model=torch.package.PackageImporter(str(MODEL)).load_pickle('tts_models','model')
    model.to(torch.device('cpu'))
    print('Model ready; speakers:',model.speakers,flush=True)
    outputs=[]
    for n,speaker in enumerate(['baya','kseniya','xenia'],1):
        # Same content for comparison; do not announce callsign or ending.
        label=['один','два','три'][n-1]
        text=(f'Голос номер {label}. Добрый вечер! Это прогноз погоды для Риги. '
              'Надеюсь, теперь меня слышно хорошо. Желаю вам приятного вечера.')
        start=time.monotonic()
        audio=model.apply_tts(text=text,speaker=speaker,sample_rate=48000,
                              put_accent=True,put_yo=True)
        audio=audio.detach().cpu().float()
        if not torch.isfinite(audio).all(): raise ValueError('Non-finite audio')
        peak=float(audio.abs().max())
        if peak<0.001: raise ValueError('Empty audio')
        audio=audio*(0.85/peak)
        # Avoid NumPy/SciPy dependency: torch's integer list -> Python array.
        from array import array
        pcm=array('h',(audio*32767).round().clamp(-32767,32767).to(torch.int16).tolist())
        path=OUT/f'{n:02}-{speaker}.wav'
        with wave.open(str(path),'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000); w.writeframes(pcm.tobytes())
        info=dict(number=n,speaker=speaker,file=str(path),text=text,seconds=len(pcm)/48000)
        outputs.append(info)
        print(json.dumps(info,ensure_ascii=False),'generation_seconds=',round(time.monotonic()-start,1),flush=True)
    (OUT/'manifest.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__': main()
