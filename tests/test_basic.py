"""
Basic test for the AutomateWhat application.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import AppConfig
from utils.logger import setup_logger


class TestAutomateWhat(unittest.TestCase):
    """Test cases for AutomateWhat application."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = AppConfig()
        self.logger = setup_logger("TestLogger", "DEBUG")
    
    def test_config_initialization(self):
        """Test configuration initialization."""
        self.assertEqual(self.config.app_name, "AutomateWhat")
        self.assertEqual(self.config.version, "1.0.0")
        self.assertIsNotNone(self.config.root_dir)
        self.assertIsNotNone(self.config.colors)
    
    def test_theme_switching(self):
        """Test theme switching functionality."""
        # Test light theme
        self.config.set_theme("light")
        self.assertEqual(self.config.theme, "light")
        
        # Test dark theme
        self.config.set_theme("dark")
        self.assertEqual(self.config.theme, "dark")
        
        # Test invalid theme
        with self.assertRaises(ValueError):
            self.config.set_theme("invalid")
    
    def test_color_retrieval(self):
        """Test color retrieval for themes."""
        light_bg = self.config.get_color("bg")
        self.assertIsNotNone(light_bg)
        
        # Switch to dark theme
        self.config.set_theme("dark")
        dark_bg = self.config.get_color("bg")
        self.assertIsNotNone(dark_bg)
        
        # Colors should be different
        self.assertNotEqual(light_bg, dark_bg)
    
    def test_logger_setup(self):
        """Test logger setup."""
        logger = setup_logger("TestLogger", "INFO")
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "TestLogger")
    
    @patch('tkinter.Tk')
    def test_main_window_creation(self, mock_tk):
        """Test main window creation."""
        mock_root = MagicMock()
        mock_tk.return_value = mock_root
        
        # Import here to avoid tkinter issues in headless environments
        from frontend.main_window import MainWindow
        
        window = MainWindow(mock_root, self.config)
        self.assertIsNotNone(window)
        self.assertEqual(window.config, self.config)


if __name__ == "__main__":
    unittest.main()
