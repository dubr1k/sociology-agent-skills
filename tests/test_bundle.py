"""Проверка сборки и безопасной установки; реальные профили не изменяются."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build
import install


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.work = ROOT / '.test-work'
        self.work.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=self.work)
        self.dest = Path(self.temp.name) / 'skills'

    def tearDown(self):
        self.temp.cleanup()

    def test_01_source_contract(self):
        self.assertEqual(len(build.validate_source()), 7)

    def test_02_all_variants_and_checksums(self):
        result = build.verify_dist()
        self.assertEqual(result['variants'], 42)
        self.assertEqual(result['harnesses'], 6)

    def test_03_dry_run_is_read_only(self):
        result = install.install('hermes', self.dest, build.SKILLS)
        self.assertFalse(self.dest.exists())
        self.assertFalse(result['applied'])

    def test_04_every_harness_install(self):
        for harness in build.HARNESSES:
            with self.subTest(harness=harness):
                dest = self.dest / harness
                result = install.install(harness, dest, build.SKILLS, apply=True)
                self.assertTrue(result['verified'])
                self.assertEqual(len(list(dest.glob('*/SKILL.md'))), 7)
                for name in build.SKILLS:
                    self.assertTrue((dest / name / 'SOURCE.json').is_file())
                    self.assertTrue(list((dest / name / 'LICENSES').iterdir()))

    def test_05_existing_directory_is_not_overwritten(self):
        self.dest.mkdir()
        existing = self.dest / build.SKILLS[0]
        existing.mkdir()
        sentinel = existing / 'SKILL.md'
        sentinel.write_text('original user version')
        with self.assertRaises(FileExistsError):
            install.install('hermes', self.dest, build.SKILLS, apply=True)
        self.assertEqual(sentinel.read_text(), 'original user version')
        self.assertEqual(len(list(self.dest.iterdir())), 1)

    def test_06_unknown_skill_is_rejected(self):
        with self.assertRaises(ValueError):
            install.install('hermes', self.dest, ['../escape'], apply=True)
        self.assertFalse(self.dest.exists())

    def test_07_symlink_destination_is_rejected(self):
        real = Path(self.temp.name) / 'real'
        real.mkdir()
        self.dest.symlink_to(real, target_is_directory=True)
        with self.assertRaises(ValueError):
            install.install('hermes', self.dest, build.SKILLS, apply=True)
        self.assertEqual(list(real.iterdir()), [])

    def test_08_duplicate_skill_is_rejected(self):
        with self.assertRaises(ValueError):
            install.install('hermes', self.dest, [build.SKILLS[0]] * 2, apply=True)

    def test_09_modified_bundle_is_rejected(self):
        clone = Path(self.temp.name) / 'clone'
        shutil.copytree(ROOT / 'dist', clone / 'dist')
        p = clone / 'dist' / 'hermes' / 'skills' / build.SKILLS[0] / 'SKILL.md'
        p.write_text(p.read_text() + '\nchanged\n')
        with self.assertRaises(ValueError):
            install.install('hermes', self.dest, build.SKILLS, apply=True, root=clone)
        self.assertFalse(self.dest.exists())

    def test_10_single_skill_install(self):
        result = install.install('codex', self.dest, ['thematic-analysis'], apply=True)
        self.assertEqual(result['skills'], ['thematic-analysis'])
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['thematic-analysis'])


if __name__ == '__main__':
    unittest.main()
