#!/usr/bin/env python3
"""
AutomateWhat - WhatsApp AI Pipeline GUI Application
Main entry point for the application.

This application provides a graphical interface for the WhatsApp AI pipeline,
allowing users to interact with the AI models through an intuitive GUI.
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frontend.main_window import MainWindow
from config.settings import AppConfig
from utils.logger import setup_logger


def main():
    """
    Main entry point for the AutomateWhat application.
    """
    try:
        # Enable DPI awareness on Windows to handle high DPI displays correctly
        try:
            import ctypes
            # Tell Windows we are DPI aware
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
        except Exception as e:
            # Not on Windows or DPI awareness already set
            pass
        
        # Setup logging
        logger = setup_logger()
        logger.info("Starting AutomateWhat Application")
        
        # Load configuration
        config = AppConfig()
        config.window_width = 1400
        config.window_height = 700
        
        # Create and configure the main window
        root = tk.Tk()
        app = MainWindow(root, config)
        
        # Start the GUI event loop
        logger.info("GUI initialized successfully")
        root.mainloop()
        
    except Exception as e:
        # Handle any critical errors
        error_msg = f"Failed to start application: {str(e)}"
        print(error_msg)
        
        # Try to show error in GUI if possible
        try:
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            messagebox.showerror("Application Error", error_msg)
        except:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()
