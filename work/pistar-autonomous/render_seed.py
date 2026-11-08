"""Generate only the seed bank, then audition the Pi-portable assembly."""
from pathlib import Path
import hashlib
import html
import json
import math
import sys
import wave
from array import array
from catalog import ROOT,OUT,PROFILE
sys.path.insert(0,str(ROOT/'work/pistar-weather'))
from silero_compare import MODEL,download
from assemble import assemble


def main():
    catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
    (OUT/'bank').mkdir(exist_ok=True)
    download()
    import torch
    import torch.nn.functional as F
    torch.set_num_threads(2)
    model=torch.package.PackageImporter(str(MODEL)).load_pickle('tts_models','model');model.to(torch.device('cpu'))
    package=model.packages[model.speaker_to_package[PROFILE['speaker']]]
    package.rate2value['fast']=PROFILE['rate'];package.pitch2value['high']=PROFILE['pitch']
    manifest_path=OUT/'bank-manifest.json'
    previous=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    records=previous.get('generated',{}) if previous.get('profile')==PROFILE else {}
    keys=list(catalog['entries']) if '--all' in sys.argv else catalog['pilot_seed_ids']
    def checkpoint():
        manifest=dict(schema=1,profile=PROFILE,generated=records,total_catalogue=len(catalog['entries']),
                      status='complete' if len(records)==len(catalog['entries']) else 'partial; resumable')
        temporary=manifest_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(manifest_path)
    for key in keys:
        e=catalog['entries'][key]
        existing=records.get(key);path=OUT/e['wav']
        if existing and existing['text_sha256']==e['text_sha256'] and path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==existing['sha256']:
            continue
        ssml='<speak><prosody rate="fast" pitch="high">'+html.escape(e['text'])+'</prosody></speak>'
        audio=model.apply_tts(ssml_text=ssml,speaker=PROFILE['speaker'],sample_rate=48000,
                             put_accent=True,put_yo=True).detach().cpu().float()
        if not torch.isfinite(audio).all() or float(audio.abs().max())<.001:raise ValueError('Bad synthesis '+key)
        # Band-limit BEFORE integer downsampling. Smooth transitions avoid a
        # sharp spectral cutoff, and zero padding avoids circular edge bleed.
        n=audio.numel();pad=2048
        padded=F.pad(audio,(pad,pad))
        freq=torch.fft.rfftfreq(padded.numel(),d=1/48000)
        lp=torch.where(freq<3000,torch.ones_like(freq),torch.where(freq>3500,torch.zeros_like(freq),.5*(1+torch.cos(math.pi*(freq-3000)/500))))
        hp=torch.where(freq<50,torch.zeros_like(freq),torch.where(freq>100,torch.ones_like(freq),.5*(1-torch.cos(math.pi*(freq-50)/50))))
        filtered=torch.fft.irfft(torch.fft.rfft(padded)*lp*hp,n=padded.numel())[pad:pad+n]
        audio=filtered[::6]
        threshold=float(audio.abs().max())*.006
        active=torch.where(audio.abs()>threshold)[0]
        if not active.numel():raise ValueError('Silent phrase '+key)
        start=max(0,int(active[0])-240);end=min(audio.numel(),int(active[-1])+401)
        audio=audio[start:end]
        audio*=.70/float(audio.abs().max())
        edge=min(40,audio.numel()//2)
        audio[:edge]*=torch.linspace(0,1,edge);audio[-edge:]*=torch.linspace(1,0,edge)
        pcm=array('h',(audio*32767).round().clamp(-32767,32767).to(torch.int16).tolist())
        path=OUT/e['wav']
        with wave.open(str(path),'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(pcm.tobytes())
        records[key]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),text_sha256=e['text_sha256'],
                          frames=len(pcm),seconds=len(pcm)/8000,bytes=path.stat().st_size)
        checkpoint()
        print('Prepared',key,round(len(pcm)/8000,2),'seconds',flush=True)
    checkpoint()
    seconds=assemble(OUT,OUT/'pilot-plan.json',OUT/'pilot-assembled.wav')
    print('SEED_READY',len(records),'phrases; pilot',round(seconds,1),'seconds',flush=True)


if __name__=='__main__':main()
