"""Check and transmit two labelled voice samples using the local private relay."""
import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    parser.add_argument('--now',action='store_true')
    args=parser.parse_args()
    source=args.directory
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    live=Path('/opt/pistar-weather/autonomous-v1')
    sys.path.insert(0,str(live))
    from verify_codec_repeatability import verify
    with open('/run/pistar-weather/autonomous.lock','r+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with tempfile.TemporaryDirectory(prefix='dialogs-audition-') as temporary:
            out=Path(temporary)
            # An isolated player keeps the selected Baya effects out of the comparison.
            player_path=out/'audition_player.py'
            shutil.copy2(live/'play.py',player_path)
            spec=importlib.util.spec_from_file_location('audition_player',player_path)
            player=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(player)
            clips=[]
            for clip in manifest['clips']:
                name=clip['file']
                if Path(name).name!=name or not name.endswith('.wav'):
                    raise ValueError('Invalid sample path')
                wav=source/name
                if hashlib.sha256(wav.read_bytes()).hexdigest()!=clip['sha256']:
                    raise ValueError('Sample checksum mismatch')
                target=out/name
                subprocess.run(['sox','-D',str(wav),'-r','8000','-e','signed-integer',
                                '-b','16','-c','1',str(target)],check=True)
                with wave.open(str(target),'rb') as audio:
                    seconds=audio.getnframes()/8000
                if not 1<seconds<35:raise ValueError('Sample duration outside range')
                clips.append(dict(file=name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),seconds=seconds))
            report=dict(generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),clips=clips)
            (out/'manifest.json').write_text(json.dumps(report))
            verify(out,player=player)
            if args.now:
                player.play(out)
            else:
                print('DIALOGS_CHECK_PASSED_NO_RF',flush=True)


if __name__=='__main__':main()
