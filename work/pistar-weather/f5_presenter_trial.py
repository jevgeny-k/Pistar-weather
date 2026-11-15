"""Render a clearly labelled synthetic forecast conditioned on an attributed reference."""
import gc
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[2]
os.environ['HF_HOME']=str(ROOT/'work/hf-cache')
os.environ['HF_HUB_DISABLE_XET']='1'
os.environ['WANDB_MODE']='disabled'
os.environ['OMP_NUM_THREADS']='2'
TEXT=('Это пробный прогноз для Риги. Сегодня пасмурно, около семи градусов тепла. '
      'Одевайтесь теплее!')
STRESSED_TEXT=('+Это пр+обный прогн+оз для Р+иги. Сег+одня п+асмурно, +около сем+и гр+адусов тепл+а. '
               'Одев+айтесь тепл+ее!')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reference',type=Path,default=ROOT/'work/presenter-reference')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/f5-presenter')
    parser.add_argument('--int8',action='store_true')
    args=parser.parse_args()
    reference=args.reference
    reference_info=json.loads((reference/'transcription.json').read_text(encoding='utf-8'))
    screening=json.loads((reference/'screening.json').read_text(encoding='utf-8'))
    reference_hash=hashlib.sha256((reference/'conditioning.wav').read_bytes()).hexdigest()
    if screening['audio_sha256']!=reference_hash or screening['start']!=0:
        raise ValueError('Screening must match the exact conditioning file')
    if screening['music_mean']>.02 or screening['music_max']>.10 or screening['speech_mean']<.5:
        raise ValueError('Reference failed the speech/music screening gate')
    source_url=reference_info.get('source_url')
    if not source_url:raise ValueError('An attributed reference source is required')
    import imageio_ffmpeg
    from pydub import AudioSegment
    AudioSegment.converter=imageio_ffmpeg.get_ffmpeg_exe()
    import torch
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    from f5_tts.api import F5TTS
    model_dir=ROOT/'work/f5-russian'
    checkpoint=model_dir/'model.safetensors'
    if checkpoint.stat().st_size!=1348435761:raise ValueError('Unexpected F5 checkpoint size')
    print('F5_LOADING_CPU_MODEL',flush=True)
    engine=F5TTS(model='F5TTS_v1_Base',ckpt_file=str(checkpoint),
                 vocab_file=str(model_dir/'vocab.txt'),device='cpu',
                 hf_cache_dir=str(ROOT/'work/hf-cache'))
    if args.int8:
        print('F5_QUANTIZING_LINEAR_LAYERS_FOR_CPU',flush=True)
        engine.ema_model=torch.ao.quantization.quantize_dynamic(
            engine.ema_model,{torch.nn.Linear},dtype=torch.qint8,inplace=True)
    gc.collect()
    forward=engine.ema_model.transformer.forward
    steps=0
    def report_forward(*positional,**keywords):
        nonlocal steps
        result=forward(*positional,**keywords)
        steps+=1
        if steps%4==0:print('F5_FLOW_STEPS_COMPLETED',steps,flush=True)
        return result
    engine.ema_model.transformer.forward=report_forward
    ref_text=(reference/'conditioning.txt').read_text(encoding='utf-8').strip()
    started=time.monotonic()
    print('F5_RENDERING_SYNTHETIC_FORECAST',flush=True)
    audio,sr,_=engine.infer(ref_file=str(reference/'conditioning.wav'),ref_text=ref_text,
                            gen_text=STRESSED_TEXT,nfe_step=32,speed=1.0,seed=2026)
    import numpy as np
    import soundfile as sf
    audio=np.asarray(audio,dtype=np.float32).reshape(-1)
    if not np.isfinite(audio).all() or not 1<len(audio)/sr<35:
        raise ValueError('Invalid F5 output')
    peak=float(np.max(np.abs(audio)))
    if peak<.001:raise ValueError('Silent F5 output')
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    path=out/'synthetic-presenter.wav'
    sf.write(path,audio*(.70/peak),sr,subtype='PCM_16')
    record=dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                seconds=len(audio)/sr,text=TEXT,inference_text=STRESSED_TEXT)
    manifest=dict(model='Misha24-10/F5-TTS_RUSSIAN F5TTS_v1_Base_v2',
        model_revision='ea166adeae4c80ec5ee423a671e2bdb83906cf84',
        checkpoint_sha256='f11e788c8d2d86b8d6e3e2e7a12c583932d2494b015b544793c1924360b474d3',
        reference_url=source_url,
        reference_excerpt_sha256=hashlib.sha256((reference/'conditioning.wav').read_bytes()).hexdigest(),
        synthetic=True,cpu_linear_quantization='int8' if args.int8 else 'none',nfe_steps=32,seed=2026,
        clips=[record],generation_seconds=round(time.monotonic()-started,2))
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('F5_PRESENTER_READY',round(record['seconds'],2),'seconds',flush=True)


if __name__=='__main__':main()
