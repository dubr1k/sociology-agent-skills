#!/usr/bin/env python3
"""Собрать шесть переносимых вариантов навыков; только стандартная библиотека."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
HARNESSES = ('hermes', 'openclaw', 'claude-code', 'codex', 'pi', 'oh-my-pi')
SKILLS = ('sociology-research', 'mixed-methods-instrument-design',
          'interim-survey-report-production', 'statistical-analysis',
          'networkx', 'thematic-analysis', 'causal-identification-gates')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frontmatter(text):
    if not text.startswith('---\n'):
        raise ValueError('Нет YAML frontmatter')
    header, body = text[4:].split('\n---\n', 1)
    fields = {}
    for key in ('name', 'description', 'license'):
        match = re.search(r'^' + key + r':\s*(.+)$', header, re.M)
        if not match:
            raise ValueError('Отсутствует поле ' + key)
        fields[key] = match.group(1).strip().strip('\"\'')
    return fields, header, body


def validate_source(root=ROOT):
    names = sorted(p.parent.name for p in (root / 'skills').glob('*/SKILL.md'))
    if names != sorted(SKILLS):
        raise ValueError('Неверный состав навыков: ' + repr(names))
    sources = json.loads((root / 'SOURCES.json').read_text())['skills']
    if sorted(x['name'] for x in sources) != sorted(SKILLS):
        raise ValueError('SOURCES.json не соответствует набору навыков')
    for name in SKILLS:
        path = root / 'skills' / name
        text = (path / 'SKILL.md').read_text()
        fields, _, body = frontmatter(text)
        if fields['name'] != name or not 1 <= len(fields['description']) <= 60:
            raise ValueError('Имя/описание: ' + name)
        if len(body) < 1500 or not re.search('[А-Яа-яЁё]', body):
            raise ValueError('Слишком краткий или не русскоязычный навык: ' + name)
        for p in path.rglob('*'):
            if p.is_symlink():
                raise ValueError('Символическая ссылка в исходнике: ' + str(p))
            if p.is_file() and p.suffix == '.md':
                s = p.read_text()
                for ref in re.findall(r'(?:references|templates|scripts)/[\w./-]+\.(?:md|py|csv|json)', s):
                    if not (path / ref).is_file():
                        raise ValueError(f'{p}: отсутствует {ref}')
                if re.search(r'/root/|/mnt/user-data|telegram:-|gh[pousr]_[A-Za-z0-9]{20,}', s):
                    raise ValueError('Потенциально приватный путь/секрет: ' + str(p))
    for item in sources:
        for license_file in item['license_files']:
            if not (root / license_file).is_file():
                raise ValueError('Нет лицензии: ' + license_file)
    for h in HARNESSES:
        if not (root / 'adapters' / (h + '.md')).is_file():
            raise ValueError('Нет адаптера: ' + h)
    return sources


def build(root=ROOT):
    sources = validate_source(root)
    target = root / 'dist'
    stage = root / '.build-tmp'
    if stage.exists():
        raise FileExistsError('Осталась временная сборка: ' + str(stage))
    stage.mkdir()
    manifest = {'schema': 1, 'harnesses': list(HARNESSES), 'skills': list(SKILLS), 'files': {}}
    try:
        for harness in HARNESSES:
            adapter = (root / 'adapters' / (harness + '.md')).read_text()
            for name in SKILLS:
                source = root / 'skills' / name
                dest = stage / harness / 'skills' / name
                shutil.copytree(source, dest)
                text = (dest / 'SKILL.md').read_text()
                _, header, body = frontmatter(text)
                (dest / 'SKILL.md').write_text('---\n' + header + '\n---\n\n' + adapter.rstrip() + '\n\n' + body.lstrip())
                rec = next(x for x in sources if x['name'] == name)
                (dest / 'LICENSES').mkdir(exist_ok=True)
                for license_file in rec['license_files']:
                    shutil.copy2(root / license_file, dest / 'LICENSES' / Path(license_file).name)
                (dest / 'SOURCE.json').write_text(json.dumps(rec, ensure_ascii=False, indent=2) + '\n')
        for p in sorted(stage.rglob('*')):
            if p.is_file():
                manifest['files'][p.relative_to(stage).as_posix()] = digest(p)
        (stage / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        # Only the generated dist directory is replaced; source and user skills are untouched.
        if target.is_symlink():
            raise ValueError('dist не должен быть символической ссылкой')
        if target.exists():
            shutil.rmtree(target)
        stage.rename(target)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    return verify_dist(root)


def verify_dist(root=ROOT):
    folder = root / 'dist'
    manifest = json.loads((folder / 'manifest.json').read_text())
    expected_pairs = {(h, s) for h in HARNESSES for s in SKILLS}
    actual_pairs = {(p.parts[-4], p.parts[-2]) for p in folder.glob('*/skills/*/SKILL.md')}
    if actual_pairs != expected_pairs:
        raise ValueError('Набор сборок не совпадает с 6 × 7')
    actual_files = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p != folder / 'manifest.json'}
    if actual_files != set(manifest['files']):
        raise ValueError('Состав файлов расходится с манифестом')
    for relative, sha in manifest['files'].items():
        path = folder / relative
        if path.is_symlink() or digest(path) != sha:
            raise ValueError('Контрольная сумма не совпала: ' + relative)
    return {'harnesses': len(HARNESSES), 'skills': len(SKILLS), 'variants': len(actual_pairs), 'files': len(actual_files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Проверить существующую сборку без перезаписи')
    args = parser.parse_args()
    validate_source()
    print(json.dumps(verify_dist() if args.check else build(), ensure_ascii=False))


if __name__ == '__main__':
    main()
