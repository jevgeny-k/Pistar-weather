"""Render a coherent Baya forecast audition with model-level word emphasis."""
from array import array
import hashlib
import json
import wave

from silero_compare import ROOT,MODEL,download

SSML=('''<speak><prosody rate="medium" pitch="medium">'''
      '''Добрый день!<break time="180ms"/>'''
      '''Это пробный прогноз погоды для Риги.<break time="200ms"/>'''
      '''Сегодня **пасмурно**, температура — около **семи** градусов.<break time="180ms"/>'''
      '''Ветер **порывистый**, поэтому на улице будет ощущаться прохладнее.<break time="230ms"/>'''
      '''Если собираетесь на прогулку — одевайтесь **теплее**.<break time="180ms"/>'''
      '''И хорошего вам дня!</prosody></speak>''')


def main():
    download()
    import torch
    torch.set_num_threads(2)
    model=torch.package.PackageImporter(str(MODEL)).load_pickle('tts_models','model')
    model.to(torch.device('cpu'))
    audio=model.apply_tts(ssml_text=SSML,speaker='baya',sample_rate=48000,
                          put_accent=True,put_yo=True,intensity=2).detach().cpu().float()
    if not torch.isfinite(audio).all() or float(audio.abs().max())<.001:
        raise ValueError('Invalid presenter audition')
    if not 1<audio.numel()/48000<35:raise ValueError('Audition outside duration limit')
    audio*=.70/float(audio.abs().max())
    pcm=array('h',(audio*32767).round().clamp(-32767,32767).to(torch.int16).tolist())
    out=ROOT/'outputs/baya-presenter'
    out.mkdir(exist_ok=True)
    path=out/'baya-presenter.wav'
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(48000)
        wav.writeframes(pcm.tobytes())
    with MODEL.open('rb') as source:model_sha=hashlib.file_digest(source,'sha256').hexdigest()
    record=dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                seconds=len(pcm)/48000,speaker='baya',ssml=SSML,intensity=2)
    (out/'manifest.json').write_text(json.dumps(dict(model='Silero v5_6_ru',
        model_sha256=model_sha,clips=[record]),ensure_ascii=False,indent=2),encoding='utf-8')
    print('BAYA_PRESENTER_READY',round(record['seconds'],2),'seconds',flush=True)


if __name__=='__main__':main()
