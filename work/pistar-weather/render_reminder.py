"""Prepare a static Baya reminder once; no model is needed on the hotspot."""
from array import array
import hashlib
import json
from pathlib import Path
import wave
from silero_compare import ROOT,MODEL,download


def main():
    download()
    import torch
    torch.set_num_threads(2)
    model=torch.package.PackageImporter(str(MODEL)).load_pickle('tts_models','model')
    model.to(torch.device('cpu'))
    package=model.packages[model.speaker_to_package['baya']]
    package.rate2value['fast']=1.0
    package.pitch2value['high']=1.0
    text='Не забудь покормить котиков, котики голодают.'
    audio=model.apply_tts(ssml_text='<speak><prosody rate="fast" pitch="high">'+text+
                          '</prosody></speak>',speaker='baya',sample_rate=48000,
                          put_accent=True,put_yo=True).detach().cpu().float()
    if not torch.isfinite(audio).all() or not 1<audio.numel()/48000<30:
        raise ValueError('Invalid reminder audio')
    peak=float(audio.abs().max())
    if peak<.001:raise ValueError('Silent reminder audio')
    audio*=.70/peak
    pcm=array('h',(audio*32767).round().clamp(-32767,32767).to(torch.int16).tolist())
    out=ROOT/'outputs/cat-reminder';out.mkdir(parents=True,exist_ok=True)
    path=out/'reminder.wav'
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(48000);wav.writeframes(pcm.tobytes())
    manifest=dict(schema=1,speaker='baya',model='silero-v5_6_ru',text=text,
                  clips=[dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              seconds=len(pcm)/48000)])
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('REMINDER_AUDIO_READY',round(len(pcm)/48000,2),'seconds',flush=True)


if __name__=='__main__':main()
