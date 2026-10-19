import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_release_manifest import load_release, check_development, check_export
from check_manifest import run_strict

ROOT = Path(__file__).resolve().parents[1]


class ReleaseManifestTests(unittest.TestCase):
    def test_snapshot_and_development_coverage(self):
        release = load_release(ROOT / 'releases/v2.0.0-rc.1.repos')
        dev = yaml.safe_load((ROOT / 'openamrobot.repos').read_text())['repositories']
        self.assertEqual(set(release), set(dev))
        for name in release:
            self.assertEqual(release[name]['url'], dev[name]['url'])

    def test_mutable_and_short_refs_rejected(self):
        original = (ROOT / 'releases/v2.0.0-rc.1.repos').read_text()
        first = next(iter(load_release(ROOT / 'releases/v2.0.0-rc.1.repos').values()))['version']
        for version in ('main', 'jazzy', 'v2.0.0-rc.1', first[:7]):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'bad.repos'
                path.write_text(original.replace(first, version, 1))
                with self.assertRaisesRegex(ValueError, 'full commit SHA'):
                    load_release(path)

    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.repos'
            path.write_text('repositories: {}\nrepositories: {}\n')
            with self.assertRaises(yaml.YAMLError):
                load_release(path)

    def test_development_stays_mutable(self):
        with self.assertRaisesRegex(ValueError, 'full commit SHA'):
            load_release(ROOT / 'openamrobot.repos')
        release = load_release(ROOT / 'releases/v2.0.0-rc.1.repos')
        check_development(release, ROOT / 'openamrobot.repos')

    def test_schema_rejects_bad_path_url_and_missing_version(self):
        original = yaml.safe_load((ROOT / 'releases/v2.0.0-rc.1.repos').read_text())
        first = next(iter(original['repositories']))
        for kind in ('path', 'url', 'version'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                data = yaml.safe_load(yaml.safe_dump(original))
                if kind == 'path':
                    data['repositories']['../escape'] = data['repositories'].pop(first)
                elif kind == 'url':
                    data['repositories'][first]['url'] = 'http://example.invalid/source.git'
                else:
                    del data['repositories'][first]['version']
                path = Path(tmp) / 'bad.repos'
                path.write_text(yaml.safe_dump(data))
                with self.assertRaises(ValueError):
                    load_release(path)

    def test_development_coverage_and_source_mismatches_rejected(self):
        release = load_release(ROOT / 'releases/v2.0.0-rc.1.repos')
        first = next(iter(release))
        changed = dict(release)
        changed.pop(first)
        with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
            check_development(changed, ROOT / 'openamrobot.repos')
        changed = {name: dict(entry) for name, entry in release.items()}
        changed[first]['url'] += '-wrong'
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            check_development(changed, ROOT / 'openamrobot.repos')

    def test_exact_export_accepts_reordering_rejects_changed_sha(self):
        release = load_release(ROOT / 'releases/v2.0.0-rc.1.repos')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'export.repos'
            exported = dict(reversed(list(release.items())))
            path.write_text(yaml.safe_dump({'repositories': exported}))
            check_export(release, path)
            first = next(iter(exported))
            exported[first] = dict(exported[first], version='0' * 40)
            path.write_text(yaml.safe_dump({'repositories': exported}))
            with self.assertRaisesRegex(ValueError, 'exact export does not match'):
                check_export(release, path)

    def test_regression_generic_validator_allows_mutable_release(self):
        original = (ROOT / 'releases/v2.0.0-rc.1.repos').read_text()
        first = next(iter(load_release(ROOT / 'releases/v2.0.0-rc.1.repos').values()))['version']
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'mutable.repos'
            path.write_text(original.replace(first, 'main', 1))
            self.assertTrue(run_strict(path)[0])
            with self.assertRaisesRegex(ValueError, 'full commit SHA'):
                load_release(path)
