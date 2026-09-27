#!/usr/bin/env python3
"""Validate a vcstool workspace manifest (openamrobot.repos).

Stages, reported separately:
  1. yamllint  - YAML syntax with key-duplicates enabled (offline)
  2. strict    - strict loader rejecting duplicate keys, plus semantic checks
                 on the manifest structure (offline)
  3. remote    - `vcs validate`: every URL is reachable and its version
                 exists; a non-hex version vcs cannot find is an error
                 (network; skipped only with --offline)

A missing tool is an error, not a pass. Import (`vcs import`), package
discovery (`colcon list`) and builds are separate checks not run here.

Usage: tools/check_manifest.py [--offline] [MANIFEST]
"""

import argparse
import posixpath
import re
import shutil
import subprocess
import sys

import yaml

YAMLLINT_CONFIG = (
    '{extends: relaxed, rules: {key-duplicates: enable, line-length: disable}}'
)
ALLOWED_TYPES = {'git'}
REPO_FIELDS = {'type', 'url', 'version'}
# vcstool 0.3.0 exits 0 when a version is neither a branch, a tag nor an
# advertised hash, since it may be an older commit. Only a hex string can be.
UNVERIFIED_REF = re.compile(
    r"unable to verify non-branch / non-tag ref '([^']*)'")
COMMIT_LIKE = re.compile(r'^[0-9a-f]{7,40}$')


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (safe_load keeps the last)."""


def _construct_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    seen = {}
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                'while constructing a mapping', node.start_mark,
                'found duplicate key %r (first defined at line %d)'
                % (key, seen[key].line + 1), key_node.start_mark)
        seen[key] = key_node.start_mark
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def semantic_errors(data):
    """Return a list of structural problems in a loaded manifest."""
    if not isinstance(data, dict) or set(data) != {'repositories'}:
        return ["top level must be a mapping with only a 'repositories' key"]
    repos = data['repositories']
    if not isinstance(repos, dict) or not repos:
        return ["'repositories' must be a non-empty mapping"]

    errors = []
    paths = []
    for path, entry in repos.items():
        where = 'repository %r' % (path,)
        if not isinstance(path, str) or not path:
            errors.append('%s: path must be a non-empty string' % where)
            continue
        norm = posixpath.normpath(path)
        if (path.startswith('/') or norm != path
                or norm == '..' or norm.startswith('../')):
            errors.append(
                '%s: path must be relative and normalized, without ".."'
                % where)
        # A key such as 'a:{ type: git, ... }' that PyYAML reads as a plain
        # scalar would surface here as a path containing ':' or '{'.
        if any(c in path for c in ':{}[], '):
            errors.append('%s: path contains YAML/flow characters' % where)
        if not isinstance(entry, dict):
            errors.append('%s: entry must be a mapping' % where)
            continue
        missing = REPO_FIELDS - set(entry)
        unknown = set(entry) - REPO_FIELDS
        if missing:
            errors.append('%s: missing %s' % (where, ', '.join(sorted(missing))))
        if unknown:
            errors.append('%s: unknown %s' % (where, ', '.join(sorted(unknown))))
        if 'type' in entry and entry['type'] not in ALLOWED_TYPES:
            errors.append('%s: type must be one of %s'
                          % (where, ', '.join(sorted(ALLOWED_TYPES))))
        for field in ('url', 'version'):
            value = entry.get(field)
            if field in entry and (not isinstance(value, str) or not value.strip()):
                errors.append('%s: %s must be a non-empty string' % (where, field))
        url = entry.get('url')
        if isinstance(url, str) and not url.startswith('https://'):
            errors.append('%s: url must use https://' % where)
        paths.append(path)

    for a in paths:
        for b in paths:
            if a != b and b.startswith(a + '/'):
                errors.append('repository %r is nested inside %r' % (b, a))
    return errors


def run_yamllint(manifest):
    if shutil.which('yamllint') is None:
        return False, 'yamllint not found on PATH (install yamllint)'
    proc = subprocess.run(
        ['yamllint', '-f', 'parsable', '-d', YAMLLINT_CONFIG, manifest],
        capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def run_strict(manifest):
    try:
        with open(manifest, encoding='utf-8') as stream:
            data = yaml.load(stream, Loader=StrictLoader)
    except (OSError, yaml.YAMLError) as exc:
        return False, str(exc)
    errors = semantic_errors(data)
    if errors:
        return False, '\n'.join(errors)
    return True, '%d repositories' % len(data['repositories'])


def missing_refs(vcs_output):
    """Versions vcs could not find that cannot be commit hashes."""
    return [ref for ref in UNVERIFIED_REF.findall(vcs_output)
            if not COMMIT_LIKE.match(ref)]


def run_vcs_validate(manifest):
    if shutil.which('vcs') is None:
        return False, 'vcs not found on PATH (install vcstool)'
    with open(manifest, encoding='utf-8') as stream:
        proc = subprocess.run(
            ['vcs', 'validate', '--retry', '2'], stdin=stream,
            capture_output=True, text=True, timeout=600)
    output = proc.stdout + proc.stderr
    if proc.returncode == 0:
        # Drop vcstool's pkg_resources deprecation noise; keep it on failure.
        output = '\n'.join(
            line for line in output.splitlines()
            if 'pkg_resources' not in line)
    missing = missing_refs(output)
    if missing:
        output += '\nversion is not a branch, tag or commit hash: ' + \
            ', '.join(missing)
    return proc.returncode == 0 and not missing, output.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('manifest', nargs='?', default='openamrobot.repos')
    parser.add_argument(
        '--offline', action='store_true',
        help='skip the network stage (vcs validate); reported as SKIPPED')
    args = parser.parse_args(argv)

    stages = [('yamllint', run_yamllint), ('strict', run_strict)]
    if not args.offline:
        stages.append(('remote', run_vcs_validate))

    ok = True
    for name, check in stages:
        passed, detail = check(args.manifest)
        print('[%s] %s' % ('PASS' if passed else 'FAIL', name))
        if detail:
            print('\n'.join('    ' + line for line in detail.splitlines()))
        ok = ok and passed
    if args.offline:
        print('[SKIPPED] remote (vcs validate) - --offline given')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
