from fastapi.testclient import TestClient
from src.backend.server import app
import unittest
from unittest.mock import patch, MagicMock

client = TestClient(app)

class TestBeathaBackend(unittest.TestCase):
    
    def test_status_endpoint_structure(self):
        """Test that /api/status returns the correct JSON structure."""
        response = client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("drone_connected", data)
        self.assertIn("mode", data)
        self.assertIn("wifi_ip", data)

    @patch("os.path.exists")
    def test_drone_detection_true(self, mock_exists):
        """Test that status reflects drone connection."""
        mock_exists.return_value = True # Simulate /dev/ttyACM0 exists
        response = client.get("/api/status")
        self.assertEqual(response.json()["drone_connected"], True)

    @patch("os.path.exists")
    def test_drone_detection_false(self, mock_exists):
        """Test that status reflects drone disconnection."""
        mock_exists.return_value = False 
        response = client.get("/api/status")
        self.assertEqual(response.json()["drone_connected"], False)

    def test_list_dumps(self):
        """Test the dump listing endpoint."""
        with patch("glob.glob") as mock_glob:
            mock_glob.return_value = ["/home/pi/dumps/dump_1.txt", "/home/pi/dumps/dump_2.txt"]
            response = client.get("/api/dumps")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["files"], ["dump_1.txt", "dump_2.txt"])

if __name__ == "__main__":
    unittest.main()
