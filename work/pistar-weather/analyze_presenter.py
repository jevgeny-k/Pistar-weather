"""Measure pitch and energy pauses in a local, attributed broadcast excerpt."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('audio',type=Path)
    parser.add_argument('--start',type=float,default=40)
    parser.add_argument('--duration',type=float,default=60)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    import librosa
    import numpy as np
    sample_rate=16000
    audio,_=librosa.load(args.audio,sr=sample_rate,mono=True,offset=args.start,duration=args.duration)
    if len(audio)<sample_rate*10:raise ValueError('Reference is too short for this analysis')
    f0,voiced,probability=librosa.pyin(audio,fmin=80,fmax=450,sr=sample_rate,
                                     frame_length=1024,hop_length=160)
    pitch=f0[voiced & (probability>=.6) & np.isfinite(f0)]
    if len(pitch)<30:raise ValueError('Insufficient confident voiced pitch frames')
    rms=librosa.feature.rms(y=audio,frame_length=1024,hop_length=160)[0]
    quiet=rms < rms.max()*10**(-25/20)
    boundaries=np.flatnonzero(np.diff(np.r_[False,quiet,False]))
    pauses=[(end-start)*.01 for start,end in zip(boundaries[::2],boundaries[1::2]) if (end-start)*.01>=.12]
    percentiles=np.percentile(pitch,[10,25,50,75,90])
    result=dict(source_audio_sha256=hashlib.sha256(args.audio.read_bytes()).hexdigest(),
                offset_seconds=args.start,analyzed_seconds=len(audio)/sample_rate,
                pitch_percentiles_hz=dict(zip(('p10','p25','median','p75','p90'),map(float,percentiles))),
                pitch_p10_p90_semitones=float(12*np.log2(percentiles[-1]/percentiles[0])),
                confident_pitch_frames=int(len(pitch)),energy_pause_count=len(pauses),
                energy_pause_median_seconds=float(np.median(pauses)) if pauses else None,
                energy_pauses_seconds=pauses,
                method='pYIN, 16 kHz, 10 ms hop, voiced probability >=0.6; energy pauses >=120 ms at -25 dB',
                limitation='Broadcast background music can bias pitch and energy-pause estimates.')
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
