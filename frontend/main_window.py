"""
Main window for the AutomateWhat GUI application.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

from frontend.layout import MainLayout


class MainWindow:
    """Main application window."""
    
    def __init__(self, root, config):
        """
        Initialize the main window.
        
        Args:
            root: Tkinter root window
            config: Application configuration
        """
        self.root = root
        self.config = config
        self.logger = logging.getLogger("AutomateWhat")
        
        self._setup_window()
        self._create_layout()
        
        self.logger.info("Main window initialized with WhatsApp theme")
    
    def _setup_window(self):
        """Setup the main window properties."""
        self.root.title(self.config.window_title)
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.root.minsize(1200, 800)
        
        # Center the window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.config.window_width // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.config.window_height // 2)
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}+{x}+{y}")
        
        # Set window icon and properties
        self.root.configure(bg='#111B21')  # WhatsApp dark background
        
        # Make window resizable
        self.root.resizable(True, True)
    
    def _create_layout(self):
        """Create the main application layout."""
        self.layout = MainLayout(self.root, self.config)
    
    def update_status(self, message, status_type="info"):
        """Update the status label."""
        self.layout.status_text.config(text=message)
        self.logger.info(f"Status updated: {message}")
        
        # Update status indicator color
        if status_type == "success":
            self.layout.status_indicator.config(fg="#4CAF50")
        elif status_type == "error":
            self.layout.status_indicator.config(fg="#F44336")
        elif status_type == "warning":
            self.layout.status_indicator.config(fg="#FF9800")
        else:
            self.layout.status_indicator.config(fg="#2196F3")
    
    def show_error(self, title, message):
        """Show an error message."""
        messagebox.showerror(title, message)
        self.logger.error(f"Error shown: {title} - {message}")
    
    def show_info(self, title, message):
        """Show an info message."""
        messagebox.showinfo(title, message)
        self.logger.info(f"Info shown: {title} - {message}")
    
    def show_progress(self, show=True):
        """Show or hide the main progress bar."""
        if show:
            self.layout.main_progress.pack(side='right', padx=20, pady=10)
        else:
            self.layout.main_progress.pack_forget()
    
    def get_model_manager(self):
        """Get the model manager instance."""
        return self.layout.model_manager
    
    def get_loaded_model(self):
        """Get the currently loaded model."""
        return self.layout.get_loaded_model()
    
    def get_model_status(self):
        """Get current model status."""
        return self.layout.get_model_status()
