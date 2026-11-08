import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave
import zipfile
import bulletin_cache as cache
from runtime import WeatherUnavailable

def wav(path,seconds=1):
    with wave.open(str(path),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(8000);audio.writeframes(b'\xe8\x03'*(int(seconds*8000)))

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'fresh';self.base=self.root/'base';self.out=self.root/'out'
        for folder in [self.source,self.base,self.out]:folder.mkdir()
        wav(self.source/'part-1.wav');wav(self.base/'fallback-notice.wav')
        notice=self.base/'fallback-notice.wav';(self.base/'fallback-notice.json').write_text(json.dumps({'text':'Previous report notice.','sha256':hashlib.sha256(notice.read_bytes()).hexdigest()}))
        self.manifest={'generated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'clips':[{'file':'part-1.wav','seconds':1,'sha256':hashlib.sha256((self.source/'part-1.wav').read_bytes()).hexdigest()}]}
        (self.source/'manifest.json').write_text(json.dumps(self.manifest));(self.source/'bulletin.txt').write_text('Original report.')
        self.archive=self.root/'last.zip';cache.store(self.source,self.archive)
    def tearDown(self):self.temp.cleanup()
    def test_fallback_preserves_old_time_and_includes_notice(self):
        def unavailable(*args):raise WeatherUnavailable('HTTP 503')
        self.assertTrue(cache.generate(self.out,self.base,self.archive,unavailable))
        manifest=json.loads((self.out/'manifest.json').read_text())
        self.assertEqual(manifest['generated_utc'],self.manifest['generated_utc'])
        self.assertEqual(manifest['fallback']['original_generated_utc'],self.manifest['generated_utc'])
        self.assertTrue((self.out/'bulletin.txt').read_text().startswith('Previous report notice.'))
        self.assertEqual(manifest['clips'][0]['seconds'],2.2)
        with self.assertRaisesRegex(ValueError,'renew'):cache.store(self.out,self.archive)
    def test_partial_cache_update_preserves_previous(self):
        previous=self.archive.read_bytes()
        with patch.object(zipfile.ZipFile,'write',side_effect=OSError('out of space')):
            with self.assertRaises(OSError):cache.store(self.source,self.archive)
        self.assertEqual(self.archive.read_bytes(),previous)
    def test_bad_cached_audio_rejected(self):
        with zipfile.ZipFile(self.archive) as z:items={n:z.read(n) for n in z.namelist()}
        items['part-1.wav']=b'damaged'
        with zipfile.ZipFile(self.archive,'w') as z:
            for name,data in items.items():z.writestr(name,data)
        with self.assertRaisesRegex(ValueError,'checksum'):cache.restore(self.archive,self.out,self.base,'503')
    def test_nonweather_bug_not_hidden_by_fallback(self):
        def broken(*args):raise ValueError('programming problem')
        with self.assertRaisesRegex(ValueError,'programming'):cache.generate(self.out,self.base,self.archive,broken)
    def test_missing_cache_is_explicit(self):
        self.archive.unlink()
        with self.assertRaisesRegex(FileNotFoundError,'No previous'):cache.restore(self.archive,self.out,self.base,'503')
    def test_old_report_can_be_replayed_without_refreshing_timestamp(self):
        with zipfile.ZipFile(self.archive) as z:items={n:z.read(n) for n in z.namelist()}
        manifest=json.loads(items['manifest.json']);old=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=3)).isoformat();manifest['generated_utc']=old;items['manifest.json']=json.dumps(manifest).encode()
        with zipfile.ZipFile(self.archive,'w') as z:
            for name,data in items.items():z.writestr(name,data)
        cache.restore(self.archive,self.out,self.base,'503')
        self.assertEqual(json.loads((self.out/'manifest.json').read_text())['generated_utc'],old)

if __name__=='__main__':unittest.main()
