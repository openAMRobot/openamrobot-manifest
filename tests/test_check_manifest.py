"""Regression tests for tools/check_manifest.py (offline stages only).

Each negative case is a single mutation of the real openamrobot.repos, and
asserts the failure reason so an unrelated error cannot satisfy the test.
Run: python3 -m unittest discover -s tests -v
"""

import os
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, 'openamrobot.repos')
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import check_manifest  # noqa: E402

FW_FIXED = '  firmware/openamr-upperbody-fw: {'
HW_FIXED = '  hardware/openamr-upperbody-hw: {'
DUPLICATE_LINE = (
    '  src/openamrobot-comm:         { type: git, url: '
    'https://github.com/openAMRobot/openamrobot-comm-fork.git, version: main }\n')


def manifest_text():
    with open(MANIFEST, encoding='utf-8') as stream:
        return stream.read()


def mutate(old, new):
    text = manifest_text()
    assert text.count(old) == 1, 'mutation anchor %r not unique' % old
    return text.replace(old, new)


class ManifestCheckTest(unittest.TestCase):

    def check(self, text):
        """Run the CLI in offline mode on text; return (exit code, output)."""
        with tempfile.NamedTemporaryFile(
                'w', suffix='.repos', delete=False, encoding='utf-8') as tmp:
            tmp.write(text)
        self.addCleanup(os.unlink, tmp.name)
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, 'tools', 'check_manifest.py'),
             '--offline', tmp.name],
            capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr

    def assert_rejected(self, text, *needles):
        code, out = self.check(text)
        self.assertEqual(code, 1, out)
        for needle in needles:
            self.assertIn(needle, out)

    # Positive case

    def test_corrected_manifest_accepted(self):
        code, out = self.check(manifest_text())
        self.assertEqual(code, 0, out)
        self.assertIn('[PASS] yamllint', out)
        self.assertIn('[PASS] strict', out)
        self.assertIn('12 repositories', out)
        self.assertIn('[SKIPPED] remote', out)

    # Original defects (D-03 H1)

    def test_rejects_original_malformed_firmware_key(self):
        self.assert_rejected(
            mutate(FW_FIXED, '  firmware/openamr-upperbody-fw:{'),
            '[FAIL] yamllint', 'mapping values are not allowed here',
            '[FAIL] strict')

    def test_rejects_original_malformed_hardware_key(self):
        self.assert_rejected(
            mutate(HW_FIXED, '  hardware/openamr-upperbody-hw:{'),
            '[FAIL] yamllint', 'mapping values are not allowed here',
            '[FAIL] strict')

    # Duplicate repository key

    def test_plain_safe_load_accepts_duplicate(self):
        # Documents why safe_load alone is insufficient: the duplicate
        # silently replaces the first entry.
        text = manifest_text() + DUPLICATE_LINE
        data = yaml.safe_load(text)
        self.assertEqual(len(data['repositories']), 12)
        self.assertIn('comm-fork', data['repositories']['src/openamrobot-comm']['url'])

    def test_rejects_duplicate_repository_key(self):
        self.assert_rejected(
            manifest_text() + DUPLICATE_LINE,
            '[FAIL] yamllint', 'duplication of key "src/openamrobot-comm"',
            '[FAIL] strict', "found duplicate key 'src/openamrobot-comm'")

    def test_strict_loader_alone_rejects_duplicate(self):
        with self.assertRaisesRegex(yaml.YAMLError, 'duplicate key'):
            yaml.load(manifest_text() + DUPLICATE_LINE,
                      Loader=check_manifest.StrictLoader)

    # Semantic checks (strict stage only; yamllint accepts these)

    def assert_semantic(self, text, needle):
        code, out = self.check(text)
        self.assertEqual(code, 1, out)
        self.assertIn('[PASS] yamllint', out)
        self.assertIn('[FAIL] strict', out)
        self.assertIn(needle, out)

    def test_rejects_missing_version(self):
        self.assert_semantic(
            mutate('openamrobot-docs.git, version: main }',
                   'openamrobot-docs.git }'),
            "'docs/openamrobot-docs': missing version")

    def test_rejects_unsupported_type(self):
        self.assert_semantic(
            mutate('ui/openamrobot-ui:            { type: git',
                   'ui/openamrobot-ui:            { type: hg'),
            'type must be one of git')

    def test_rejects_non_https_url(self):
        self.assert_semantic(
            mutate('https://github.com/openAMRobot/openamrobot-ui.git',
                   'http://github.com/openAMRobot/openamrobot-ui.git'),
            'url must use https://')

    def test_rejects_parent_path(self):
        self.assert_semantic(
            mutate('  docs/openamrobot-docs:', '  ../openamrobot-docs:'),
            'path must be relative and normalized')

    def test_rejects_absolute_path(self):
        self.assert_semantic(
            mutate('  docs/openamrobot-docs:', '  /docs/openamrobot-docs:'),
            'path must be relative and normalized')

    def test_rejects_nested_path(self):
        self.assert_semantic(
            mutate('  docs/openamrobot-docs:', '  ui/openamrobot-ui/docs:'),
            "'ui/openamrobot-ui/docs' is nested inside 'ui/openamrobot-ui'")

    # Remote stage output interpretation (no network needed)

    def test_missing_branch_reported_but_commit_hash_tolerated(self):
        out = '\n'.join(
            "Found git repository 'https://x/%s.git' but unable to verify "
            "non-branch / non-tag ref '%s' without cloning the repo" % (n, v)
            for n, v in (('a', 'no-such-branch'), ('b', '6be6552'),
                         ('c', '6be65524788d2b4be91f0c7d14f9decf324834d6')))
        self.assertEqual(check_manifest.missing_refs(out), ['no-such-branch'])

    def test_rejects_empty_manifest(self):
        self.assert_semantic('repositories: {}\n', 'non-empty mapping')


if __name__ == '__main__':
    unittest.main()
