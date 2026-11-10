"""Check that pins recorded inside pinned repositories agree with the release manifest.

openamr-upperbody-sw records the platform commit it is built against in
ros2/src/openamrobot_upperbody_description/config/upstream_pins.yaml. A release manifest
that pins a different platform commit would ship an upper body built against another base.

Usage, after `vcs import <workspace> < releases/<release>.repos`:
    python3 tools/check_upstream_pins.py releases/v2.0.0-rc.1.repos --workspace <workspace>
"""
import argparse
import sys
from pathlib import Path

import yaml
from check_release_manifest import load_release

# (repository holding the pins file, path inside it, pin key, manifest repository the key names)
CROSS_PINS = (
    ('src/openamr-upperbody-sw',
     'ros2/src/openamrobot_upperbody_description/config/upstream_pins.yaml',
     'openamr_platform_sw',
     'src/openamr-platform-sw'),
)


def cross_pin_errors(repos, workspace):
    errors = []
    for holder, rel, key, target in CROSS_PINS:
        if holder not in repos or target not in repos:
            continue
        path = Path(workspace) / holder / rel
        if not path.is_file():
            errors.append(f'{holder}: {rel} not found in the workspace (import the release first)')
            continue
        pins = (yaml.safe_load(path.read_text(encoding='utf-8')) or {}).get('pins') or {}
        recorded = str(pins.get(key, ''))
        expected = repos[target]['version']
        if recorded != expected:
            errors.append(f'{holder} pins {key} {recorded[:12] or "(missing)"}, '
                          f'the manifest pins {target} {expected[:12]}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('manifest')
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    errors = cross_pin_errors(load_release(args.manifest), args.workspace)
    for error in errors:
        print(f'FAIL {error}')
    if errors:
        sys.exit(1)
    print(f'PASS cross pins: {len(CROSS_PINS)} checked')


if __name__ == '__main__':
    main()
