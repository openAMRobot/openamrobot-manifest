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
snapshot dated 2026-10-19. All 13 entries use full 40-character commit SHAs and
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
Both manifests now include the OA-06 driver sources; the release bundle also
includes a separately pinned governance export.

This snapshot is not final rc.1 acceptance. Package discovery exposes the known
duplicate `openamr_ui_msgs` under `src/` and `ui/` (OA-08); the manifest does not
hide UI packages or resolve that build issue. Updating a release snapshot
requires a reviewed PR with explicit replacement SHAs and fresh exact-export
evidence. Future release versions should get their own `.repos` file.

## Jazzy source drivers (OA-06)

Both manifests include these source-only dependencies:

| Package / checkout path | Upstream | Pinned commit |
|---|---|---|
| `sllidar_ros2` / `src/sllidar_ros2` | [SLAMTEC](https://github.com/Slamtec/sllidar_ros2) | `34300099fadfc772965962dec837bf436706188f` |
| `micro_ros_agent` / `src/micro_ros_agent` | [micro-ROS Jazzy](https://github.com/micro-ROS/micro-ROS-Agent/tree/jazzy) | `7c932329ad5591ef23942ef1962534258c16b000` |

For these packages, source import replaces attempts to install the driver
itself through apt or a rosdep rule. Rosdep still installs their declared
dependencies; `--ignore-src` recognizes packages present in the workspace.

On Ubuntu 24.04 with ROS 2 Jazzy installed, prepare the build tools and index:

```sh
sudo apt-get update
sudo apt-get install build-essential cmake git python3-colcon-common-extensions python3-rosdep python3-vcstool python3-yaml
# Run once if /etc/ros/rosdep/sources.list.d/20-default.list is absent:
sudo rosdep init
rosdep update --rosdistro jazzy
```

From this manifest repository, build and verify the drivers in a new workspace:

```sh
bash tools/verify_jazzy_drivers.sh releases/v2.0.0-rc.1.repos ~/oamr_driver_ws ~/oamr_driver_evidence
```

This imports the complete release manifest and records an exact export and
root package discovery. It then runs rosdep install/check and colcon build
with explicit base paths for the two drivers, sources their installation,
and confirms that `sllidar_node` and `micro_ros_agent` executables are installed.
It does not hide other packages or start hardware. The selected driver build
does not establish that the full workspace builds; OA-08 and the UI dependency
declarations remain separate issues.

The SLAMTEC package declares BSD; retain its original LICENSE and bundled SDK
notices. micro-ROS-Agent is Apache-2.0 and retains its third-party notices.
Only repository references are added here. The micro-ROS upstream superbuild
downloads further dependencies during compilation; these source pins do not
claim a hermetic or reproducible binary build.

## Validate the manifest

Requires Python 3 with PyYAML, `yamllint` and `vcstool`:

    python3 -m unittest discover -s tests -v
    python3 tools/check_manifest.py openamrobot.repos

`check_manifest.py` reports three stages separately: `yamllint` (syntax, duplicate keys), `strict` (duplicate-key-rejecting loader and manifest structure) and `remote` (branch/tag checks with `vcs validate`, full-SHA checks with an exact Git fetch and commit verification). Remote checks need network; `--offline` reports them as SKIPPED. These checks do not import a workspace, discover packages or build; run `vcs import`, `colcon list` and `colcon build` for those.

Part of the OpenAMRobot ecosystem: https://github.com/openAMRobot

## Ownership, licensing, and contributions

OpenAMRobot is a project initiated, operated, and controlled by **Botshare LTD** (Cyprus Company ID HE479056). Botshare LTD owns the transferable economic rights in original OpenAMRobot material created by or validly assigned to it. Third-party material remains subject to its respective ownership, licences, and notices.

Original OpenAMRobot software and firmware are licensed under MIT, documentation under CC BY 4.0, and hardware design source under CERN-OHL-P-2.0, as mapped in [`LICENSING.md`](LICENSING.md). Public distribution grants the permissions stated in the applicable licence; it does not transfer ownership of underlying copyright, trademarks, patents, or other intellectual property.

Accepted external contributions require DCO sign-off and an applicable Individual or Corporate Contributor Agreement. See the organization [IP Policy](https://github.com/openAMRobot/.github/blob/main/IP_POLICY.md), [Contribution Guide](https://github.com/openAMRobot/.github/blob/main/CONTRIBUTING.md), and [Contributor Agreement Process](https://github.com/openAMRobot/.github/blob/main/CLA.md).
