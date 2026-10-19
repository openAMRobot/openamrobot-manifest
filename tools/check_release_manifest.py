"""Validate immutable release refs, source coverage and a vcs exact export."""
import argparse
import re
from pathlib import Path

import yaml
from check_manifest import StrictLoader, semantic_errors


def load_release(path):
    data = yaml.load(Path(path).read_text(encoding='utf-8'), Loader=StrictLoader)
    errors = semantic_errors(data)
    if errors:
        raise ValueError('\n'.join(errors))
    for name, entry in data['repositories'].items():
        if not re.fullmatch(r'[0-9a-f]{40}', entry['version']):
            raise ValueError(f'{name}: release version must be a full commit SHA')
    return data['repositories']


def check_development(release, path):
    data = yaml.load(Path(path).read_text(encoding='utf-8'), Loader=StrictLoader)
    errors = semantic_errors(data)
    if errors:
        raise ValueError('\n'.join(errors))
    development = data['repositories']
    if set(release) != set(development):
        raise ValueError('release/development repository coverage mismatch')
    for name, entry in release.items():
        if any(entry[field] != development[name][field] for field in ('type', 'url')):
            raise ValueError(f'{name}: release/development source mismatch')


def check_export(release, path):
    exported = load_release(path)
    if release != exported:
        raise ValueError('exact export does not match release manifest')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    parser.add_argument('--development', type=Path)
    parser.add_argument('--exact-export', type=Path)
    args = parser.parse_args()
    repos = load_release(args.manifest)
    if args.development:
        check_development(repos, args.development)
        print('PASS development coverage and sources')
    if args.exact_export:
        check_export(repos, args.exact_export)
        print('PASS exact export matches all release pins')
    print(f'PASS immutable refs: {len(repos)} repositories')


if __name__ == '__main__':
    main()
