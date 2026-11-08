"""Validate, encode and play one local private voice audition."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from array import array
sys.path.insert(0,'/opt/pistar-weather')
from weather import BASE,STATE,build_call,request

if len(sys.argv)!=3:raise ValueError('Expected WAV basename and SHA256')
name=sys.argv[1]
if Path(name).name!=name or not name.endswith('.wav'):raise ValueError('Bad basename')
wav=STATE/name
if hashlib.sha256(wav.read_bytes()).hexdigest()!=sys.argv[2]:raise ValueError('SHA256 mismatch')
raw=wav.with_suffix('.raw');ambe=wav.with_suffix('.ambe72');decoded=wav.with_suffix('.decoded.raw')
subprocess.run(['sox',str(wav),'-t','raw','-r','8000','-e','signed-integer','-b','16','-c','1','-L',str(raw),
    'gain','-6','highpass','100','lowpass','3400','gain','-n','-3','pad','0.5','0.5'],check=True)
subprocess.run([str(BASE/'encode'),str(raw),str(ambe)],check=True)
subprocess.run([str(BASE/'encode'),'-d',str(ambe),str(decoded)],check=True)
s=array('h');s.frombytes(decoded.read_bytes())
peak=max(abs(v) for v in s)
print('Decoded audio seconds=',len(s)/8000,'peak=',peak,flush=True)
assert len(s)>8000 and 1000<peak<32767
packets=wav.with_suffix('.dmr55');packets.write_bytes(build_call(ambe.read_bytes()))
result=request({'op':'play','file':str(packets)})
print(json.dumps(result),flush=True)
if not result.get('ok'):sys.exit(1)
