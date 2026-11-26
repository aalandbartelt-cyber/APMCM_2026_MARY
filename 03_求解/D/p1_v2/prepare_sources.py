"""Download only software source / elemental descriptors; never material labels."""
from pathlib import Path
import hashlib
import json
import shutil
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/p1_v21'
PROPS = [f'N{s}{kind}' for kind in ('Valence', 'Unfilled') for s in 'spdf']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url, timeout=60) as response:
            path.write_bytes(response.read())
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for prop in PROPS:
        url = f'https://raw.githubusercontent.com/hackingmaterials/matminer/v0.9.3/matminer/utils/data_files/magpie_elementdata/{prop}.table'
        path = fetch(url, OUT / 'sources/magpie' / (prop + '.table'))
        records.append(dict(property=prop, url=url, sha256=digest(path)))
    meta = json.loads(urllib.request.urlopen('https://pypi.org/pypi/lightgbm/3.3.5/json', timeout=60).read())
    item = next(x for x in meta['urls'] if x['packagetype'] == 'sdist')
    archive = fetch(item['url'], OUT / 'sources' / item['filename'])
    assert digest(archive) == item['digests']['sha256']
    source = OUT / 'sources/lightgbm-3.3.5'
    if not source.exists():
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                dest = (OUT / 'sources' / member.name).resolve()
                assert dest.is_relative_to((OUT / 'sources').resolve())
                assert not member.issym() and not member.islnk()
            tar.extractall(OUT / 'sources')
    cpp = source / 'compile/src/metric/dcg_calculator.cpp'
    if not cpp.exists():
        cpp = source / 'src/metric/dcg_calculator.cpp'
    old = cpp.read_text()
    needle = 'DCGCalculator::kMaxPosition = 10000;'
    assert needle in old or 'DCGCalculator::kMaxPosition = 20000;' in old
    if needle in old:
        (OUT / 'sources/dcg_calculator.original.cpp').write_text(old)
        cpp.write_text(old.replace(needle, 'DCGCalculator::kMaxPosition = 20000;'))
    records.append(dict(software='LightGBM 3.3.5', url=item['url'], sha256=digest(archive), patched_cpp_sha256=digest(cpp), patch='kMaxPosition 10000 -> 20000'))
    (OUT / 'sources/source_manifest.json').write_text(json.dumps(records, indent=2))
    print(json.dumps({'sources': len(records), 'cpp': str(cpp), 'cmake_source': str(cpp.parents[2])}))


if __name__ == '__main__':
    main()
