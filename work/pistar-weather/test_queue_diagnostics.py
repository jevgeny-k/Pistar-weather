import gzip
import json
from pathlib import Path
import tempfile
import unittest
from queue_diagnostics import metadata,Window,ErrorTail,save_snapshot,MAX_EVENTS

def frame(payload):
    ethernet=bytes(12)+b'\x08\x00'
    ip=bytearray(20);ip[0]=0x45;ip[9]=17;ip[12:20]=b'\x0a\x00\x00\x01\x0a\x00\x00\x02'
    udp=(62031).to_bytes(2,'big')+(1234).to_bytes(2,'big')+(len(payload)+8).to_bytes(2,'big')+bytes(2)
    return ethernet+ip+udp+payload

class DiagnosticTests(unittest.TestCase):
    def test_non_dmr_authentication_is_not_recorded(self):
        self.assertIsNone(metadata(frame(b'RPTK'+b'secret'*20),'wlan0',0,1.,2.))

    def test_dmr_metadata_omits_addresses_ids_and_audio(self):
        data=bytearray(55);data[:4]=b'DMRD';data[5:11]=b'SECRET';data[16:20]=b'TEST';data[20:]=b'A'*35
        event=metadata(frame(data),'wlan0',0,1.,2.)
        self.assertIsNotNone(event);text=json.dumps(event)
        self.assertNotIn('SECRET',text);self.assertNotIn('AAAA',text);self.assertEqual(event[-1],b'TEST'.hex())
        self.assertIsNone(metadata(frame(data),'lo',0,1.,2.))

    def test_bad_short_frames_are_rejected(self):
        for size in range(42):self.assertIsNone(metadata(bytes(size),'wlan0',0,0,0))

    def test_window_is_bounded_in_time_and_count(self):
        window=Window()
        for i in range(MAX_EVENTS+100):window.append((0,float(i)/1000))
        self.assertEqual(len(window.rows),MAX_EVENTS)
        window.append((0,200.));self.assertEqual(len(window.rows),1)
        self.assertEqual(len(window.snapshot(250.)),1)
        self.assertEqual(window.snapshot(321.),[])

    def test_historical_errors_do_not_trigger_new_watch(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'log';path.write_text('E: old overflow in the DMR slot RF queue\n')
            tail=ErrorTail();self.assertIsNone(tail.poll(path))
            with path.open('a') as output:output.write('E: 2026-11-09 20:23:27.765 DMR Slot 2, overflow in the DMR slot RF queue\n')
            self.assertEqual(tail.poll(path),'2026-11-09 20:23:27.765')
            self.assertIsNone(tail.poll(path))

    def test_log_rotation_and_snapshot_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'log';path.write_text('old\n');tail=ErrorTail();tail.poll(path)
            rotated=root/'next';rotated.write_text('E: 2026-11-09 20:23:27.765 overflow in the DMR slot RF queue\n')
            self.assertIsNotNone(tail.poll(rotated))
            size=save_snapshot(root,[(1,2)]*(MAX_EVENTS+50),[(3,4)]*4100,'test',{})
            data=json.loads(gzip.decompress((root/'snapshot.json.gz').read_bytes()))
            self.assertEqual(len(data['pre']),MAX_EVENTS);self.assertEqual(len(data['post']),4000)
            self.assertLess(size,2*1024*1024)

if __name__=='__main__':unittest.main()
