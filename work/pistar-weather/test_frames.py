import unittest
from unittest.mock import patch
from bitarray import bitarray
from dmr_utils3 import bptc, golay
from proxy import validate_packets
from weather import build_call
RADIO_ID = 1  # Synthetic test identity; never an operator's live ID.


@patch('proxy.RADIO_ID', RADIO_ID)
@patch('weather.RADIO_ID', RADIO_ID)
class FrameTests(unittest.TestCase):
    def test_lc_roundtrip_and_embedded_lc(self):
        raw=build_call(bytes.fromhex('b9e881526173002a6b')*18)
        packets=validate_packets(raw)
        self.assertEqual(len(packets),12)
        for p in packets[:3]+packets[-3:]:
            bits=bitarray(endian='big'); bits.frombytes(p[20:53])
            decoded=bptc.decode_full_lc(bits[:98]+bits[166:]).tobytes()
            self.assertEqual(decoded,b'\x03\x00\x00'+RADIO_ID.to_bytes(3,'big')*2)
        for i,p in enumerate(packets[3:-3]):
            self.assertEqual(p[15],0x50 if i==0 else 0x40|i)


if __name__=='__main__': unittest.main()
