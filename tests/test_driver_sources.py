"""Regression coverage for source-only Jazzy drivers and SHA validation."""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check_manifest


class DriverSourceTests(unittest.TestCase):
    def test_both_drivers_are_pinned_in_both_manifests(self):
        manifests = [yaml.safe_load((ROOT / name).read_text())['repositories']
                     for name in ('openamrobot.repos', 'releases/v2.0.0-rc.1.repos')]
        expected = {'src/sllidar_ros2': 'https://github.com/Slamtec/sllidar_ros2.git',
                    'src/micro_ros_agent': 'https://github.com/micro-ROS/micro-ROS-Agent.git'}
        for name, url in expected.items():
            with self.subTest(name=name):
                self.assertIn(name, manifests[0])
                self.assertEqual(manifests[0][name], manifests[1][name])
                self.assertEqual(manifests[0][name]['url'], url)
                self.assertRegex(manifests[0][name]['version'], r'^[0-9a-f]{40}$')

    def test_pinned_sources_do_not_reach_broken_vcs_validate(self):
        with patch.object(check_manifest, 'verify_pinned_commit', return_value=(True, 'verified')), \
                patch.object(check_manifest.shutil, 'which', return_value='/usr/bin/vcs'), \
                patch.object(check_manifest.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
            passed, _ = check_manifest.run_vcs_validate(ROOT / 'openamrobot.repos')
        self.assertTrue(passed)
        sent = yaml.safe_load(run.call_args.kwargs['input'])['repositories']
        self.assertNotIn('src/sllidar_ros2', sent)
        self.assertNotIn('src/micro_ros_agent', sent)
        self.assertEqual(len(sent), 11)

    def test_failed_pin_fails_remote_stage(self):
        with patch.object(check_manifest, 'verify_pinned_commit', return_value=(False, 'fetch failed')):
            passed, detail = check_manifest.run_vcs_validate(ROOT / 'openamrobot.repos')
        self.assertFalse(passed)
        self.assertIn('fetch failed', detail)

    def test_exact_git_fetch_verifies_commit(self):
        entry = {'url': 'https://github.com/example/driver.git', 'version': 'a' * 40}
        with patch.object(check_manifest.shutil, 'which', return_value='/usr/bin/git'), \
                patch.object(check_manifest.subprocess, 'run', side_effect=[
                    subprocess.CompletedProcess([], 0, '', ''),
                    subprocess.CompletedProcess([], 0, '', ''),
                    subprocess.CompletedProcess([], 0, entry['version'] + '\n', '')]) as run:
            self.assertTrue(check_manifest.verify_pinned_commit(entry)[0])
            fetch = run.call_args_list[1].args[0]
            self.assertEqual(fetch[-2:], [entry['url'], entry['version']])

    def test_commit_mismatch_rejected(self):
        entry = {'url': 'https://github.com/example/driver.git', 'version': 'a' * 40}
        with patch.object(check_manifest.shutil, 'which', return_value='/usr/bin/git'), \
                patch.object(check_manifest.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'b' * 40, '')):
            passed, detail = check_manifest.verify_pinned_commit(entry)
        self.assertFalse(passed)
        self.assertIn('does not match', detail)

    def test_fetch_error_or_missing_git_not_reported_as_pass(self):
        entry = {'url': 'https://github.com/example/driver.git', 'version': 'a' * 40}
        with patch.object(check_manifest.shutil, 'which', return_value=None):
            self.assertFalse(check_manifest.verify_pinned_commit(entry)[0])
        with patch.object(check_manifest.shutil, 'which', return_value='/usr/bin/git'), \
                patch.object(check_manifest.subprocess, 'run', side_effect=subprocess.CalledProcessError(128, ['git'], stderr='missing commit')):
            passed, detail = check_manifest.verify_pinned_commit(entry)
        self.assertFalse(passed)
        self.assertIn('missing commit', detail)
