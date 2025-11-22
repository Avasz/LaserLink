import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from config import Config

class TestConfigDebug(unittest.TestCase):
    def test_yaml_enabled_env_token(self):
        # Scenario: 
        # config.yaml has enabled: True, but empty token
        # Environment has the token
        
        yaml_data = {
            'telegram': {
                'enabled': True,
                'bot_token': "",
                'chat_id': ""
            }
        }
        
        env_vars = {
            "TELEGRAM_BOT_TOKEN": "env_token_123",
            "TELEGRAM_CHAT_ID": "env_chat_id_456",
            "BLUETOOTH_MAC": "AA:BB:CC:DD:EE:FF"
        }
        
        with patch.dict(os.environ, env_vars):
            with patch('yaml.safe_load', return_value=yaml_data):
                with patch('os.path.exists', return_value=True):
                    with patch('builtins.open', unittest.mock.mock_open(read_data="data")):
                        cfg = Config("dummy.yaml")
                        
                        # Check if it picked up the env vars
                        self.assertEqual(cfg.telegram_token, "env_token_123")
                        self.assertEqual(cfg.telegram_chat_id, "env_chat_id_456")
                        self.assertTrue(cfg.telegram_enabled)
                        
                        # Validate should pass
                        valid, msg = cfg.validate()
                        self.assertTrue(valid, f"Validation failed: {msg}")

if __name__ == '__main__':
    unittest.main()
