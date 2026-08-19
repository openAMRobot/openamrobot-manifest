# openamrobot-manifest

Workspace manifest for the OpenAMRobot ecosystem: the repositories and versions that make up a full source checkout.

## Assemble the workspace

    mkdir -p ~/oamr_ws && cd ~/oamr_ws
    vcs import . < /path/to/openamrobot.repos
    colcon build

ROS 2 packages land in `src/` and build with colcon. Firmware, hardware, UI, and docs land in their own folders and are not part of the colcon build.

Part of the OpenAMRobot ecosystem: https://github.com/openAMRobot
