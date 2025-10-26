"""
Logging utilities for the AutomateWhat application.
"""

import logging
import os
from pathlib import Path
from datetime import datetime


def setup_logger(name="AutomateWhat", level="INFO"):
    """
    Setup and configure the application logger.
    
    Args:
        name (str): Logger name
        level (str): Logging level
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler for detailed logs
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler for simple logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(simple_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
