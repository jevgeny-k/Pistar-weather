"""Transcribe a local reference and extract a short, word-aligned conditioning clip."""
import json
from pathlib import Path
import argparse


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--start',type=float,default=40)
    parser.add_argument('--duration',type=float,default=60)
    parser.add_argument('--asr-model',default='base')
    args=parser.parse_args()
    import librosa
    import soundfile as sf
    from faster_whisper import WhisperModel
    root=Path(__file__).resolve().parents[2]
    base=root/'work/presenter-reference'
    audio,sr=sf.read(base/'polyakova.wav',dtype='float32')
    sample=librosa.resample(audio[int(args.start*sr):int((args.start+args.duration)*sr)],orig_sr=sr,target_sr=16000)
    model=WhisperModel(args.asr_model,device='cpu',compute_type='int8',cpu_threads=2,
                       download_root=str(root/'work/asr-cache'))
    segments,info=model.transcribe(sample,language='ru',beam_size=3,word_timestamps=True,vad_filter=True)
    rows=[];words=[]
    for segment in segments:
        rows.append(dict(start=segment.start,end=segment.end,text=segment.text,
                         avg_logprob=segment.avg_logprob))
        words.extend(dict(start=w.start,end=w.end,word=w.word,probability=w.probability)
                     for w in (segment.words or []))
    if len(words)<20:raise ValueError('Insufficient reference words')
    selected=words[:20]
    start=max(0,args.start+selected[0]['start']-.05)
    end=min(len(audio)/sr,args.start+selected[-1]['end']+.10)
    if not 3<end-start<14:raise ValueError('Reference excerpt outside conditioning range')
    text=''.join(w['word'] for w in selected).strip()
    sf.write(base/'conditioning.wav',audio[int(start*sr):int(end*sr)],sr,subtype='PCM_16')
    result=dict(analysis_offset_seconds=args.start,segments=rows,words=words,
                words_per_minute=len(words)*60/(len(sample)/16000),conditioning_start=start,conditioning_end=end,
                conditioning_text=text,conditioning_word_count=len(selected),
                conditioning_mean_probability=sum(w['probability'] for w in selected)/len(selected))
    (base/'transcription.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (base/'conditioning.txt').write_text(text,encoding='utf-8')
    print('REFERENCE_WORDS_PER_MINUTE',round(result['words_per_minute'],1),
          'CLIP_SECONDS',round(end-start,2),flush=True)
    print('REFERENCE_TRANSCRIPT_READY',len(selected),'words',flush=True)


if __name__=='__main__':main()
