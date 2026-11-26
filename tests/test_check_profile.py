import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_profile import (ACCEPTANCE_WORKFLOW, PINS_FILE, acceptance_mismatches, duplicate_providers,
                           package_providers, release_mismatches)
from check_release_manifest import load_release

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'releases/v2.0.0-rc.1-digital-twin.repos'
RELEASE = ROOT / 'releases/v2.0.0-rc.1.repos'
A, B = 'a' * 40, 'b' * 40


def entry(version, url='https://example.invalid/x.git'):
    return {'type': 'git', 'url': url, 'version': version}


def package(root, relative, name):
    directory = Path(root) / relative
    directory.mkdir(parents=True)
    (directory / 'package.xml').write_text(f'<package format="3"><name>{name}</name></package>')
    return directory


def upperbody(root, pins, workflow):
    root = Path(root)
    (root / PINS_FILE).parent.mkdir(parents=True)
    (root / PINS_FILE).write_text('pins:\n' + ''.join(f'  {key}:\n    sha: "{sha}"\n' for key, sha in pins.items()))
    (root / ACCEPTANCE_WORKFLOW).parent.mkdir(parents=True)
    (root / ACCEPTANCE_WORKFLOW).write_text('env:\n' + ''.join(f'  {key}: {sha}\n' for key, sha in workflow.items()))
    return root


def full_profile(version=A):
    return {name: entry(version) for name in ('src/openamr-platform-sw', 'src/openamrobot-interfaces',
                                              'src/upstream/openarm_description', 'src/upstream/openarm_ros2',
                                              'src/upstream/openarm_can')}


def full_pins(version=A):
    return {key: version for key in ('platform_sw_main', 'platform_sw_sil', 'openamrobot_interfaces',
                                     'openarm_description', 'openarm_ros2', 'openarm_can')}


class ShippedProfileTests(unittest.TestCase):
    def test_profile_has_immutable_refs_and_agrees_with_the_release_manifest(self):
        profile = load_release(PROFILE)
        self.assertEqual(release_mismatches(profile, load_release(RELEASE)), [])

    def test_profile_is_the_supported_runtime_and_nothing_else(self):
        self.assertEqual(set(load_release(PROFILE)), {
            'src/openamr-upperbody-sw', 'src/openamr-platform-sw', 'src/openamrobot-interfaces',
            'src/upstream/openarm_description', 'src/upstream/openarm_ros2', 'src/upstream/openarm_can'})


class ReleaseAgreementTests(unittest.TestCase):
    def test_a_shared_entry_with_another_commit_is_reported(self):
        errors = release_mismatches({'src/x': entry(A)}, {'src/x': entry(B)})
        self.assertEqual(len(errors), 1)
        self.assertIn('src/x: profile version', errors[0])

    def test_an_entry_only_in_the_profile_is_allowed(self):
        self.assertEqual(release_mismatches({'src/only-here': entry(A)}, {'src/x': entry(B)}), [])


class AcceptanceAgreementTests(unittest.TestCase):
    def test_matching_pins_and_workflow_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = upperbody(tmp, full_pins(), {'PLATFORM_SW_SHA': A, 'INTERFACES_SHA': A})
            self.assertEqual(acceptance_mismatches(full_profile(), root), [])

    def test_a_stale_platform_pin_in_the_profile_is_reported_twice_from_pins_and_once_from_the_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = upperbody(tmp, full_pins(), {'PLATFORM_SW_SHA': A, 'INTERFACES_SHA': A})
            profile = full_profile()
            profile['src/openamr-platform-sw'] = entry(B)
            errors = acceptance_mismatches(profile, root)
            self.assertEqual(len(errors), 3, errors)
            self.assertTrue(all('src/openamr-platform-sw' in error for error in errors))

    def test_a_missing_runtime_dependency_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = upperbody(tmp, full_pins(), {'PLATFORM_SW_SHA': A, 'INTERFACES_SHA': A})
            profile = full_profile()
            del profile['src/upstream/openarm_can']
            self.assertEqual(acceptance_mismatches(profile, root),
                             ['src/upstream/openarm_can: required by the acceptance configuration, missing from the profile'])

    def test_a_workflow_without_the_pin_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = upperbody(tmp, full_pins(), {'INTERFACES_SHA': A})
            errors = acceptance_mismatches(full_profile(), root)
            self.assertEqual(len(errors), 1)
            self.assertIn('PLATFORM_SW_SHA: expected exactly one', errors[0])


class PackageProviderTests(unittest.TestCase):
    def test_two_providers_of_one_package_name_are_reported_with_both_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            package(tmp, 'src/interfaces/ros2/openamr_ui_msgs', 'openamr_ui_msgs')
            package(tmp, 'ui/openamrobot-ui/ros2/src/openamr_ui_msgs', 'openamr_ui_msgs')
            package(tmp, 'src/platform/ros2/src/openamrobot_nav2', 'openamrobot_nav2')
            self.assertEqual(duplicate_providers(tmp), {'openamr_ui_msgs': [
                'src/interfaces/ros2/openamr_ui_msgs/package.xml', 'ui/openamrobot-ui/ros2/src/openamr_ui_msgs/package.xml']})

    def test_ignored_and_generated_directories_do_not_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            package(tmp, 'src/a/pkg', 'pkg')
            ignored = package(tmp, 'src/b/pkg', 'pkg')
            (ignored.parent / 'COLCON_IGNORE').write_text('')
            package(tmp, 'install/pkg/share/pkg', 'pkg')
            package(tmp, 'build/pkg', 'pkg')
            self.assertEqual(duplicate_providers(tmp), {})
            self.assertEqual(package_providers(tmp), {'pkg': ['src/a/pkg/package.xml']})

    def test_a_package_inside_a_package_is_not_searched(self):
        with tempfile.TemporaryDirectory() as tmp:
            outer = package(tmp, 'src/a/outer', 'outer')
            package(outer, 'test/fixture', 'outer')
            self.assertEqual(duplicate_providers(tmp), {})


if __name__ == '__main__':
    unittest.main()
