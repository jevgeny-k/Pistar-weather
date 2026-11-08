"""Manual standalone entry point. Prevent overlapping bulletins; no timer."""
import argparse
import fcntl
from pathlib import Path
import tempfile
from runtime import prepare
from bulletin_cache import generate,store

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','now'])
    args=parser.parse_args()
    base=Path(__file__).resolve().parent
    with open('/run/pistar-weather/autonomous.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix='pistar-autonomous-') as tmp:
            cache=Path('/run/pistar-weather/last-bulletin.zip')
            cached=generate(Path(tmp),base,cache,prepare)
            print((Path(tmp)/'bulletin.txt').read_text(encoding='utf-8'),flush=True)
            if args.action=='now':
                from play import play
                play(tmp,cached=cached)
                if not cached:store(tmp,cache)
            else:print('PREPARE_ONLY_OK; temporary audio removed; no transmission',flush=True)

if __name__=='__main__':main()
