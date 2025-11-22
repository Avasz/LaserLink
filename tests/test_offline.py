import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
import json
import socket

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from monitor import LaserMonitor

class TestOfflineStatus(unittest.TestCase):

    @patch('monitor.Config')
    @patch('monitor.mqtt.Client')
    @patch('monitor.socket.socket')
    @patch('monitor.time.sleep') # Mock sleep to speed up test
    def test_publish_offline_on_socket_error(self, mock_sleep, mock_socket_cls, mock_mqtt_cls, mock_config_cls):
        # Setup Config
        mock_config = mock_config_cls.return_value
        mock_config.validate.return_value = (True, "")
        mock_config.mqtt_enabled = True
        mock_config.mqtt_topic = "laser/status"
        mock_config.bluetooth_mac = "00:00:00:00:00:00"
        mock_config.rfcomm_port = 1
        mock_config.log_level = "INFO"
        
        # Setup MQTT Client
        mock_mqtt_client = mock_mqtt_cls.return_value
        
        # Setup Socket to raise error on connect
        mock_socket = mock_socket_cls.return_value
        mock_socket.connect.side_effect = [socket.error("Host is down"), KeyboardInterrupt] # Fail once, then stop
        
        # Initialize Monitor
        monitor = LaserMonitor()
        
        # Run Monitor (will run loop once, hit error, then hit KeyboardInterrupt)
        try:
            monitor.run()
        except KeyboardInterrupt:
            pass
            
        # Verify publish was called with Offline status
        # We expect at least one publish call with "Offline"
        publish_calls = mock_mqtt_client.publish.call_args_list
        
        offline_published = False
        for args, _ in publish_calls:
            topic, payload = args
            if topic == "laser/status":
                data = json.loads(payload)
                if data.get("detailed_status") == "Offline" and data.get("state") == "Offline":
                    offline_published = True
                    break
        
        self.assertTrue(offline_published, "Offline status was not published to MQTT")

if __name__ == '__main__':
    unittest.main()
