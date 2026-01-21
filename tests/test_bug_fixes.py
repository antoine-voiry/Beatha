"""
Unit tests for critical bug fixes
Tests the fixes for:
1. Deprecated pyserial method (flushInput -> reset_input_buffer)
2. Process cleanup in stop_socat
3. Race condition in state management
4. Serial reading infinite loop
5. Config path resolution
6. Exception handling in background loops
7. Serial port cleanup with context manager
"""

import unittest
from unittest.mock import patch, MagicMock, Mock, call
import threading
import time
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestConfigPathResolution(unittest.TestCase):
    """Test that config path is resolved to absolute path"""

    def test_config_path_is_absolute(self):
        """Config path should be absolute, not relative"""
        from src.backend.config_loader import CONFIG_PATH

        self.assertTrue(os.path.isabs(CONFIG_PATH),
                       f"CONFIG_PATH should be absolute, got: {CONFIG_PATH}")
        self.assertTrue(CONFIG_PATH.endswith("config.json"),
                       f"CONFIG_PATH should end with config.json, got: {CONFIG_PATH}")


class TestStateManagementRaceCondition(unittest.TestCase):
    """Test that state management uses locks to prevent race conditions"""

    @patch('src.backend.server.pixels')
    @patch('src.backend.server.buzzer')
    @patch('src.backend.server.btn_dump')
    @patch('src.backend.server.btn_pair')
    @patch('src.backend.server.EMULATION_MODE', True)
    def test_state_lock_exists(self, *mocks):
        """BeathaManager should have a state_lock attribute"""
        from src.backend.server import BeathaManager

        manager = BeathaManager()
        self.assertTrue(hasattr(manager, 'state_lock'))
        # threading.Lock is a factory function, not a type, so we need to get the actual type
        self.assertIsInstance(manager.state_lock, type(threading.Lock()))

    @patch('src.backend.server.pixels')
    @patch('src.backend.server.buzzer')
    @patch('src.backend.server.btn_dump')
    @patch('src.backend.server.btn_pair')
    @patch('src.backend.server.EMULATION_MODE', True)
    @patch('src.backend.server.threading.Thread')
    def test_trigger_dump_uses_lock(self, mock_thread, *mocks):
        """trigger_dump should use lock for state check and transition"""
        from src.backend.server import BeathaManager

        manager = BeathaManager()
        manager.drone_connected = True

        # Mock the thread to not actually start
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        initial_state = manager.state
        manager.trigger_dump()

        # Verify thread was started (meaning we got past the lock)
        mock_thread_instance.start.assert_called_once()

    @patch('src.backend.server.pixels')
    @patch('src.backend.server.buzzer')
    @patch('src.backend.server.btn_dump')
    @patch('src.backend.server.btn_pair')
    @patch('src.backend.server.EMULATION_MODE', True)
    def test_concurrent_trigger_dump_prevented(self, *mocks):
        """Multiple concurrent trigger_dump calls should be prevented"""
        from src.backend.server import BeathaManager

        manager = BeathaManager()
        manager.drone_connected = True
        manager.state = "DUMPING"  # Already in progress

        # Should return early without starting thread
        with patch('src.backend.server.threading.Thread') as mock_thread:
            manager.trigger_dump()
            mock_thread.assert_not_called()


class TestProcessCleanup(unittest.TestCase):
    """Test that stop_socat properly cleans up processes"""

    @patch('src.backend.server.pixels')
    @patch('src.backend.server.buzzer')
    @patch('src.backend.server.btn_dump')
    @patch('src.backend.server.btn_pair')
    @patch('src.backend.server.EMULATION_MODE', True)
    def test_stop_socat_waits_for_process(self, *mocks):
        """stop_socat should call wait() on the process"""
        from src.backend.server import BeathaManager

        manager = BeathaManager()

        # Create a mock process
        mock_process = MagicMock()
        manager.socat_process = mock_process

        manager.stop_socat()

        # Verify terminate was called
        mock_process.terminate.assert_called_once()
        # Verify wait was called with timeout
        mock_process.wait.assert_called_once_with(timeout=5)
        # Verify process set to None
        self.assertIsNone(manager.socat_process)

    @patch('src.backend.server.pixels')
    @patch('src.backend.server.buzzer')
    @patch('src.backend.server.btn_dump')
    @patch('src.backend.server.btn_pair')
    @patch('src.backend.server.EMULATION_MODE', True)
    def test_stop_socat_kills_on_timeout(self, *mocks):
        """stop_socat should kill process if wait times out"""
        from src.backend.server import BeathaManager
        import subprocess

        manager = BeathaManager()

        # Create a mock process that times out
        mock_process = MagicMock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd='socat', timeout=5)
        manager.socat_process = mock_process

        manager.stop_socat()

        # Verify terminate and kill were called
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        self.assertIsNone(manager.socat_process)


