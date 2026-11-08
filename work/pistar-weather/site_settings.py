"""Load optional private site settings without embedding an operator identity."""
import json
import os
from pathlib import Path


def load_site(required=False):
    path = Path(os.environ.get('PISTAR_SITE_CONFIG', '/etc/pistar-weather/site.json'))
    if not path.is_file():
        if required:
            raise ValueError('Private site configuration is missing; see config/site.example.json')
        return {}
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('Site configuration must be a JSON object')
    return value


def configured_radio_id():
    value = load_site().get('radio_id')
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= 0xFFFFFF:
        raise ValueError('Set a valid private radio_id before enabling the service')
    return value


def require_radio_id(value):
    if not 0 < value <= 0xFFFFFF:
        raise ValueError('Radio ID is not configured; transmission is disabled')
    return value
