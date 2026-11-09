"""Fail-closed vcstool abbreviated-tip recovery; no network required."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import check_manifest as check

SHA = 'a' * 40
BUG = "UnboundLocalError: local variable 'version_type' referenced before assignment"


def result(code=0, out='', err=''):
    return subprocess.CompletedProcess([], code, out, err)


def entry(version):
    return {'type': 'git', 'url': 'https://example.com/repo.git', 'version': version}


class TipFallbackTests(unittest.TestCase):
    def run_manifest(self, repos, responses):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / 'workspace.repos'
            manifest.write_text(yaml.safe_dump({'repositories': repos}))
            calls = []

            def run(argv, **kwargs):
                calls.append((argv, kwargs))
                if argv[0] == 'vcs':
                    self.assertTrue(os.path.isdir(kwargs['cwd']))
                    self.assertNotEqual(os.path.realpath(kwargs['cwd']), os.getcwd())
                response = next(responses)
                if isinstance(response, Exception):
                    raise response
                return response

            with patch.object(check.shutil, 'which', return_value='/usr/bin/tool'), \
                    patch.object(check.subprocess, 'run', side_effect=run):
                passed, detail = check.run_vcs_validate(manifest)
        return passed, detail, calls

    def test_abbreviated_tip_recovers_in_isolated_directory(self):
        passed, detail, calls = self.run_manifest({'src/a': entry(SHA[:8])}, iter([
            result(1, err=BUG), result(1, err=BUG), result(out=SHA + '\trefs/heads/main\n')]))
        self.assertTrue(passed, detail)
        self.assertIn('advertised tip ' + SHA, detail)
        self.assertEqual(len(calls), 3)

    def test_full_sha_still_uses_exact_fetch_even_when_abbreviation_crashes(self):
        with patch.object(check, 'verify_pinned_commit', return_value=(True, 'verified')) as verify:
            passed, detail, calls = self.run_manifest(
                {'src/full': entry('b' * 40), 'src/short': entry(SHA[:8])}, iter([
                    result(1, err=BUG), result(1, err=BUG), result(out=SHA + '\trefs/heads/main\n')]))
        self.assertTrue(passed, detail)
        verify.assert_called_once_with(entry('b' * 40))
        for argv, kwargs in calls:
            if argv[0] == 'vcs':
                self.assertNotIn('src/full', yaml.safe_load(kwargs['input'])['repositories'])

    def test_bad_sibling_branch_cannot_hide_behind_tip_crash(self):
        passed, detail, _ = self.run_manifest(
            {'src/a': entry(SHA[:8]), 'src/b': entry('missing')}, iter([
                result(1, err=BUG), result(1, err=BUG), result(out=SHA + '\trefs/heads/main\n'),
                result(out="unable to verify non-branch / non-tag ref 'missing'")]))
        self.assertFalse(passed)
        self.assertIn('src/b', detail)

    def test_unrelated_vcs_failure_does_not_enable_fallback(self):
        passed, detail, calls = self.run_manifest({'src/a': entry(SHA[:8])}, iter([
            result(1, err='authentication failed')]))
        self.assertFalse(passed)
        self.assertEqual(len(calls), 1)

    def test_branch_named_like_nonhex_cannot_use_workaround(self):
        passed, detail, calls = self.run_manifest({'src/a': entry('main')}, iter([
            result(1, err=BUG), result(1, err=BUG)]))
        self.assertFalse(passed)
        self.assertIn('abbreviated', detail)
        self.assertEqual(len(calls), 2)

    def advertised(self, response, version=SHA[:8]):
        with patch.object(check.shutil, 'which', return_value='/usr/bin/git'), \
                patch.object(check.subprocess, 'run', side_effect=[response]):
            return check.validate_advertised_branch_tip('https://example.com/repo.git', version)

    def test_ambiguous_abbreviation_rejected(self):
        passed, detail = self.advertised(result(out=SHA + '\trefs/heads/a\n' +
            SHA[:8] + 'b' * 32 + '\trefs/heads/b\n'))
        self.assertFalse(passed)
        self.assertIn('2 matching', detail)

    def test_duplicate_refs_to_same_commit_are_not_ambiguous(self):
        self.assertTrue(self.advertised(result(out=SHA + '\trefs/heads/a\n' +
            SHA + '\trefs/heads/b\n'))[0])

    def test_unadvertised_abbreviation_rejected(self):
        self.assertFalse(self.advertised(result(out='b' * 40 + '\trefs/heads/main\n'))[0])

    def test_full_sha_not_accepted_by_abbreviated_fallback(self):
        self.assertFalse(self.advertised(result(out=SHA), version=SHA)[0])

    def test_ls_remote_failure_rejected(self):
        self.assertFalse(self.advertised(result(128, err='network unavailable'))[0])

    def test_ls_remote_timeout_rejected(self):
        self.assertFalse(self.advertised(subprocess.TimeoutExpired(['git'], 120))[0])

    def test_ls_remote_oserror_rejected(self):
        self.assertFalse(self.advertised(OSError('cannot execute git'))[0])

    def test_missing_git_rejected(self):
        with patch.object(check.shutil, 'which', return_value=None):
            self.assertFalse(check.validate_advertised_branch_tip('https://example.com', SHA[:8])[0])

    def test_fallback_vcs_timeout_rejected(self):
        passed, detail, _ = self.run_manifest({'src/a': entry(SHA[:8])}, iter([
            result(1, err=BUG), subprocess.TimeoutExpired(['vcs'], 120)]))
        self.assertFalse(passed)
        self.assertIn('vcstool invocation failed', detail)


if __name__ == '__main__':
    unittest.main()
