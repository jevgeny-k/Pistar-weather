import unittest
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import slot2_trial as trial
from slot2_trial import set_slot2

class ConfigTests(unittest.TestCase):
    def test_changes_only_network_slot(self):
        source='[DMR]\nSlot2=1\nId=1\n[DMR Network]\nSlot1=1\nSlot2=1\nPassword=example\n[Other]\nSlot2=1\n'
        changed=set_slot2(source,0)
        self.assertEqual(changed,source.replace('[DMR Network]\nSlot1=1\nSlot2=1','[DMR Network]\nSlot1=1\nSlot2=0'))
        self.assertEqual(set_slot2(changed,1),source)
    def test_missing_or_duplicate_slot_rejected(self):
        for source in ['[DMR]\nSlot2=1\n','[DMR Network]\nSlot1=1\n','[DMR Network]\nSlot2=1\nSlot2=0\n']:
            with self.assertRaises(ValueError):set_slot2(source,0)

class RestoreTests(unittest.TestCase):
    def test_future_deadline_does_not_restore_early(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)/'state.json';state.write_text(json.dumps({'active':True,'until_epoch':100,'until_utc':'future'}))
            with patch.object(trial,'STATE',state),patch.object(trial.time,'time',lambda:50),patch.object(trial,'command') as command:
                trial.restore();command.assert_not_called()
                self.assertTrue(json.loads(state.read_text())['active'])

    def test_failed_restart_keeps_restore_armed_and_retry_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);config=root/'config';state=root/'state.json'
            config.write_text('[DMR Network]\nSlot1=1\nSlot2=0\nAddress=keep.example\n[Other]\nId=123\n')
            state.write_text(json.dumps({'active':True,'until_epoch':0,'until_utc':'past','original_slot2':1}))
            calls=[];fail=[True]
            def command(*args):
                calls.append(args)
                if args==('systemctl','restart','mmdvmhost') and fail[0]:raise RuntimeError('simulated restart failure')
                return SimpleNamespace(stdout='inactive\n')
            with patch.object(trial,'CONFIG',config),patch.object(trial,'STATE',state),patch.object(trial,'writable',nullcontext),patch.object(trial,'write_config',lambda text:config.write_text(text)),patch.object(trial,'command',command):
                with self.assertRaisesRegex(RuntimeError,'restart failure'):trial.restore()
                self.assertTrue(json.loads(state.read_text())['active'])
                self.assertIn('Slot2=1',config.read_text())
                fail[0]=False;trial.restore()
                self.assertFalse(json.loads(state.read_text())['active'])
                self.assertIn('Address=keep.example',config.read_text())
                self.assertIn('[Other]\nId=123',config.read_text())
                self.assertIn(('systemctl','disable','--now',trial.TIMER),calls)

if __name__=='__main__':unittest.main()
