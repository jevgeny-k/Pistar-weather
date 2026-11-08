"""One Xenia notice outside the fixed 1604-entry weather vocabulary."""
from array import array
import hashlib
import html
import json
import math
from pathlib import Path
import sys
import wave
from catalog import ROOT,OUT,PROFILE
sys.path.insert(0,str(ROOT/'work/pistar-weather'))
from silero_compare import MODEL

def main():
    import torch
    import torch.nn.functional as F
    torch.set_num_threads(2)
    text='Свежие погодные данные недоступны. Повторяю предыдущую сводку.'
    model=torch.package.PackageImporter(str(MODEL)).load_pickle('tts_models','model');model.to(torch.device('cpu'))
    package=model.packages[model.speaker_to_package[PROFILE['speaker']]]
    package.rate2value['fast']=PROFILE['rate'];package.pitch2value['high']=PROFILE['pitch']
    audio=model.apply_tts(ssml_text='<speak><prosody rate="fast" pitch="high">'+html.escape(text)+'</prosody></speak>',speaker=PROFILE['speaker'],sample_rate=48000,put_accent=True,put_yo=True).detach().cpu().float()
    n=audio.numel();pad=2048;padded=F.pad(audio,(pad,pad));freq=torch.fft.rfftfreq(padded.numel(),d=1/48000)
    lp=torch.where(freq<3000,torch.ones_like(freq),torch.where(freq>3500,torch.zeros_like(freq),.5*(1+torch.cos(math.pi*(freq-3000)/500))))
    hp=torch.where(freq<50,torch.zeros_like(freq),torch.where(freq>100,torch.ones_like(freq),.5*(1-torch.cos(math.pi*(freq-50)/50))))
    audio=torch.fft.irfft(torch.fft.rfft(padded)*lp*hp,n=padded.numel())[pad:pad+n:6]
    active=torch.where(audio.abs()>float(audio.abs().max())*.006)[0]
    audio=audio[max(0,int(active[0])-240):min(audio.numel(),int(active[-1])+401)]
    audio*=.70/float(audio.abs().max());edge=min(40,audio.numel()//2)
    audio[:edge]*=torch.linspace(0,1,edge);audio[-edge:]*=torch.linspace(1,0,edge)
    pcm=array('h',(audio*32767).round().clamp(-32767,32767).to(torch.int16).tolist())
    path=OUT/'fallback-notice.wav'
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(pcm.tobytes())
    metadata={'text':text,'profile':PROFILE,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'seconds':len(pcm)/8000}
    (OUT/'fallback-notice.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    print('NOTICE_READY',metadata['seconds'],metadata['sha256'],flush=True)

if __name__=='__main__':main()
