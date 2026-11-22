import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_upstream_pins import CROSS_PINS, cross_pin_errors

HOLDER, REL, KEY, TARGET = CROSS_PINS[0]
A, B = 'a' * 40, 'b' * 40


def repos(platform):
    return {HOLDER: {'version': 'c' * 40}, TARGET: {'version': platform}}


def workspace(tmp, recorded):
    path = Path(tmp) / HOLDER / REL
    path.parent.mkdir(parents=True)
    path.write_text(f'schema_version: 1\npins:\n  {KEY}: "{recorded}"\n')
    return tmp


class CrossPinTests(unittest.TestCase):
    def test_duplicate_upstream_keys_fail_closed(self):
        for text in (
            f'pins:\n  {KEY}: "{B}"\n  {KEY}: "{A}"\n',
            f'pins:\n  {KEY}: "{B}"\npins:\n  {KEY}: "{A}"\n',
        ):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                workspace(tmp, A)
                (Path(tmp) / HOLDER / REL).write_text(text, encoding='utf-8')
                self.assertRegex(' '.join(cross_pin_errors(repos(A), tmp)), 'duplicate key')

    def test_matching_pin_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(cross_pin_errors(repos(A), workspace(tmp, A)), [])

    def test_upperbody_built_against_other_platform_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = cross_pin_errors(repos(A), workspace(tmp, B))
        self.assertEqual(errors, [f'{HOLDER} pins {KEY} {B[:12]}, the manifest pins {TARGET} {A[:12]}'])

    def test_missing_pins_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertRegex(' '.join(cross_pin_errors(repos(A), tmp)), 'not found in the workspace')


if __name__ == '__main__':
    unittest.main()
