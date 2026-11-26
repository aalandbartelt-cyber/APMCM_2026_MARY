"""Read-only source extraction helpers; cache creation is not a reading claim."""
import argparse
import csv
import re
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'artifacts/codex_review/web_text'


def extract(row):
    source = ROOT / '01_参考学习' / row['path']
    raw = source.read_text(encoding='utf-8-sig')
    if source.suffix == '.html':
        soup = BeautifulSoup(raw, 'html.parser')
        article = soup.select_one('article.bd-article') or soup.select_one('main') or soup.body or soup
        for element in article.select('script,style,.headerlink,nav'):
            element.decompose()
        for node in list(article.find_all(string=True)):
            try:
                repaired = str(node).encode('latin1').decode('utf8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            node.replace_with(repaired)
        text = article.get_text('\n', strip=True)
    else:
        lines = raw.splitlines()
        start = next((n for n, s in enumerate(lines) if re.match(r'^# [^#]', s)), 0)
        text = '\n'.join(lines[start:])
    lines = [s.rstrip() for s in text.splitlines() if s.strip()]
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (row['id'] + '.txt')
    path.write_text('\n'.join(lines) + '\n')
    return path, lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ids', nargs='+')
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--end', type=int)
    parser.add_argument('--inventory-only', action='store_true')
    args = parser.parse_args()
    rows = {r['id']: r for r in csv.DictReader((ROOT / 'docs/review/CODEX_D_READING_LEDGER.csv').open())}
    for key in args.ids:
        path, lines = extract(rows[key])
        print(f"SOURCE {key} {rows[key]['path']} | {len(lines)} cleaned lines | {path}")
        if not args.inventory_only:
            for n in range(args.start, min(args.end or len(lines), len(lines)) + 1):
                print(f'{n}: {lines[n - 1]}')


if __name__ == '__main__':
    main()
