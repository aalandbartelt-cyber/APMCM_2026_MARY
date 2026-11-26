"""Static reference-source map. Never imports or executes a reference repository.

An outline is evidence of structural inspection, not a full-text reading claim.
"""
import ast
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / '01_参考学习'
OUT = ROOT / 'artifacts/codex_review/source_outline'


def describe(row):
    path = BASE / row['path']
    result = {'id': row['id'], 'path': row['path'], 'bytes': row['bytes'],
              'duplicate_of': row['duplicate_of']}
    try:
        source = path.read_text(encoding='utf-8-sig')
    except (UnicodeError, OSError):
        result['kind'] = 'binary_not_loaded'
        return result
    result['lines'] = len(source.splitlines())
    if path.suffix == '.py' or path.name == 'Python Code':
        try:
            tree = ast.parse(source)
        except SyntaxError as error:
            result.update(kind='unparsed_source', reason=str(error))
            return result
        result['kind'] = 'python_static_outline'
        result['module_doc'] = (ast.get_docstring(tree) or '')[:600]
        result['symbols'] = [{'line': n.lineno, 'name': n.name,
                              'doc': (ast.get_docstring(n) or '').split('\n')[0][:160]}
                             for n in ast.walk(tree)
                             if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
        calls = Counter(ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call))
        result['calls'] = dict(calls)
        result['imports'] = [ast.unparse(n) for n in tree.body
                             if isinstance(n, (ast.Import, ast.ImportFrom))]
    elif path.suffix.lower() == '.md':
        result['kind'] = 'document_outline'
        result['headings'] = re.findall(r'^#{1,6} .+$', source, re.M)
        result['opening'] = source[:900]
        result['ending'] = source[-700:]
    elif path.suffix == '.po':
        result['kind'] = 'translation_catalog'
        result['messages'] = len(re.findall(r'^msgid ', source, re.M))
        result['references'] = re.findall(r'^#: (.+)$', source, re.M)
    else:
        result['kind'] = 'support_text'
        result['opening'] = source[:350]
    return result


def main():
    rows = list(csv.DictReader((ROOT / 'docs/review/CODEX_D_READING_LEDGER.csv').open()))
    OUT.mkdir(parents=True, exist_ok=True)
    result = [describe(r) for r in rows if r['category'] == 'source_or_repo_document']
    (OUT / 'all.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    by_repo = {}
    for item in result:
        name = item['path'].split('/02_GitHub开源/')[1].split('/')[0]
        by_repo.setdefault(name, []).append(item)
    for name, items in by_repo.items():
        (OUT / (name + '.json')).write_text(json.dumps(items, ensure_ascii=False, indent=2))
        print(name, len(items), dict(Counter(x['kind'] for x in items)))


if __name__ == '__main__':
    main()
