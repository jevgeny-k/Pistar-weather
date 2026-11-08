import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from bootcheck import verify_bank

class BankChecks(unittest.TestCase):
    def test_detects_corruption_and_missing_index(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);(base/'bank').mkdir();audio=base/'bank/test.wav';audio.write_bytes(b'known audio')
            entries={str(i):{'wav':'bank/test.wav','text_sha256':'text'} for i in range(1604)}
            records={key:{'sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),'text_sha256':'text'} for key in entries}
            catalog={'profile':{'speaker':'xenia'},'entries':entries};bank={'profile':catalog['profile'],'generated':records}
            (base/'catalog.json').write_text(json.dumps(catalog));(base/'bank-manifest.json').write_text(json.dumps(bank))
            self.assertIn('1604',verify_bank(base))
            audio.write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError,'Damaged'):verify_bank(base)
            records.pop('0');(base/'bank-manifest.json').write_text(json.dumps(bank))
            with self.assertRaisesRegex(ValueError,'Incomplete'):verify_bank(base)

if __name__=='__main__':unittest.main()
