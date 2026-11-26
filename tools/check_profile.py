"""Check a supported installation profile against the release manifest and an imported workspace.

Three checks, each of which stops a wrong release before any simulation is started:

1. Pin agreement with the release manifest: a repository that is in both files has the same URL and commit.
2. Pin agreement with the acceptance configuration: the commits that the upperbody acceptance workflow and its
   pins file name for the platform, the interfaces and the upstream arm packages are the commits of the profile.
3. Unique package providers: no ROS package name is provided by two package.xml files in the imported workspace.

A text and file check. It does not build or run anything and proves nothing about behaviour.
"""
import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from check_release_manifest import load_release

SKIP_DIRECTORIES = {'.git', 'build', 'install', 'log', 'node_modules'}
IGNORE_MARKERS = ('COLCON_IGNORE', 'AMENT_IGNORE')

# profile entry -> key in the upperbody pins file
PINS_FILE = 'ros2/src/openamrobot_build1_scene/config/pins.yaml'
ACCEPTANCE_WORKFLOW = '.github/workflows/baseline1-acceptance.yml'
PIN_KEYS = {
    'src/openamr-platform-sw': ('platform_sw_main', 'platform_sw_sil'),
    'src/openamrobot-interfaces': ('openamrobot_interfaces',),
    'src/upstream/openarm_description': ('openarm_description',),
    'src/upstream/openarm_ros2': ('openarm_ros2',),
    'src/upstream/openarm_can': ('openarm_can',),
}
MODEL_PINS_FILE = 'ros2/src/openamrobot_upperbody_description/config/upstream_pins.yaml'
WORKFLOW_VARIABLES = {
    'src/openamr-platform-sw': 'PLATFORM_SW_SHA',
    'src/openamrobot-interfaces': 'INTERFACES_SHA',
}


def release_mismatches(profile, release):
    """Entries present in both files must name the same source and commit."""
    errors = []
    for name, entry in profile.items():
        if name not in release:
            continue
        for field in ('type', 'url', 'version'):
            if entry[field] != release[name][field]:
                errors.append(f'{name}: profile {field} {entry[field]} differs from release manifest {release[name][field]}')
    return errors


def acceptance_mismatches(profile, upperbody_root):
    """The profile must pin what the acceptance workflow of the pinned upperbody commit builds."""
    errors = []
    root = Path(upperbody_root)
    pins = yaml.safe_load((root / PINS_FILE).read_text(encoding='utf-8'))['pins']
    workflow = (root / ACCEPTANCE_WORKFLOW).read_text(encoding='utf-8')
    for name, keys in PIN_KEYS.items():
        if name not in profile:
            errors.append(f'{name}: required by the acceptance configuration, missing from the profile')
            continue
        for key in keys:
            if key not in pins:
                errors.append(f'{key}: missing from {PINS_FILE}')
            elif pins[key]['sha'] != profile[name]['version']:
                errors.append(f"{name}: profile {profile[name]['version']} differs from pins.yaml {key} {pins[key]['sha']}")
    for name, variable in WORKFLOW_VARIABLES.items():
        found = re.findall(rf'^\s+{variable}:\s*([0-9a-f]{{40}})\s*$', workflow, flags=re.MULTILINE)
        if len(found) != 1:
            errors.append(f'{variable}: expected exactly one full commit in {ACCEPTANCE_WORKFLOW}, found {len(found)}')
        elif name in profile and found[0] != profile[name]['version']:
            errors.append(f"{name}: profile {profile[name]['version']} differs from workflow {variable} {found[0]}")
    return errors


def model_pin_differences(profile, upperbody_root):
    """The model and emulator tests of the upperbody commit build the platform commit named in
    upstream_pins.yaml. When that differs from the profile, those tests did not run on the candidate
    platform. Returned as text; the caller decides whether it is a note or an error."""
    path = Path(upperbody_root) / MODEL_PINS_FILE
    if not path.is_file() or 'src/openamr-platform-sw' not in profile:
        return []
    model_pin = yaml.safe_load(path.read_text(encoding='utf-8'))['pins'].get('openamr_platform_sw')
    candidate = profile['src/openamr-platform-sw']['version']
    if model_pin and model_pin != candidate:
        return [f'model and emulator tests build platform {model_pin} ({MODEL_PINS_FILE}), the profile pins {candidate}']
    return []


def package_providers(workspace):
    """Map package name -> package.xml paths, skipping what colcon skips."""
    providers = {}
    workspace = Path(workspace)
    stack = [workspace]
    while stack:
        directory = stack.pop()
        if any((directory / marker).exists() for marker in IGNORE_MARKERS):
            continue
        manifest = directory / 'package.xml'
        if manifest.is_file():
            name = ET.parse(manifest).getroot().findtext('name')
            if not name:
                raise ValueError(f'{manifest}: no <name>')
            providers.setdefault(name.strip(), []).append(str(manifest.relative_to(workspace)))
            continue  # a ROS package does not contain another package
        for child in sorted(directory.iterdir()):
            if child.is_dir() and not child.is_symlink() and child.name not in SKIP_DIRECTORIES:
                stack.append(child)
    return providers


def duplicate_providers(workspace):
    return {name: sorted(paths) for name, paths in package_providers(workspace).items() if len(paths) > 1}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile')
    parser.add_argument('--release', type=Path, help='full release manifest to compare shared entries with')
    parser.add_argument('--workspace', type=Path, help='directory the profile was imported into with vcs import')
    parser.add_argument('--upperbody', default='src/openamr-upperbody-sw',
                        help='profile entry whose acceptance configuration is compared (needs --workspace)')
    parser.add_argument('--strict-model-pin', action='store_true',
                        help='fail, instead of printing a note, when the model tests build another platform commit')
    args = parser.parse_args()

    profile = load_release(args.profile)
    errors = []
    if args.release:
        errors += release_mismatches(profile, load_release(args.release))
        print(f'checked {len(profile)} profile entries against {args.release}')
    if args.workspace:
        errors += acceptance_mismatches(profile, args.workspace / args.upperbody)
        differences = model_pin_differences(profile, args.workspace / args.upperbody)
        if args.strict_model_pin:
            errors += differences
        else:
            print('\n'.join('NOTE ' + difference for difference in differences), end='\n' if differences else '')
        providers = package_providers(args.workspace)
        duplicates = {name: paths for name, paths in providers.items() if len(paths) > 1}
        for name, paths in sorted(duplicates.items()):
            errors.append(f'{name}: provided by {len(paths)} packages: ' + ', '.join(paths))
        print(f'checked {len(providers)} package names in {args.workspace}')
    if errors:
        print('\n'.join('FAIL ' + error for error in errors))
        return 1
    print('PASS profile pins and package providers')
    return 0


if __name__ == '__main__':
    sys.exit(main())
