#!/usr/bin/env bash
# Build source drivers in a new workspace; never connects to robot hardware.
set -eo pipefail
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 MANIFEST NEW_WORKSPACE EVIDENCE_DIR" >&2
  exit 2
fi
manifest=$(realpath "$1")
workspace=$(realpath -m "$2")
evidence=$(realpath -m "$3")
if [ -d "$workspace" ] && [ -n "$(ls -A "$workspace")" ]; then
  echo "Workspace must be new and empty" >&2
  exit 2
fi
mkdir -p "$workspace" "$evidence"
source /opt/ros/jazzy/setup.bash
vcs import "$workspace" < "$manifest" 2>&1 | tee "$evidence/import.log"
vcs export --exact "$workspace" > "$evidence/exact.repos"
cd "$workspace"
colcon list | tee "$evidence/colcon-list.txt"
driver_paths=(src/sllidar_ros2 src/micro_ros_agent)
rosdep install --from-paths "${driver_paths[@]}" --ignore-src --rosdistro jazzy -y 2>&1 | tee "$evidence/rosdep-install.log"
rosdep check --from-paths "${driver_paths[@]}" --ignore-src --rosdistro jazzy 2>&1 | tee "$evidence/rosdep-check.log"
colcon build --base-paths "${driver_paths[@]}" --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release 2>&1 | tee "$evidence/build.log"
source install/setup.bash
ros2 pkg executables sllidar_ros2 | tee "$evidence/sllidar-executables.txt"
ros2 pkg executables micro_ros_agent | tee "$evidence/agent-executables.txt"
grep -q '^sllidar_ros2 sllidar_node$' "$evidence/sllidar-executables.txt"
grep -q '^micro_ros_agent micro_ros_agent$' "$evidence/agent-executables.txt"
echo 'PASS: both pinned drivers built and installed; no hardware was started'
