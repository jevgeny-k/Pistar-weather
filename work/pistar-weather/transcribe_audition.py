"""Check generated audition intelligibility with a cached local ASR model."""
import argparse
import json
import math
from pathlib import Path
import re


def word_errors(expected,actual):
    previous=list(range(len(actual)+1))
    for i,word in enumerate(expected,1):
        current=[i]
        for j,other in enumerate(actual,1):
            current.append(min(previous[j]+1,current[-1]+1,previous[j-1]+(word!=other)))
        previous=current
    return previous[-1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    args=parser.parse_args()
    from faster_whisper import WhisperModel
    import soundfile as sf
    from scipy.signal import resample_poly
    root=Path(__file__).resolve().parents[2]
    model=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=2,
                      download_root=str(root/'work/asr-cache'))
    manifest=json.loads((args.directory/'manifest.json').read_text(encoding='utf-8'))
    report=[]
    for clip in manifest['clips']:
        name=clip['file']
        if Path(name).name!=name:raise ValueError('Invalid sample path')
        audio,sr=sf.read(args.directory/name,dtype='float32')
        if audio.ndim>1:audio=audio.mean(axis=1)
        divisor=math.gcd(sr,16000)
        audio=resample_poly(audio,16000//divisor,sr//divisor)
        segments,_=model.transcribe(audio,language='ru',beam_size=3)
        text=' '.join(segment.text for segment in segments).strip()
        normalize=lambda value:re.findall(r'\w+',value.lower().replace('ё','е'))
        expected=normalize(clip['text']);actual=normalize(text)
        rate=word_errors(expected,actual)/max(1,len(expected))
        report.append(dict(file=name,recognized_text=text,word_error_rate=rate,
                           passed=bool(expected) and rate<=.35))
    (args.directory/'asr-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
    if not all(row['passed'] for row in report):raise SystemExit('Audition intelligibility check failed')


if __name__=='__main__':main()
