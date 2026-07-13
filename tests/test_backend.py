import sys
import os
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
            # glob is called twice (root + subdirs). Return files only for the first call.
            mock_glob.side_effect = [
                ["/home/pi/dumps/dump_1.txt", "/home/pi/dumps/dump_2.txt"],
                []
            ]

            # Need to patch os.path.getmtime to avoid errors during sort
            with patch("os.path.getmtime") as mock_mtime, \
                 patch("os.path.getsize") as mock_getsize, \
                 patch("os.path.relpath") as mock_relpath:
                mock_mtime.return_value = 1000.0
                mock_getsize.return_value = 1024
                # Mock relpath to return just the basename for simplicity
                mock_relpath.side_effect = lambda p, start: os.path.basename(p)

                response = client.get("/api/dumps")
                self.assertEqual(response.status_code, 200)

                # The implementation returns a list of objects
                files = response.json()["files"]
                self.assertEqual(len(files), 2)
                self.assertEqual(files[0]["filename"], "dump_1.txt")
                self.assertEqual(files[1]["filename"], "dump_2.txt")

    def test_sync_to_cloud_path_traversal(self):
        """Test that syncing a file with path traversal or absolute path returns 400."""
        # Test directory traversal with ..
        response = client.post("/api/cloud/sync", json={"filepath": "../etc/passwd"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid filepath")

        # Test absolute path bypass
        response = client.post("/api/cloud/sync", json={"filepath": "/etc/passwd"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid filepath")

    def test_download_blackbox_msc_path_traversal(self):
        """Test that downloading blackbox files from MSC with path traversal returns 400."""
        response = client.post("/api/fc/msc/download", json={"mount_path": "../etc"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid mount path")

    def test_exception_details_not_exposed(self):
        """Test that raw exception messages are not exposed to the user."""
        # 1. Test connect_serial with a mock that throws an exception
        with patch.object(manager, 'detect_fc_type', side_effect=Exception("Database connection credentials exposed!")):
            with patch("serial.tools.list_ports.comports") as mock_comports:
                mock_port = MagicMock()
                mock_port.device = "/dev/ttyACM0"
                mock_comports.return_value = [mock_port]

                response = client.post("/api/serial/connect", json={"port": "/dev/ttyACM0"})
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("warning", data)
                self.assertNotIn("Database connection credentials exposed!", data["warning"])
                self.assertEqual(data["warning"], "Internal connection error")

        # 2. Test analyze_dump with a mock that throws an exception
        with patch("src.backend.server.GEMINI_AVAILABLE", True), \
             patch("src.backend.server.genai", create=True) as mock_genai, \
             patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):  # pragma: allowlist secret
            mock_genai.configure.side_effect = Exception("Mocked LLM error!")
            # We patch os.path.exists to return True so it passes path checks
            with patch("os.path.exists", return_value=True), \
                 patch("builtins.open", unittest.mock.mock_open(read_data="Betaflight config")):
                response = client.post("/api/llm/analyze", json={"filepath": "dump_1.txt"})
                self.assertEqual(response.status_code, 500)
                self.assertNotIn("Mocked LLM error!", response.json()["detail"])
                self.assertEqual(response.json()["detail"], "Analysis failed due to an internal error")

        # 3. Test sync_to_cloud with a mock that throws an exception
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Mocked sync error!")
            with patch("os.path.exists", return_value=True):
                response = client.post("/api/cloud/sync", json={"filepath": "dump_1.txt"})
                self.assertEqual(response.status_code, 500)
                self.assertNotIn("Mocked sync error!", response.json()["detail"])
                self.assertEqual(response.json()["detail"], "Sync failed due to an internal error")

    def test_safe_path_validation(self):
        """Test that unified path sanitizer rejects invalid paths."""
        # Test get_dump with path traversal using %2F URL encoding so client doesn't resolve it
        response = client.get("/api/dumps/..%2Fetc%2Fpasswd")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid filepath")

        # Test get_dump with absolute path bypass
        response = client.get("/api/dumps/%2Fetc%2Fpasswd")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid filepath")

if __name__ == "__main__":
    unittest.main()
