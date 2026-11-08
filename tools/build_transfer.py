"""Build a self-contained asset/source bundle; never connect to the hotspot."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(destination):
    files = {}

    def add(source, target):
        if target in files:
            raise ValueError('Duplicate destination: ' + target)
        if not source.is_file():
            raise FileNotFoundError(source)
        files[target] = source

    for name in ('proxy.py', 'weather.py', 'encode.c', 'site_settings.py', 'pistar-weather-relay.service'):
        add(ROOT / 'work/pistar-weather' / name, 'relay/' + name)
    add(ROOT / 'assets/encode', 'relay/encode')
    add(ROOT / 'config/site.example.json', 'config/site.example.json')
    add(ROOT / 'work/pistar-weather/site_settings.py', 'autonomous/site_settings.py')
    for name in ('assemble.py', 'autonomous.py', 'runtime.py', 'play.py', 'readiness.py'):
        add(ROOT / 'work/pistar-autonomous' / name, 'autonomous/' + name)
    add(ROOT / 'work/pistar-autonomous/bootcheck.py', 'relay/bootcheck.py')
    base = ROOT / 'outputs/pi-only-preparation'
    catalog = json.loads((base / 'catalog.json').read_text(encoding='utf-8'))
    bank = json.loads((base / 'bank-manifest.json').read_text(encoding='utf-8'))
    if len(catalog['entries']) != 1604 or set(catalog['entries']) != set(bank['generated']):
        raise ValueError('Incomplete bank')
    if catalog['profile'] != bank['profile']:
        raise ValueError('Voice profile mismatch')
    for key, entry in catalog['entries'].items():
        relative = Path(entry['wav'])
        path = (base / relative).resolve()
        if path.parent != (base / 'bank').resolve():
            raise ValueError('Invalid bank path')
        record = bank['generated'][key]
        if record['text_sha256'] != entry['text_sha256']:
            raise ValueError('Phrase text mismatch: ' + key)
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Phrase audio mismatch: ' + key)
        add(path, 'autonomous/' + relative.as_posix())
    for name in ('catalog.json', 'bank-manifest.json'):
        add(base / name, 'autonomous/' + name)
    for path in sorted((base / 'schedule').iterdir()):
        if path.suffix in ('.service', '.timer'):
            add(path, 'systemd/' + path.name)
    for name in ('CODEX-HANDOFF.md', 'AGENTS.md', 'README.md', 'VALIDATION.md', 'PRIVACY.md'):
        add(ROOT / name, name)
    for path in sorted(base.glob('*.md')):
        add(path, 'docs/' + path.name)

    records = {
        name: {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        for name, path in sorted(files.items())
    }
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Refuse to overwrite a package that another agent may already be using.
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, name)
        archive.writestr('TRANSFER-MANIFEST.json', json.dumps({'files': records}, indent=2) + '\n')
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP integrity check failed')
        for name, record in records.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != record['sha256']:
                raise ValueError('Packaged file mismatch: ' + name)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.zip.sha256').write_text(digest + '  ' + destination.name + '\n', encoding='ascii')
    print(f'Verified {len(records)} files, including 1604 phrases: {destination}')
    print('SHA256 ' + digest)


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'dist/pistar-weather-transfer.zip')
