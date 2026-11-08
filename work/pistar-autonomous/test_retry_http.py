import io
import unittest
import urllib.error
from retry_http import get_json

class Retries(unittest.TestCase):
    def test_503_then_fresh_result(self):
        attempts=[];delays=[]
        def opener(request,timeout):
            attempts.append(timeout)
            if len(attempts)==1:raise urllib.error.HTTPError('https://example.test',503,'busy',{},None)
            return io.BytesIO(b'{"fresh": true}')
        self.assertEqual(get_json('request',opener=opener,sleep=delays.append),{'fresh':True})
        self.assertEqual(attempts,[25,25]);self.assertEqual(delays,[2])
    def test_persistent_failure_is_bounded(self):
        attempts=[];delays=[]
        def opener(request,timeout):
            attempts.append(1);raise urllib.error.HTTPError('https://example.test',503,'busy',{},None)
        with self.assertRaises(urllib.error.HTTPError):get_json('request',opener=opener,sleep=delays.append)
        self.assertEqual(len(attempts),3);self.assertEqual(delays,[2,5])
    def test_nontransient_http_error_not_retried(self):
        delays=[]
        def opener(request,timeout):raise urllib.error.HTTPError('https://example.test',401,'unauthorized',{},None)
        with self.assertRaises(urllib.error.HTTPError):get_json('request',opener=opener,sleep=delays.append)
        self.assertEqual(delays,[])
    def test_corrupt_json_not_used(self):
        delays=[]
        with self.assertRaises(ValueError):get_json('request',opener=lambda *a,**kw:io.BytesIO(b'not json'),sleep=delays.append)
        self.assertEqual(delays,[])

if __name__=='__main__':unittest.main()
