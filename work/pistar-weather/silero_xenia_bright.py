"""A gentle upbeat Xenia audition. Existing default voices remain unchanged."""
from silero_compare import MODEL, OUT, download
import argparse
import hashlib
import json
import wave
from array import array


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pitch',type=float,default=1.04)
    parser.add_argument('--name',default='04-xenia-bright')
    args=parser.parse_args()
    if not .75<=args.pitch<=1.25 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name):
        raise ValueError('Invalid audition profile')
    download()
    import torch
    torch.set_num_threads(2)
    model=torch.package.PackageImporter(str(MODEL)).load_pickle('tts_models','model')
    model.to(torch.device('cpu'))
    # The published SSML presets are coarse (+20% rate/+15% pitch). Refine
    # their in-memory mapping for a subtler change, without changing weights.
    package=model.packages[model.speaker_to_package['xenia']]
    package.rate2value['fast']=1.08
    package.pitch2value['high']=args.pitch
    ssml=('''<speak><prosody rate="fast" pitch="high">'''
          '''Добрый вечер!<break time="150ms"/>'''
          '''Это прогноз погоды для Риги.<break time="120ms"/>'''
          '''Надеюсь, теперь меня слышно хорошо!<break time="120ms"/>'''
          '''Желаю вам приятного вечера!</prosody></speak>''')
    audio=model.apply_tts(ssml_text=ssml,speaker='xenia',sample_rate=48000,
                          put_accent=True,put_yo=True).detach().cpu().float()
    if not torch.isfinite(audio).all() or float(audio.abs().max())<.001:
        raise ValueError('Invalid generated audio')
    audio=audio*(.85/float(audio.abs().max()))
    pcm=array('h',(audio*32767).round().clamp(-32767,32767).to(torch.int16).tolist())
    path=OUT/(args.name+'.wav')
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(pcm.tobytes())
    meta=dict(speaker='xenia',rate=1.08,pitch=args.pitch,ssml=ssml,
              seconds=len(pcm)/48000,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (OUT/(args.name+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(meta,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
