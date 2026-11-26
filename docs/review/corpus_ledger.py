"""Local reading inventory. Extraction never marks a source as read.

This utility does not import modeling code, contact services, or unpickle assets.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

PROJECT = Path(__file__).resolve().parents[2]
CORPUS = PROJECT / '01_参考学习'
LEDGER = PROJECT / 'docs/review/CODEX_D_READING_LEDGER.csv'
CACHE = PROJECT / 'artifacts/codex_review/corpus_text'
FIELDS = ['id', 'path', 'bytes', 'sha256', 'duplicate_of', 'category',
          'text_lines', 'read_state', 'coverage', 'notes']


def rows():
    with LEDGER.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def save(items):
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='',
                                     dir=LEDGER.parent, delete=False) as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(items)
        temporary = stream.name
    os.replace(temporary, LEDGER)


def category(path):
    rel = path.relative_to(CORPUS).as_posix()
    if path.suffix.lower() in {'.zip', '.whl'}:
        return 'archive'
    if path.suffix.lower() in {'.png', '.ico', '.pkl', '.npz', '.npy', '.xlsx', '.xls', '.mol2', '.pdbqt'}:
        return 'data_or_visual'
    if '/03_学术论文/' in rel:
        return 'research'
    if rel.startswith('优秀论文/') or rel.startswith('论文终稿参考/'):
        return 'writing_reference'
    if rel.startswith('往届赛题/'):
        return 'past_problem'
    if '/01_Kaiwu官方/' in rel:
        return 'official_platform'
    if '/02_GitHub开源/' in rel:
        return 'source_or_repo_document'
    return 'guide'


def inventory():
    previous = {row['path']: row for row in rows()} if LEDGER.exists() else {}
    seen, result = {}, []
    for number, path in enumerate(sorted(p for p in CORPUS.rglob('*') if p.is_file()), 1):
        rel = path.relative_to(CORPUS).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        row = {key: '' for key in FIELDS}
        row.update(id=f'R{number:04d}', path=rel, bytes=path.stat().st_size,
                   sha256=digest, duplicate_of=seen.get(digest, ''),
                   category=category(path), read_state='inventoried')
        old = previous.get(rel)
        if old and old['sha256'] == digest:
            row.update({k: old[k] for k in ['text_lines', 'read_state', 'coverage', 'notes']})
        seen.setdefault(digest, row['id'])
        result.append(row)
    save(result)
    print(json.dumps({'files': len(result), 'byte_identical_duplicates': sum(bool(r['duplicate_of']) for r in result),
                      'categories': Counter(r['category'] for r in result)}, ensure_ascii=False))


def select(items, selector):
    matches = [r for r in items if r['id'] == selector or r['path'] == selector]
    if len(matches) != 1:
        raise SystemExit(f'Expected one exact ID/path, found {len(matches)}')
    return matches[0]


def extract(row):
    path = CORPUS / row['path']
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{row['id']}.txt"
    if path.suffix.lower() == '.pdf':
        proc = subprocess.run(['pdftotext', '-layout', str(path), '-'], capture_output=True, check=True)
        content = proc.stdout.decode('utf-8')
    elif path.suffix.lower() == '.docx':
        with ZipFile(path) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
            content = '\n'.join(''.join(t.text or '' for t in p.iter() if t.tag.endswith('}t'))
                                for p in root.iter() if p.tag.endswith('}p'))
    elif path.suffix.lower() in {'.zip', '.whl'}:
        with ZipFile(path) as archive:
            content = '\n'.join(archive.namelist())
    else:
        content = path.read_bytes().decode('utf-8')
        if '\0' in content:
            raise ValueError('Binary source requires a format-specific inspection')
    cached.write_text(content, encoding='utf-8')
    row['text_lines'] = str(len(content.splitlines()))
    return cached, content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['inventory', 'show', 'mark', 'summary'])
    parser.add_argument('selector', nargs='?')
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--end', type=int)
    parser.add_argument('--state')
    parser.add_argument('--coverage', default='')
    parser.add_argument('--notes', default='')
    args = parser.parse_args()
    if args.action == 'inventory':
        inventory()
        return
    items = rows()
    if args.action == 'summary':
        print(json.dumps({'total': len(items), 'states': Counter(r['read_state'] for r in items)}, ensure_ascii=False))
        return
    row = select(items, args.selector)
    if args.action == 'mark':
        if not args.state:
            parser.error('mark requires explicit --state')
        cached = CACHE / f"{row['id']}.txt"
        if cached.exists():
            row['text_lines'] = str(len(cached.read_text().splitlines()))
        row.update(read_state=args.state, coverage=args.coverage, notes=args.notes)
        save(items)
        print(json.dumps(row, ensure_ascii=False))
        return
    cached, content = extract(row)
    lines = content.splitlines()
    end = min(args.end or len(lines), len(lines))
    print(f"SOURCE {row['id']} {row['path']} | {len(lines)} lines | {cached}")
    for number in range(args.start, end + 1):
        print(f'{number}: {lines[number - 1]}')


if __name__ == '__main__':
    main()
