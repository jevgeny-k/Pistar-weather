"""Private configuration must never turn an unconfigured copy into a transmitter."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from site_settings import configured_radio_id, load_site, require_radio_id
import proxy


class SiteSettingsTests(unittest.TestCase):
    def test_missing_configuration_blocks_transmission(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'PISTAR_SITE_CONFIG': str(Path(folder) / 'missing.json')}):
                self.assertEqual(configured_radio_id(), 0)
                with self.assertRaisesRegex(ValueError, 'transmission is disabled'):
                    require_radio_id(configured_radio_id())
                with self.assertRaisesRegex(ValueError, 'missing'):
                    load_site(required=True)

    def test_private_configuration_is_loaded_explicitly(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'site.json'
            path.write_text(json.dumps({'radio_id': 1, 'upstream_host': 'example.invalid'}))
            with patch.dict(os.environ, {'PISTAR_SITE_CONFIG': str(path)}):
                self.assertEqual(require_radio_id(configured_radio_id()), 1)
                self.assertEqual(load_site()['upstream_host'], 'example.invalid')

    def test_invalid_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'site.json'
            for value in (0, -1, 0x1000000, True, '1'):
                path.write_text(json.dumps({'radio_id': value}))
                with patch.dict(os.environ, {'PISTAR_SITE_CONFIG': str(path)}):
                    with self.assertRaises(ValueError):
                        configured_radio_id()

    def test_relay_and_packet_validation_stop_before_network_access(self):
        with patch('proxy.RADIO_ID', 0), patch('proxy.socket.gethostbyname') as lookup:
            with self.assertRaisesRegex(ValueError, 'transmission is disabled'):
                proxy.validate_packets(b'')
            with patch('sys.argv', ['proxy.py']):
                with self.assertRaisesRegex(ValueError, 'transmission is disabled'):
                    proxy.main()
            lookup.assert_not_called()


if __name__ == '__main__':
    unittest.main()
