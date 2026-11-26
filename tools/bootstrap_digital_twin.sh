#!/usr/bin/env bash
# Supported installation of the OpenAMRobot Digital Twin v2.0.0-rc.1 on Ubuntu 24.04 (noble), x86_64.
# ROS 2 Jazzy, Gazebo Harmonic, CycloneDDS. The commands and the pinned versions are those of the Baseline 1
# acceptance workflow of openamr-upperbody-sw. Safe to run again: every step is idempotent.
#
#   bash tools/bootstrap_digital_twin.sh [WORKSPACE] [PROFILE]
#
# WORKSPACE defaults to ~/oamr_dt_ws, PROFILE to releases/v2.0.0-rc.1-digital-twin.repos beside this script.
# Needs sudo for apt. Simulation only: nothing here is hardware, physical acceptance or safety evidence.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${1:-$HOME/oamr_dt_ws}"
PROFILE="$(realpath "${2:-$HERE/../releases/v2.0.0-rc.1-digital-twin.repos}")"
RELEASE="$HERE/../releases/v2.0.0-rc.1.repos"

ROS_APT_SOURCE_VERSION=1.3.0
GZ_SIM_VENDOR=0.0.13-1noble.20261031.125555
GZ_TOOLS_VENDOR=0.0.8-1noble.20261025.230735
SDFORMAT_VENDOR=0.0.14-1noble.20261031.120928
PACKAGES="openamrobot_build1_scene openamrobot_station_alignment"

step() { printf '\n=== %s\n' "$*"; }

step "1/6 ROS 2 Jazzy from packages.ros.org"
sudo apt-get update
sudo apt-get install -y curl locales software-properties-common python3-pip
sudo add-apt-repository -y universe
if ! dpkg -s ros2-apt-source > /dev/null 2>&1; then
  curl --fail --location --retry 5 --retry-delay 5 -o /tmp/ros2-apt-source.deb \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.noble_all.deb"
  sudo dpkg -i /tmp/ros2-apt-source.deb
fi
sudo apt-get update
sudo apt-get install -y ros-jazzy-ros-base ros-dev-tools python3-vcstool
sudo rosdep init 2> /dev/null || echo "rosdep init: already initialized"

step "2/6 Gazebo Harmonic, pinned vendor builds"
sudo apt-mark unhold ros-jazzy-gz-sim-vendor ros-jazzy-gz-tools-vendor ros-jazzy-sdformat-vendor > /dev/null 2>&1 || true
sudo apt-get install -y --allow-downgrades \
  "ros-jazzy-gz-sim-vendor=${GZ_SIM_VENDOR}" "ros-jazzy-gz-tools-vendor=${GZ_TOOLS_VENDOR}" "ros-jazzy-sdformat-vendor=${SDFORMAT_VENDOR}"
sudo apt-mark hold ros-jazzy-gz-sim-vendor ros-jazzy-gz-tools-vendor ros-jazzy-sdformat-vendor

step "3/6 Import the pinned sources into ${WORKSPACE}"
mkdir -p "$WORKSPACE"
vcs import "$WORKSPACE" < "$PROFILE"
vcs export --exact "$WORKSPACE" > "$WORKSPACE/exact.repos"
python3 "$HERE/check_release_manifest.py" "$PROFILE" --exact-export "$WORKSPACE/exact.repos"
python3 "$HERE/check_profile.py" "$PROFILE" --release "$RELEASE" --workspace "$WORKSPACE"

step "4/6 Dependencies"
# shellcheck disable=SC1091
set +u; source /opt/ros/jazzy/setup.bash; set -u
cd "$WORKSPACE"
rosdep update --rosdistro jazzy
# shellcheck disable=SC2086
paths=$(colcon list --base-paths src --packages-up-to $PACKAGES --paths-only)
# shellcheck disable=SC2086
rosdep install --rosdistro jazzy --from-paths $paths --ignore-src -y -r
sudo apt-get install -y python3-can ros-jazzy-ros-gz ros-jazzy-gz-ros2-control ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
  ros-jazzy-moveit ros-jazzy-joint-state-publisher ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-rviz2 iproute2 can-utils
sudo apt-get install -y "linux-modules-extra-$(uname -r)" || echo "linux-modules-extra-$(uname -r) not installed: the firmware_sil profile needs the vcan module"

step "5/6 Build"
# shellcheck disable=SC2086
colcon build --base-paths src --packages-up-to $PACKAGES --event-handlers console_cohesion+

step "6/6 Done"
cat <<EOF
Workspace: $WORKSPACE
Exact sources: $WORKSPACE/exact.repos

In every new terminal:
  source /opt/ros/jazzy/setup.bash
  source $WORKSPACE/install/setup.bash
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  export CYCLONEDDS_URI='<CycloneDDS><Domain Id="any"><Discovery><MaxAutoParticipantIndex>120</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'

Start the twin with RViz (needs the five virtual CAN interfaces, set up once per boot):
  ros2 run openamrobot_build1_scene setup_vcan_all.sh
  ros2 launch openamrobot_build1_scene build1.launch.py rviz:=true

Without virtual CAN (no firmware in the loop):
  ros2 launch openamrobot_build1_scene build1.launch.py profile:=fast rviz:=true

Run a scenario against the running launch, in a second terminal:
  ros2 run openamrobot_build1_scene run_scenario.py --list
  ros2 run openamrobot_build1_scene run_scenario.py scn01_drive
EOF
