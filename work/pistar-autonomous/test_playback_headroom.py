"""Keep codec saturation retries bounded and retain the strict audio guard."""
from array import array
import importlib.util
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock


def load_subject():
    spec=importlib.util.spec_from_file_location('headroom_subject',Path(__file__).with_name('play.py'))
    module=importlib.util.module_from_spec(spec)
    weather=types.SimpleNamespace(BASE=Path('/unused'),STATE=Path('/unused'),build_call=None,request=None)
    readiness=types.SimpleNamespace(wait_for_ready=None)
    with mock.patch.dict('sys.modules',weather=weather,readiness=readiness):
        spec.loader.exec_module(module)
    return module


class HeadroomTests(unittest.TestCase):
    def exercise(self,peaks,count=16000):
        subject=load_subject()
        levels=[]
        attempts=iter(peaks)
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            decoded=base/'decoded.raw'
            def run(command,**kwargs):
                if command[0]=='sox':levels.append(float(command[command.index('-n')+1]))
                elif command[1]=='-d':decoded.write_bytes(array('h',[next(attempts)]*count).tobytes())
            with mock.patch.object(subject.subprocess,'run',side_effect=run):
                try:
                    subject.encode_audio(base/'input.wav',base/'input.raw',base/'voice.ambe',decoded)
                except ValueError as error:
                    return levels,str(error)
        return levels,None

    def test_normal_audio_uses_one_pass(self):
        self.assertEqual(self.exercise([24998]),([-3],None))

    def test_saturation_reencodes_with_headroom(self):
        self.assertEqual(self.exercise([32767,24578]),([-3,-6],None))

    def test_persistent_saturation_still_fails(self):
        levels,error=self.exercise([32767,32767,32767])
        self.assertEqual(levels,[-3,-6,-9])
        self.assertIn('clips',error)

    def test_quiet_and_invalid_duration_are_not_retried(self):
        for peak,count in ((500,16000),(2000,8000),(2000,41*8000)):
            with self.subTest(peak=peak,count=count):
                levels,error=self.exercise([peak],count)
                self.assertEqual(levels,[-3])
                self.assertIsNotNone(error)


if __name__=='__main__':unittest.main()
