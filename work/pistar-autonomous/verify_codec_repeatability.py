"""Run the real playback codec twice with all relay access stubbed out."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import play

def verify(directory,cached=False,player=play):
    directory=Path(directory);manifest=json.loads((directory/'manifest.json').read_text())
    original=(player.STATE,player.request,player.time.sleep)
    results=[]
    print('OFFLINE_CODEC_REPEATABILITY_NO_RF',flush=True)
    try:
        with tempfile.TemporaryDirectory(prefix='codec-repeatability-') as tmp:
            base=Path(tmp);packets=base/'packets';packets.mkdir();player.STATE=packets;player.time.sleep=lambda _:None
            for attempt in range(2):
                out=base/str(attempt);out.mkdir();(out/'manifest.json').write_text(json.dumps(manifest))
                for clip in manifest['clips']:
                    name=clip['file']
                    if Path(name).name!=name or not name.endswith('.wav'):raise ValueError('Invalid clip path')
                    (out/name).write_bytes((directory/name).read_bytes())
                calls=[]
                def fake(message,**kwargs):
                    operation=message['op'];calls.append(operation)
                    if operation=='status':return {'connected':True,'host':['offline-test',1],'weather_priority':True}
                    if operation=='begin_bulletin':return {'ok':True,'token':'synthetic-offline-test'}
                    if operation not in {'play','end_bulletin'}:raise ValueError('Unexpected offline request')
                    return {'ok':True,'offline_no_rf':True}
                player.request=fake;player.play(out,cached=cached)
                if calls.count('begin_bulletin')!=1 or calls[-1]!='end_bulletin':raise ValueError('Priority release was not exercised')
                record={}
                for clip in manifest['clips']:
                    stem=Path(clip['file']).stem
                    for suffix in ('.raw','.ambe72','.decoded.raw'):
                        record[stem+suffix]=hashlib.sha256((out/(stem+suffix)).read_bytes()).hexdigest()
                results.append(record)
    finally:player.STATE,player.request,player.time.sleep=original
    if results[0]!=results[1]:raise ValueError('Identical input produced different codec artifacts')
    print('CODEC_REPEATABILITY_VERIFIED_NO_RF',len(manifest['clips']),'parts',flush=True)
    return results[0]

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('prepared_directory');parser.add_argument('--cached',action='store_true')
    args=parser.parse_args();verify(args.prepared_directory,args.cached)
