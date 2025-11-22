import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import logging

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from config import Config
from monitor import LaserMonitor

class TestLoggingConfig(unittest.TestCase):

    @patch('config.os.getenv')
    @patch('monitor.logging')
    def test_logging_level_debug(self, mock_logging, mock_getenv):
        # Mock env vars
        def getenv_side_effect(key, default=None):
            if key == 'LOG_LEVEL':
                return 'DEBUG'
            return default
        mock_getenv.side_effect = getenv_side_effect
        
        # Initialize monitor
        # We need to mock Config validation to pass
        with patch('config.Config.validate', return_value=(True, "")):
             monitor = LaserMonitor()
        
        # Check if basicConfig was called with DEBUG level
        mock_logging.basicConfig.assert_called()
        call_args = mock_logging.basicConfig.call_args
        self.assertEqual(call_args.kwargs['level'], mock_logging.DEBUG)

    @patch('config.os.getenv')
    @patch('monitor.logging')
    def test_logging_level_info_default(self, mock_logging, mock_getenv):
        # Mock env vars - LOG_LEVEL missing
        def getenv_side_effect(key, default=None):
            if key == 'LOG_LEVEL':
                return default # Return default (INFO)
            return default
        mock_getenv.side_effect = getenv_side_effect
        
        # Initialize monitor
        with patch('config.Config.validate', return_value=(True, "")):
             monitor = LaserMonitor()
        
        # Check if basicConfig was called with INFO level
        mock_logging.basicConfig.assert_called()
        call_args = mock_logging.basicConfig.call_args
        self.assertEqual(call_args.kwargs['level'], mock_logging.INFO)

if __name__ == '__main__':
    unittest.main()
