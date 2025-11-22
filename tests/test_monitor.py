import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call
import socket
import json

# Mock dependencies before importing monitor
mock_paho = MagicMock()
mock_mqtt = MagicMock()
mock_paho.mqtt = mock_mqtt
mock_mqtt.client = MagicMock()
sys.modules["paho"] = mock_paho
sys.modules["paho.mqtt"] = mock_mqtt
sys.modules["paho.mqtt.client"] = MagicMock()

sys.modules["requests"] = MagicMock()

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from monitor import LaserMonitor
from config import Config

class TestLaserMonitor(unittest.TestCase):
    @patch('monitor.Config')
    def setUp(self, mock_config_cls):
        # Mock config
        self.mock_config = MagicMock()
        self.mock_config.validate.return_value = (True, "")
        self.mock_config.mqtt_enabled = True
        self.mock_config.ha_enabled = True
        self.mock_config.ha_discovery_prefix = "homeassistant"
        self.mock_config.ha_node_id = "laserlink"
        self.mock_config.ha_device_name = "Laser Cutter"
        self.mock_config.mqtt_topic = "laser/status"
        
        self.mock_config.telegram_enabled = True
        self.mock_config.bluetooth_mac = "00:11:22:33:44:55"
        self.mock_config.rfcomm_port = 1
        self.mock_config.polling_interval = 0.1
        self.mock_config.framing_threshold = 20
        self.mock_config.max_spindle_speed = 1000 # Default GRBL max
        self.mock_config.show_raw = False
        self.mock_config.telegram_message_started = "Job Started"
        self.mock_config.telegram_message_completed = "Job Done"
        
        mock_config_cls.return_value = self.mock_config
        
    def test_parse_laser_power(self):
        # Configure manual mock
        import paho.mqtt.client as mock_mqtt_module
        mock_client_instance = MagicMock()
        mock_mqtt_module.Client.return_value = mock_client_instance
        
        with patch('monitor.Config', return_value=self.mock_config):
            monitor = LaserMonitor()
            
            # Test 2.5% power (25 RPM / 1000 * 100)
            line = "<Run|MPos:0,0,0|FS:100,25|A:S>"
            data = monitor.parse_response(line)
            self.assertEqual(data["spindle_speed"], 25)
            self.assertEqual(data["laser_power_pct"], 2.5)
            
            # Test 100% power
            line = "<Run|MPos:0,0,0|FS:100,1000|A:S>"
            data = monitor.parse_response(line)
            self.assertEqual(data["laser_power_pct"], 100.0)

    def test_ha_discovery_sensors(self):
        # Configure manual mock
        import paho.mqtt.client as mock_mqtt_module
        mock_client_instance = MagicMock()
        mock_mqtt_module.Client.return_value = mock_client_instance
        
        with patch('monitor.Config', return_value=self.mock_config):
            monitor = LaserMonitor()
            monitor.publish_ha_discovery()
            
            # Verify specific sensors are published
            calls = mock_client_instance.publish.call_args_list
            
            # Check for "Laser Power" instead of "Spindle Speed"
            power_call = next((c for c in calls if "sensor/laserlink/laser_power/config" in c[0][0]), None)
            self.assertIsNotNone(power_call)
            payload = json.loads(power_call[0][1])
            self.assertEqual(payload["name"], "Laser Cutter Laser Power")
            self.assertEqual(payload["unit_of_measurement"], "%")
            
            # Check for "Speed" instead of "Feed Rate"
            speed_call = next((c for c in calls if "sensor/laserlink/speed/config" in c[0][0]), None)
            self.assertIsNotNone(speed_call)
            payload = json.loads(speed_call[0][1])
            self.assertEqual(payload["name"], "Laser Cutter Speed")
            
            # Check Z axis is GONE
            z_call = next((c for c in calls if "sensor/laserlink/pos_z/config" in c[0][0]), None)
            self.assertIsNone(z_call, "Position Z should not be published")

if __name__ == '__main__':
    unittest.main()
