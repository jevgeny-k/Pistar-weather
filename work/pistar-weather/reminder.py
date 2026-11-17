"""Play a verified static reminder with the selected weather voice effects."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true',help='Run native codec verification without RF')
    parser.add_argument('--assets',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    live=Path('/opt/pistar-weather/autonomous-v1')
    sys.path.insert(0,str(live))
    import play
    # Share the complete weather/maintenance exclusion lock, without truncating it.
    with open('/run/pistar-weather/autonomous.lock','r+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        source=json.loads((args.assets/'manifest.json').read_text(encoding='utf-8'))
        if len(source['clips'])!=1:raise ValueError('A reminder must contain exactly one clip')
        clip=source['clips'][0];name=clip['file']
        if Path(name).name!=name or not name.endswith('.wav'):raise ValueError('Invalid reminder path')
        wav=args.assets/name
        if hashlib.sha256(wav.read_bytes()).hexdigest()!=clip['sha256']:
            raise ValueError('Reminder audio checksum mismatch')
        with tempfile.TemporaryDirectory(prefix='reminder-',dir='/run/pistar-weather') as temporary:
            out=Path(temporary);target=out/'reminder.wav'
            subprocess.run(['sox','-D',str(wav),'-r','8000','-e','signed-integer',
                            '-b','16','-c','1',str(target)],check=True)
            manifest=dict(generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                          clips=[dict(file=target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest())])
            (out/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            if args.check:
                from verify_codec_repeatability import verify
                verify(out,player=play)
                print('REMINDER_CHECK_PASSED_NO_RF',flush=True)
            else:
                play.play(out)
                print('REMINDER_DELIVERED_TO_LOCAL_HOST',flush=True)


if __name__=='__main__':main()
