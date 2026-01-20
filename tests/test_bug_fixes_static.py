"""
Static code analysis tests for critical bug fixes
These tests don't require importing modules with hardware dependencies
"""

import unittest
import os
import re


class TestBugFixesStatic(unittest.TestCase):
    """Static analysis of bug fixes in source code"""

    def setUp(self):
        """Setup file paths"""
        self.test_dir = os.path.dirname(__file__)
        self.project_root = os.path.dirname(self.test_dir)
        self.server_path = os.path.join(self.project_root, 'src', 'backend', 'server.py')
        self.main_path = os.path.join(self.project_root, 'src', 'main.py')
        self.config_loader_path = os.path.join(self.project_root, 'src', 'backend', 'config_loader.py')

    def test_no_flush_input_in_server(self):
        """server.py should not use deprecated flushInput"""
        with open(self.server_path, 'r') as f:
            content = f.read()

        self.assertNotIn('flushInput', content,
                        "server.py should not use deprecated flushInput method")
        self.assertIn('reset_input_buffer', content,
                     "server.py should use reset_input_buffer instead")

    def test_no_flush_input_in_main(self):
        """main.py should not use deprecated flushInput"""
        with open(self.main_path, 'r') as f:
            content = f.read()

        self.assertNotIn('flushInput', content,
                        "main.py should not use deprecated flushInput method")
        self.assertIn('reset_input_buffer', content,
                     "main.py should use reset_input_buffer instead")

    def test_config_path_is_absolute(self):
        """config_loader.py should use absolute path for CONFIG_PATH"""
        with open(self.config_loader_path, 'r') as f:
            content = f.read()

        # Should NOT have: CONFIG_PATH = "config.json"
        self.assertNotIn('CONFIG_PATH = "config.json"', content,
                        "Should not use relative path for config")

        # Should have: os.path.join with __file__
        self.assertIn('os.path.join', content,
                     "Should use os.path.join for path construction")
        self.assertIn('__file__', content,
                     "Should use __file__ for absolute path resolution")

    def test_state_lock_created(self):
        """BeathaManager should create a state_lock"""
        with open(self.server_path, 'r') as f:
            content = f.read()

        self.assertIn('self.state_lock = threading.Lock()', content,
                     "BeathaManager should create state_lock")

    def test_state_lock_used_in_trigger_dump(self):
        """trigger_dump should use state_lock"""
        with open(self.server_path, 'r') as f:
            content = f.read()

        # Check for: with self.state_lock:
        self.assertIn('with self.state_lock:', content,
                     "Should use 'with self.state_lock:' for locking")

    def test_stop_socat_waits_for_process(self):
        """stop_socat should call wait() with timeout"""
        with open(self.server_path, 'r') as f:
            content = f.read()

        # Find the stop_socat method
        stop_socat_match = re.search(
            r'def stop_socat\(self\):.*?(?=\n    def |\nclass |\Z)',
            content,
            re.DOTALL
        )

        self.assertIsNotNone(stop_socat_match, "stop_socat method should exist")
        stop_socat_code = stop_socat_match.group(0)

        self.assertIn('.wait(timeout=', stop_socat_code,
                     "stop_socat should call wait() with timeout")
        self.assertIn('except subprocess.TimeoutExpired:', stop_socat_code,
                     "stop_socat should handle TimeoutExpired")
        self.assertIn('.kill()', stop_socat_code,
                     "stop_socat should kill process on timeout")

    def test_serial_uses_context_manager(self):
        """_perform_extraction should use 'with serial.Serial' context manager"""
        with open(self.server_path, 'r') as f:
            content = f.read()

        self.assertIn('with serial.Serial', content,
                     "Should use 'with serial.Serial' context manager")

    def test_serial_reading_uses_time_based_silence(self):
        """Serial reading should use time-based silence detection"""
        with open(self.server_path, 'r') as f:
            content = f.read()

        # Find the _perform_extraction method
        extraction_match = re.search(
            r'def _perform_extraction\(self\):.*?(?=\n    def |\nclass |\n# ---|\Z)',
            content,
            re.DOTALL
        )

        self.assertIsNotNone(extraction_match, "_perform_extraction method should exist")
        extraction_code = extraction_match.group(0)

        self.assertIn('silence_threshold', extraction_code,
                     "Should use silence_threshold constant")
        self.assertIn('last_data_time', extraction_code,
                     "Should track last_data_time for silence detection")

    def test_usb_monitor_loop_has_exception_handling(self):
        """_usb_monitor_loop should have try-except wrapper"""
        with open(self.server_path, 'r') as f:
            content = f.read()

        loop_match = re.search(
            r'def _usb_monitor_loop\(self\):.*?(?=\n    def )',
            content,
            re.DOTALL
        )

        self.assertIsNotNone(loop_match, "_usb_monitor_loop should exist")
        loop_code = loop_match.group(0)

        self.assertIn('try:', loop_code, "_usb_monitor_loop should have try block")
        self.assertIn('except Exception', loop_code,
                     "_usb_monitor_loop should catch Exception")
        self.assertIn('logger.error', loop_code,
                     "_usb_monitor_loop should log errors")

    def test_button_monitor_loop_has_exception_handling(self):
        """_button_monitor_loop should have try-except wrapper"""
        with open(self.server_path, 'r') as f:
            content = f.read()

        loop_match = re.search(
            r'def _button_monitor_loop\(self\):.*?(?=\n    def )',
            content,
            re.DOTALL
        )

        self.assertIsNotNone(loop_match, "_button_monitor_loop should exist")
        loop_code = loop_match.group(0)

        self.assertIn('try:', loop_code, "_button_monitor_loop should have try block")
        self.assertIn('except Exception', loop_code,
                     "_button_monitor_loop should catch Exception")

    def test_socat_manager_loop_has_exception_handling(self):
        """_socat_manager_loop should have try-except wrapper"""
        with open(self.server_path, 'r') as f:
            content = f.read()

        loop_match = re.search(
            r'def _socat_manager_loop\(self\):.*?(?=\n    def )',
            content,
            re.DOTALL
        )

        self.assertIsNotNone(loop_match, "_socat_manager_loop should exist")
        loop_code = loop_match.group(0)

        self.assertIn('try:', loop_code, "_socat_manager_loop should have try block")
        self.assertIn('except Exception', loop_code,
                     "_socat_manager_loop should catch Exception")

    def test_animation_loop_has_exception_handling(self):
        """_animation_loop should have try-except wrapper"""
        with open(self.server_path, 'r') as f:
            content = f.read()

        loop_match = re.search(
            r'def _animation_loop\(self\):.*?(?=\n    def |\n    # ---)',
            content,
            re.DOTALL
        )

        self.assertIsNotNone(loop_match, "_animation_loop should exist")
        loop_code = loop_match.group(0)

        self.assertIn('try:', loop_code, "_animation_loop should have try block")
        self.assertIn('except Exception', loop_code,
                     "_animation_loop should catch Exception")


if __name__ == '__main__':
    unittest.main()
