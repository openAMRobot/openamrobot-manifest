# OA-06 source-driver validation

Date: 2026-10-19. Parent SHA (OA-39 PR #17):
`3e619a88cc8cfafdb51673700a96eff2b69d7df2`.
The final head SHA is recorded in the PR description.

## Source selection

Both the development and rc.1 manifests now include:

- `src/sllidar_ros2`: SLAMTEC sllidar_ros2 at
  `34300099fadfc772965962dec837bf436706188f`, reusing PR #11's selection.
- `src/micro_ros_agent`: micro-ROS-Agent Jazzy at
  `7c932329ad5591ef23942ef1962534258c16b000`.

All 13 shared source entries agree with the OA-05 candidate in release PR #12.
The original 11 development branches and checkout paths are unchanged.

## Environment and commands

Started from official `ros:jazzy-ros-base`, immutable image reference
`ros@sha256:c3706ef0a0aa45413c07803cf433602f543b22e45b4855f6fca955c2d8ecc4e8`.
Installed the documented build/import tools and yamllint, then initialized
the Jazzy rosdep index. The prepared dependency image contains no built
driver overlay; source import and compilation ran in a fresh workspace.

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_manifest.py openamrobot.repos
bash tools/verify_jazzy_drivers.sh releases/v2.0.0-rc.1.repos /tmp/oa06-workspace /manifest/evidence-local/jazzy
python3 tools/check_release_manifest.py releases/v2.0.0-rc.1.repos --development openamrobot.repos --exact-export evidence-local/jazzy/exact.repos
```

The helper runs these build/dependency/discovery commands after source import:

```sh
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src/sllidar_ros2 src/micro_ros_agent --ignore-src --rosdistro jazzy -y
rosdep check --from-paths src/sllidar_ros2 src/micro_ros_agent --ignore-src --rosdistro jazzy
colcon build --base-paths src/sllidar_ros2 src/micro_ros_agent --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
ros2 pkg executables sllidar_ros2
ros2 pkg executables micro_ros_agent
```

## Results

- **28 tests pass**, zero failures, on Linux/Python 3.12.3. Final run: 4.896 s.
- Development YAML/schema and remote validation all pass. Both pinned commits
  are verified by an exact fetch; branch refs retain vcs validation.
- Fresh import succeeds. [Exact export](exact.repos) matches all 13 pins.
- Root package discovery succeeds with 20 entries, including both drivers.
  [Discovery output](colcon-list.txt) retains the known duplicate UI package.
- Driver rosdep install and check both exit 0. See
  [install log](rosdep-install.log) and [check result](rosdep-check.txt).
  `micro_ros_msgs` resolves through apt; no additional source entry is needed.
- **Both source drivers build successfully**: micro_ros_agent 6 min 33 s,
  sllidar_ros2 35.6 s; total 7 min 10 s. See [build log](build.log).
  Upstream clone messages and SDK compiler warnings appear on stderr; they
  are preserved and did not fail the build.
- Installed executables: [sllidar_node and sllidar_client](sllidar-executables.txt),
  [micro_ros_agent](agent-executables.txt). No node or hardware was started.

## Regression and fault injection

Ran the required-driver-entry test against parent PR #17's manifests: one
test runs and fails both driver subcases because the entries are absent.
The same test passes after the change. New tests also prove pinned entries
are excluded from the buggy vcs validation path, requested SHAs are passed
to Git, mismatched commits fail, and failed fetches or missing Git fail.

An initial mounted Windows-worktree run failed branch validation because Git
inherited an invalid host worktree path. The final checker runs validation
in an isolated temporary directory; the complete remote stage then passes.
No check was skipped or weakened to obtain the passing result.

## Not verified

This is a build/install check for the selected drivers, not full-workspace
or physical robot acceptance. OA-08's duplicate openamr_ui_msgs remains visible
under src and ui; the three UI ROS packages remain outside src. UI rosdep
declarations are not repaired by this PR. Firmware communication, LiDAR scans
and physical operation are not tested.

Upstream micro-ROS superbuild dependencies are downloaded during compilation
(Micro-XRCE-DDS-Agent v2.4.3 and spdlog 1.9.2). The manifest pins top-level
source entries; this is not evidence of a hermetic/reproducible binary build.
Hosted CI and owner acceptance are reported separately from local results.

## Integration, dependencies and AI disclosure

Stacked on OA-39 PR #17. Reuses PR #11's LiDAR revision without closing or
superseding that PR. Resolves pinned-ref validation needed for issue #12;
branch/tag checks remain active. The dedicated workflow uses the tested
official image digest; migration to PR #13's shared candidate awaits adoption.

SLAMTEC's package declares BSD; its original LICENSE and bundled SDK notices
remain upstream. micro-ROS-Agent is Apache-2.0 with its upstream third-party
notices. Only source references are added, and no upstream code or licence
files are modified. Existing Python validation dependencies are unchanged.

OpenAI Codex prepared the manifest entries, validation fix, tests, CI/helper,
documentation and evidence. No safety implementation was authored or modified.