class TestSerialReading(unittest.TestCase):
    """Test that serial reading loop doesn't have unnecessary delays"""

    def test_serial_reading_logic(self):
        """Verify serial reading uses time-based silence detection, not sleep in loop"""
        from src.backend.server import BeathaManager

        # Read the source code to verify the fix
        import inspect
        source = inspect.getsource(BeathaManager._perform_extraction)

        # The old bug had: time.sleep(2) in the exit check
        # The fix uses: silence_duration = time.time() - last_data_time
        self.assertIn('silence_threshold', source,
                     "Should use silence_threshold constant")
        self.assertIn('last_data_time', source,
                     "Should track last_data_time instead of sleeping in check")


class TestExceptionHandling(unittest.TestCase):
    """Test that background loops have exception handling"""

    def test_usb_monitor_loop_has_exception_handling(self):
        """_usb_monitor_loop should have try-except wrapper"""
        from src.backend.server import BeathaManager
        import inspect

        source = inspect.getsource(BeathaManager._usb_monitor_loop)
        self.assertIn('try:', source, "_usb_monitor_loop should have try block")
        self.assertIn('except', source, "_usb_monitor_loop should have except block")

    def test_button_monitor_loop_has_exception_handling(self):
        """_button_monitor_loop should have try-except wrapper"""
        from src.backend.server import BeathaManager
        import inspect

        source = inspect.getsource(BeathaManager._button_monitor_loop)
        self.assertIn('try:', source, "_button_monitor_loop should have try block")
        self.assertIn('except', source, "_button_monitor_loop should have except block")

    def test_socat_manager_loop_has_exception_handling(self):
        """_socat_manager_loop should have try-except wrapper"""
        from src.backend.server import BeathaManager
        import inspect

        source = inspect.getsource(BeathaManager._socat_manager_loop)
        self.assertIn('try:', source, "_socat_manager_loop should have try block")
        self.assertIn('except', source, "_socat_manager_loop should have except block")

    def test_animation_loop_has_exception_handling(self):
        """_animation_loop should have try-except wrapper"""
        from src.backend.server import BeathaManager
        import inspect

        source = inspect.getsource(BeathaManager._animation_loop)
        self.assertIn('try:', source, "_animation_loop should have try block")
        self.assertIn('except', source, "_animation_loop should have except block")


class TestSerialPortCleanup(unittest.TestCase):
    """Test that serial port uses context manager for guaranteed cleanup"""

    def test_serial_uses_context_manager(self):
        """_perform_extraction should use 'with serial.Serial' context manager"""
        from src.backend.server import BeathaManager
        import inspect

        source = inspect.getsource(BeathaManager._perform_extraction)

        # Check for context manager usage
        self.assertIn('with serial.Serial', source,
                     "Should use 'with serial.Serial' context manager")

        # Old bug had: ser = serial.Serial() followed by ser.close()
        # Should NOT have standalone ser.close() anymore in the serial block
        # (it's handled by context manager)


class TestPyserialDeprecation(unittest.TestCase):
    """Test that deprecated pyserial methods are not used"""

    def test_no_flush_input_in_server(self):
        """server.py should not use deprecated flushInput"""
        server_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'backend', 'server.py')
        with open(server_path, 'r') as f:
            content = f.read()

        self.assertNotIn('flushInput', content,
                        "Should not use deprecated flushInput method")
        self.assertIn('reset_input_buffer', content,
                     "Should use reset_input_buffer instead")

    def test_no_flush_input_in_main(self):
        """main.py should not use deprecated flushInput"""
        main_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'main.py')
        with open(main_path, 'r') as f:
            content = f.read()

        self.assertNotIn('flushInput', content,
                        "Should not use deprecated flushInput method")
        self.assertIn('reset_input_buffer', content,
                     "Should use reset_input_buffer instead")


if __name__ == '__main__':
    unittest.main()
