# OA-39 validation evidence

Date: 2026-10-19.
Base SHA: `7fbe540d95fdd2861d506fc104cb7f3f5e7f1fa3`.
The final head SHA is recorded in the PR description.

The development manifest and its existing tests are unchanged. All 11 release
entries retain their checkout paths and source URLs and use full commit SHAs.
The shared pins match openamrobot-release PR #12's candidate snapshot.

## Commands and results

Ran in a fresh container using local image `issue8-imported:local`, image ID
`sha256:eb767a40095afd38cf325afb6898859aaf8ee5b72d3f6952ddf7babaa33d6538`,
with Python 3.12.3, vcstool, colcon and Ubuntu's yamllint installed:

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_manifest.py --offline openamrobot.repos
python3 tools/check_manifest.py --offline releases/v2.0.0-rc.1.repos
python3 tools/check_release_manifest.py releases/v2.0.0-rc.1.repos --development openamrobot.repos
mkdir -p /tmp/oa39-workspace
vcs import /tmp/oa39-workspace < releases/v2.0.0-rc.1.repos
vcs export --exact /tmp/oa39-workspace > evidence-local/rc1-exact.repos
python3 tools/check_release_manifest.py releases/v2.0.0-rc.1.repos --exact-export evidence-local/rc1-exact.repos
cd /tmp/oa39-workspace
colcon list
```

- **22 tests pass**, zero failures: 14 existing tests and 8 new release tests.
- Both YAML/schema checks pass. Their remote stage is explicitly SKIPPED;
  the fresh import/export below is the separate network check.
- Development coverage/source checks and full-SHA checks pass.
- Fresh import exits 0. All 11 exported revisions exactly match the release.
  The captured export is [rc1-exact.repos](rc1-exact.repos).
- Package discovery exits 0: 18 entries, including the duplicate package below.
  The captured output is [colcon-list.txt](colcon-list.txt).
- Windows: all 8 new release tests pass. The initial full suite fails because
  yamllint is missing from PATH (9 environment-dependent failures); the Linux
  suite above passes with the dependency installed. No checks were weakened.

## Regression and deliberate faults

The regression test replaces one full SHA with `main`. The unchanged generic
schema validator accepts that input; the release checker rejects it. Additional
tests reject tags, abbreviated hashes, duplicate keys, malformed paths/URLs,
missing versions, missing repositories, different source URLs and a changed
SHA in an exact export. Export ordering differences are accepted.

## Not verified

No full workspace build, driver installation, physical hardware or release
acceptance is claimed. Discovery includes three UI packages outside `src/`:
`openamr_ui_bringup`, `openamr_ui_msgs` and `openamr_ui_package`. The duplicate
`openamr_ui_msgs` also exists under `src/openamrobot-interfaces`; OA-08 remains
unresolved by this work. No packages are hidden or ignored.

OA-06 driver additions and the final rc.1 component selection remain separate.
Hosted workflow results are reported in the PR, separately from this local run.

## Dependencies, integration and AI disclosure

No repository, dependency, licence or development branch selection changes.
The new tooling reuses the existing PyYAML strict loader, schema validator and
vcstool. Existing CI tooling versions remain unchanged. PR #11 (LiDAR sources)
and #13 (CI image pin) were inspected; neither is superseded. No inaccessible
work or owner acceptance is asserted. No safety implementation changes.

OpenAI Codex prepared the pinned manifest, checker, tests, CI extension,
documentation and evidence. The source pins come from the verified OA-05
candidate and were independently imported here.
