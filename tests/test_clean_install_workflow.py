"""The documented CI environment has no display; every scene launch must be headless."""
import re
import shlex
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class CleanInstallWorkflowTests(unittest.TestCase):
    def test_every_scene_launch_is_headless(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/digital-twin-clean-install.yml').read_text(encoding='utf-8'))
        scripts = [step.get('run', '') for step in workflow['jobs']['install']['steps']]
        commands = []
        for script in scripts:
            script = script.replace(chr(92) + chr(10), ' ')
            commands.extend(re.findall(r'ros2 launch openamrobot_build1_scene build1[.]launch[.]py\s+([^>]+)>', script))
        self.assertEqual(len(commands), 2, 'Check both the initial scene and the fresh arm-demo launch')
        for index, arguments in enumerate(commands, start=1):
            with self.subTest(launch=index):
                self.assertIn('headless:=true', shlex.split(arguments), 'Gazebo must not try to open a GUI on the runner')

    def test_the_arm_demo_uses_the_engine_the_fast_profile_arms_are_qualified_with(self):
        text = (ROOT / '.github/workflows/digital-twin-clean-install.yml').read_text(encoding='utf-8')
        second = text[text.index('launch2.log') - 600:text.index('launch2.log')]
        self.assertIn('physics_engine:=gz-physics-bullet-featherstone-plugin', second)
        self.assertIn('run_scenario.py scn04_grasp', text)
        self.assertNotIn('run_scenario.py scn03_arms_reach', text)


if __name__ == '__main__':
    unittest.main()
