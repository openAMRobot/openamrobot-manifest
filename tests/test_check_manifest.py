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
from unittest import mock

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
        self.assertIn('11 repositories', out)
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
        self.assertEqual(len(data['repositories']), 11)
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



class TipBugFallbackTest(unittest.TestCase):
    """vcstool 0.3.0 advertises a branch-tip SHA but crashes in validate."""

    SHA = '34300099fadfc772965962dec837bf436706188f'
    URL = 'https://example.org/lidar.git'
    BUG = "UnboundLocalError: cannot access local variable 'version_type'"

    def manifest(self, version=None, other=False):
        repos = {
            'src/lidar': {
                'type': 'git',
                'url': self.URL,
                'version': version or self.SHA,
            },
        }
        if other:
            repos['src/other'] = {
                'type': 'git', 'url': 'https://example.org/other.git',
                'version': 'main',
            }
        with tempfile.NamedTemporaryFile(
                'w', suffix='.repos', delete=False, encoding='utf-8') as tmp:
            yaml.safe_dump({'repositories': repos}, tmp, sort_keys=False)
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    @staticmethod
    def completed(cmd, code=0, out='', err=''):
        return subprocess.CompletedProcess(cmd, code, stdout=out, stderr=err)

    def fake_run(self, cmd, **kwargs):
        if cmd[:2] == ['git', 'ls-remote']:
            return self.completed(cmd, out=self.SHA + '\trefs/heads/main\n')
        if cmd[0] != 'vcs':
            raise AssertionError('unexpected subprocess command: %r' % cmd)
        if kwargs.get('input') is None or 'src/lidar' in kwargs['input']:
            return self.completed(cmd, 1, err=self.BUG)
        return self.completed(cmd, 0, out='Found valid main branch')

    def test_advertised_branch_tip_accepted_after_strict_revalidation(self):
        with mock.patch.object(check_manifest.shutil, 'which',
                               return_value='/usr/bin/tool'), \
             mock.patch.object(check_manifest.subprocess, 'run',
                               side_effect=self.fake_run) as run:
            ok, detail = check_manifest.run_vcs_validate(self.manifest(other=True))
        self.assertTrue(ok, detail)
        self.assertIn('vcstool 0.3.0 tip bug', detail)
        self.assertIn('src/other: vcs validate passed', detail)
        self.assertTrue(any(call.args[0][:2] == ['git', 'ls-remote']
                            for call in run.call_args_list))

    def test_unknown_sha_does_not_pass_tip_workaround(self):
        manifest = self.manifest(version='abcdef0123456789abcdef0123456789abcdef01')
        with mock.patch.object(check_manifest.shutil, 'which',
                               return_value='/usr/bin/tool'), \
             mock.patch.object(check_manifest.subprocess, 'run',
                               side_effect=self.fake_run):
            ok, detail = check_manifest.run_vcs_validate(manifest)
        self.assertFalse(ok)
        self.assertIn('0 matching advertised ref-tip SHAs', detail)

    def test_other_invalid_repo_not_masked_by_lidar_tip_crash(self):
        def fake(cmd, **kwargs):
            if cmd[0] == 'vcs' and kwargs.get('input') and \
                    'src/other' in kwargs['input']:
                return self.completed(cmd, 0, out=(
                    "unable to verify non-branch / non-tag ref "
                    "'no-such-branch'"))
            return self.fake_run(cmd, **kwargs)

        with mock.patch.object(check_manifest.shutil, 'which',
                               return_value='/usr/bin/tool'), \
             mock.patch.object(check_manifest.subprocess, 'run',
                               side_effect=fake):
            ok, detail = check_manifest.run_vcs_validate(self.manifest(other=True))
        self.assertFalse(ok)
        self.assertIn('src/other', detail)
        self.assertIn('no-such-branch', detail)

    def test_non_hex_branch_cannot_use_commit_tip_workaround(self):
        with mock.patch.object(check_manifest.shutil, 'which',
                               return_value='/usr/bin/tool'), \
             mock.patch.object(check_manifest.subprocess, 'run',
                               side_effect=self.fake_run):
            ok, detail = check_manifest.run_vcs_validate(
                self.manifest(version='main'))
        self.assertFalse(ok)
        self.assertIn('requires a hexadecimal commit SHA', detail)

    def test_arbitrary_vcs_failure_never_triggers_workaround(self):
        def fake(cmd, **kwargs):
            return self.completed(cmd, 1, err='ERROR: network unreachable')

        with mock.patch.object(check_manifest.shutil, 'which',
                               return_value='/usr/bin/tool'), \
             mock.patch.object(check_manifest.subprocess, 'run',
                               side_effect=fake) as run:
            ok, detail = check_manifest.run_vcs_validate(self.manifest())
        self.assertFalse(ok)
        self.assertIn('network unreachable', detail)
        self.assertEqual(run.call_count, 1)



if __name__ == '__main__':
    unittest.main()
