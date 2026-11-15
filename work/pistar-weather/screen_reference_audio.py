"""Screen a local speech reference for music and non-speech using YAMNet."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('audio',type=Path)
    parser.add_argument('--start',type=float,default=0)
    parser.add_argument('--duration',type=float,default=10)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    import librosa
    import numpy as np
    import onnxruntime as ort
    root=Path(__file__).resolve().parents[2]
    model=root/'work/yamnet/yamnet.onnx'
    labels=[r['display_name'] for r in csv.DictReader(
        (model.parent/'yamnet_class_map.csv').open(encoding='utf-8'))]
    audio,_=librosa.load(args.audio,sr=16000,mono=True,offset=args.start,duration=args.duration)
    options=ort.SessionOptions();options.intra_op_num_threads=2
    session=ort.InferenceSession(str(model),sess_options=options,providers=['CPUExecutionProvider'])
    scores=session.run(['output_0'],{'waveform':audio.astype(np.float32)})[0]
    mean=scores.mean(axis=0)
    result=dict(audio_sha256=hashlib.sha256(args.audio.read_bytes()).hexdigest(),
        start=args.start,seconds=len(audio)/16000,
        model_revision='f25b741c2f0bdc6d7e6db24b5fddda23347dbafd',
        model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
        top_classes=[dict(label=labels[i],mean=float(mean[i])) for i in np.argsort(mean)[-8:][::-1]],
        speech_mean=float(mean[labels.index('Speech')]),
        music_mean=float(mean[labels.index('Music')]),
        music_max=float(scores[:,labels.index('Music')].max()),
        limitation='Classifier scores are screening evidence, not proof of audible quality or absence of background sound.')
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
