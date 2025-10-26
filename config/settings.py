"""
Configuration settings for the AutomateWhat application.
"""

import os
from pathlib import Path


class AppConfig:
    """Application configuration class."""
    
    def __init__(self):
        """Initialize configuration with default values."""
        self.app_name = "AutomateWhat"
        self.version = "1.0.0"
        self.author = "Your Name"
        
        # Paths
        self.root_dir = Path(__file__).parent.parent
        self.frontend_dir = self.root_dir / "frontend"
        self.backend_dir = self.root_dir / "backend"
        self.config_dir = self.root_dir / "config"
        self.utils_dir = self.root_dir / "utils"
        self.models_dir = self.root_dir / "models"
        self.assets_dir = self.root_dir / "assets"
        self.docs_dir = self.root_dir / "docs"
        self.tests_dir = self.root_dir / "tests"
        
        # GUI Settings
        self.window_width = 1200
        self.window_height = 800
        self.window_title = f"{self.app_name} v{self.version}"
        
        # Theme settings
        self.theme = "whatsapp_dark"  # whatsapp_dark, light
        self.colors = {
            "whatsapp_dark": {
                "bg": "#111B21",
                "fg": "#E9EDEF",
                "primary": "#00A884",
                "secondary": "#202C33",
                "accent": "#53BDEB",
                "success": "#4CAF50",
                "warning": "#FF9800",
                "error": "#F44336",
                "info": "#2196F3"
            },
            "light": {
                "bg": "#ffffff",
                "fg": "#000000",
                "primary": "#0078d4",
                "secondary": "#f3f2f1",
                "accent": "#106ebe"
            }
        }
        
        # Model settings
        self.model_paths = {
            "yolo": "../yolo_models/message_detector.pt",
            "qwen": "../hf_models/qwen2",
            "tinyllama": "../hf_models/tinyllama"
        }
        
        # Logging settings
        self.log_level = "INFO"
        self.log_file = self.root_dir / "logs" / "app.log"
        
        # Create necessary directories
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.log_file.parent,
            self.models_dir,
            self.assets_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_color(self, color_name):
        """Get color value for current theme."""
        return self.colors[self.theme].get(color_name, "#000000")
    
    def set_theme(self, theme):
        """Set the application theme."""
        if theme in self.colors:
            self.theme = theme
        else:
            raise ValueError(f"Invalid theme: {theme}")
