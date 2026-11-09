#!/usr/bin/env python3
"""Установить выбранный вариант в явно заданный каталог; по умолчанию только план."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from build import HARNESSES, ROOT, SKILLS, digest, verify_dist


def install(harness, destination, names, apply=False, root=ROOT):
    verify_dist(root)
    if harness not in HARNESSES or not names or any(n not in SKILLS for n in names):
        raise ValueError('Неизвестный харнесс/навык или пустой набор')
    if len(names) != len(set(names)):
        raise ValueError('Навыки не должны повторяться')
    dest = Path(destination).expanduser().absolute()
    if any(p.is_symlink() for p in (dest, *dest.parents)):
        raise ValueError('Для предсказуемой установки укажите путь без символических ссылок')
    source = root / 'dist' / harness / 'skills'
    for name in names:
        if (dest / name).exists() or (dest / name).is_symlink():
            raise FileExistsError(f'Уже существует {dest / name}; существующий навык не перезаписан')
    result = {'harness': harness, 'destination': str(dest), 'skills': list(names), 'applied': False}
    if not apply:
        return result
    dest.mkdir(parents=True, exist_ok=True)
    # Staging remains on the destination filesystem; no system temporary directory.
    stage = Path(tempfile.mkdtemp(prefix='.sociology-install-', dir=dest))
    moved = []
    try:
        for name in names:
            shutil.copytree(source / name, stage / name)
            for path in (source / name).rglob('*'):
                if path.is_file():
                    counterpart = stage / name / path.relative_to(source / name)
                    if digest(path) != digest(counterpart):
                        raise ValueError('Ошибка копирования: ' + name)
        for name in names:
            # Exclusive reservation prevents accidentally replacing a raced-in directory.
            target = dest / name
            target.mkdir(exist_ok=False)
            moved.append(target)
            for child in (stage / name).iterdir():
                child.rename(target / child.name)
        for name in names:
            for path in (source / name).rglob('*'):
                if path.is_file() and digest(path) != digest(dest / name / path.relative_to(source / name)):
                    raise ValueError('Проверка установленной копии не пройдена: ' + name)
        result['applied'] = True
        result['verified'] = True
    except Exception:
        for target in moved:
            shutil.rmtree(target)
        raise
    finally:
        shutil.rmtree(stage)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness', required=True, choices=HARNESSES)
    parser.add_argument('--dest', required=True, help='Точный каталог skills выбранной установки; см. docs/harnesses.md')
    parser.add_argument('--skill', action='append', choices=SKILLS, help='Повторяемый параметр; по умолчанию все семь')
    parser.add_argument('--apply', action='store_true', help='Записать файлы после проверки плана')
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.harness, args.dest, args.skill or SKILLS, args.apply), ensure_ascii=False, indent=2))
    except (ValueError, FileExistsError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
