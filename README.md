# openamrobot-manifest

Workspace manifest for the OpenAMRobot ecosystem: the repositories and versions that make up a full source checkout.

> **Status:** Active

## Assemble the workspace

    mkdir -p ~/oamr_ws && cd ~/oamr_ws
    vcs import . < /path/to/openamrobot.repos
    colcon build

ROS 2 packages land in `src/`; additional UI ROS packages are discovered under `ui/` when colcon runs at the workspace root. Firmware, hardware and docs use their own build procedures. Import and discovery do not establish that a full workspace build passes.

## Pinned release checkout (OA-39)

`openamrobot.repos` remains the development manifest and may track branches.
[`releases/v2.0.0-rc.1.repos`](releases/v2.0.0-rc.1.repos) is a separate candidate
snapshot dated 2026-10-19. All 11 entries use full 40-character commit SHAs and
retain the development manifest's repository URLs and checkout paths.

From this repository, validate the snapshot:

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_manifest.py --offline releases/v2.0.0-rc.1.repos
python3 tools/check_release_manifest.py releases/v2.0.0-rc.1.repos --development openamrobot.repos
```

Import into a **new, empty** workspace, then compare the exact checkout:

```sh
mkdir -p ~/oamr_rc1_ws
vcs import ~/oamr_rc1_ws < releases/v2.0.0-rc.1.repos
vcs export --exact ~/oamr_rc1_ws > /tmp/rc1-exact.repos
python3 tools/check_release_manifest.py releases/v2.0.0-rc.1.repos --exact-export /tmp/rc1-exact.repos
cd ~/oamr_rc1_ws
colcon list
```

The strict release checker rejects branches, tags and abbreviated hashes;
comparison with an exact export rejects changed, missing or extra repositories.
The network import/export stage is separate from offline YAML validation.
It also avoids the vcstool 0.3.0 `vcs validate` bug for advertised commit hashes
tracked in [issue #12](https://github.com/openAMRobot/openamrobot-manifest/issues/12).
Development validation retains its existing remote check.

The shared component pins agree with the OA-05 candidate in
[release PR #12](https://github.com/openAMRobot/openamrobot-release/pull/12).
That bundle also includes separately pinned drivers and governance. Adding
driver sources to this workspace is OA-06 and is handled separately.

This snapshot is not final rc.1 acceptance. Package discovery exposes the known
duplicate `openamr_ui_msgs` under `src/` and `ui/` (OA-08); the manifest does not
hide UI packages or resolve that build issue. Updating a release snapshot
requires a reviewed PR with explicit replacement SHAs and fresh exact-export
evidence. Future release versions should get their own `.repos` file.

## Validate the manifest

Requires Python 3 with PyYAML, `yamllint` and `vcstool`:

    python3 -m unittest discover -s tests -v
    python3 tools/check_manifest.py openamrobot.repos

`check_manifest.py` reports three stages separately: `yamllint` (syntax, duplicate keys), `strict` (duplicate-key-rejecting loader and manifest structure) and `remote` (`vcs validate`: URLs reachable, versions exist; needs network, `--offline` skips it and reports it as SKIPPED). These do not import, discover packages or build; run `vcs import`, `colcon list` and `colcon build` for those.

Part of the OpenAMRobot ecosystem: https://github.com/openAMRobot

## Ownership, licensing, and contributions

OpenAMRobot is a project initiated, operated, and controlled by **Botshare LTD** (Cyprus Company ID HE479056). Botshare LTD owns the transferable economic rights in original OpenAMRobot material created by or validly assigned to it. Third-party material remains subject to its respective ownership, licences, and notices.

Original OpenAMRobot software and firmware are licensed under MIT, documentation under CC BY 4.0, and hardware design source under CERN-OHL-P-2.0, as mapped in [`LICENSING.md`](LICENSING.md). Public distribution grants the permissions stated in the applicable licence; it does not transfer ownership of underlying copyright, trademarks, patents, or other intellectual property.

Accepted external contributions require DCO sign-off and an applicable Individual or Corporate Contributor Agreement. See the organization [IP Policy](https://github.com/openAMRobot/.github/blob/main/IP_POLICY.md), [Contribution Guide](https://github.com/openAMRobot/.github/blob/main/CONTRIBUTING.md), and [Contributor Agreement Process](https://github.com/openAMRobot/.github/blob/main/CLA.md).
