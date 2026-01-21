import sys
from unittest.mock import MagicMock

# MOCK pyudev BEFORE importing server.py
# This prevents the CI from crashing if libudev is missing/broken
mock_pyudev = MagicMock()
sys.modules["pyudev"] = mock_pyudev

from fastapi.testclient import TestClient
from src.backend.server import app, manager
import unittest
from unittest.mock import patch

client = TestClient(app)

class TestBeathaBackend(unittest.TestCase):

    def setUp(self):
        # Reset manager state before each test
        manager.drone_connected = False
        manager.state = "IDLE"

    def test_status_endpoint_structure(self):
        """Test that /api/status returns the correct JSON structure."""
        response = client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("drone_connected", data)
        self.assertIn("mode", data)
        self.assertIn("wifi_ip", data)

    def test_drone_detection_true(self):
        """Test that status reflects drone connection."""
        # Manually set the state in the singleton manager
        manager.drone_connected = True
        response = client.get("/api/status")
        self.assertEqual(response.json()["drone_connected"], True)

    def test_drone_detection_false(self):
        """Test that status reflects drone disconnection."""
        manager.drone_connected = False
        response = client.get("/api/status")
        self.assertEqual(response.json()["drone_connected"], False)

    def test_list_dumps(self):
        """Test the dump listing endpoint."""
        with patch("glob.glob") as mock_glob:
            # glob returns full paths
            mock_glob.return_value = ["/home/pi/dumps/dump_1.txt", "/home/pi/dumps/dump_2.txt"]

            # Need to patch os.path.getmtime to avoid errors during sort
            with patch("os.path.getmtime") as mock_mtime:
                mock_mtime.return_value = 1000.0

                response = client.get("/api/dumps")
                self.assertEqual(response.status_code, 200)
                # The implementation returns basenames
                self.assertEqual(response.json()["files"], ["dump_1.txt", "dump_2.txt"])

if __name__ == "__main__":
    unittest.main()
