# Manifest state

## OA-06 source drivers

The development and rc.1 manifests now contain 13 entries, adding pinned
SLAMTEC sllidar_ros2 and the Jazzy micro-ROS-Agent. Their SHAs match the OA-05
candidate. The 11 original development branches are unchanged. This PR is
based on main after OA-39 PR #17 merged and reuses the LiDAR selection from PR #11.

Full-SHA remote checks now fetch and verify the commit directly, avoiding the
vcstool 0.3.0 branch-tip bug tracked in #12. Branch/tag checks still use vcs.
Both run independently of the caller's local Git worktree context.

The dedicated Jazzy check imports the complete release workspace, reports all
discovered packages, then resolves and builds only the two source drivers.
It never connects to robot hardware. Full workspace installation/build still
depends on the separate UI rosdep declarations and OA-08 duplicate-package fix.

## OA-39 baseline

OA-39 added `releases/v2.0.0-rc.1.repos` alongside the development
manifest. Its original 11 repositories retain their paths and URLs and use full commit
SHAs. The 2026-10-19 snapshot agrees with the shared component revisions in
openamrobot-release PR #12. That builder also includes the drivers and
a separately pinned governance source outside the workspace scope.

The snapshot demonstrates a pinned checkout, not rc.1 acceptance. The final
release selection requires owner review and updates as outstanding fixes land.
Manifest PR #11 proposes LiDAR source selection and is not superseded here.
PR #13 has merged its ci/ros2-image.txt baseline; that file is preserved.
The dedicated driver job still uses its recorded upstream ROS digest.

Integrated main at 80161e5 on 2026-10-28 after the #17 squash merge.
Conflict resolution retains the 13-entry manifests and driver instructions;
no source pins changed. Full 40-character pins bypass vcstool validation.
Abbreviated SHAs still use vcstool, so issue #12 is not claimed fully closed.

Validation separates YAML/schema, immutable refs, source import, exact export,
package discovery and component builds. No hardware or safety implementation
is changed. Full workspace build and robot acceptance remain unverified here.
