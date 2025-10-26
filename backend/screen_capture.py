"""
Screen Capture Manager for AutomateWhat application.
Handles screenshot capture, area selection, and live preview.
"""

import os
import sys
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Tuple, Callable
from datetime import datetime
import numpy as np

# Try to import PIL for screenshots
try:
    from PIL import Image, ImageGrab
    from PIL import ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageGrab = None
    ImageTk = None

# Try to import mss for faster screenshots
try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    mss = None


class ScreenCaptureManager:
    """Manages screen capture and area selection."""
    
    def __init__(self, config):
        """
        Initialize the screen capture manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger("AutomateWhat.ScreenCapture")
        
        # Capture settings
        self.selected_area: Optional[dict] = None  # {x, y, width, height}
        self.is_recording = False
        self.capture_interval = 2  # seconds
        self.capture_thread: Optional[threading.Thread] = None
        self.stop_capturing = threading.Event()
        
        # Screenshot storage
        self.screenshot_dir = self.config.root_dir / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
        self.screenshot_path = self.screenshot_dir / "current_screenshot.png"
        
        # Callbacks
        self.on_screenshot_captured: Optional[Callable] = None
        self.on_area_selected: Optional[Callable] = None
        
        self.logger.info("Screen Capture Manager initialized")
    
    def set_selected_area(self, x: int, y: int, width: int, height: int):
        """
        Set the selected recording area.
        
        Args:
            x: X position
            y: Y position
            width: Width
            height: Height
        """
        self.selected_area = {
            'x': x,
            'y': y,
            'width': width,
            'height': height
        }
        
        self.logger.info(f"Selected area set: x={x}, y={y}, width={width}, height={height}")
        self.logger.info(f"Area dimensions: {width}x{height} pixels at position ({x}, {y})")
        
        if self.on_area_selected:
            self.on_area_selected(self.selected_area)
    
    def get_selected_area(self) -> Optional[dict]:
        """
        Get the selected recording area.
        
        Returns:
            Selected area dictionary or None
        """
        return self.selected_area
    
    def has_selected_area(self) -> bool:
        """Check if an area has been selected."""
        return self.selected_area is not None
    
    def start_capturing(self):
        """Start capturing screenshots at interval."""
        if not self.selected_area:
            self.logger.error("No area selected for capturing")
            return False
        
        if self.is_recording:
            self.logger.warning("Already capturing")
            return False
        
        self.is_recording = True
        self.stop_capturing.clear()
        
        # Start capture thread
        self.capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )
        self.capture_thread.start()
        
        self.logger.info("Started capturing screenshots")
        return True
    
    def stop_capturing_screenshots(self):
        """Stop capturing screenshots."""
        if not self.is_recording:
            return
        
        self.is_recording = False
        self.stop_capturing.set()
        
        if self.capture_thread:
            self.capture_thread.join(timeout=1)
        
        self.logger.info("Stopped capturing screenshots")
    
    def _capture_loop(self):
        """Main capture loop running in background thread."""
        while self.is_recording and not self.stop_capturing.is_set():
            try:
                # Capture screenshot of selected area
                screenshot = self.capture_area()
                
                # Check if screenshot is valid (not None and has content)
                if screenshot is not None and len(screenshot.shape) == 3:
                    # Save screenshot
                    self._save_screenshot(screenshot)
                    
                    # Call callback with screenshot
                    if self.on_screenshot_captured:
                        self.on_screenshot_captured(screenshot)
                
                # Wait for next interval
                time.sleep(self.capture_interval)
            
            except Exception as e:
                self.logger.error(f"Error in capture loop: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
                time.sleep(1)  # Wait before retrying
    
    def capture_area(self) -> Optional[np.ndarray]:
        """
        Capture screenshot of the selected area.
        
        Returns:
            Screenshot as numpy array or None
        """
        if not self.selected_area:
            return None
        
        try:
            # Use MSS if available (faster)
            if MSS_AVAILABLE and mss:
                return self._capture_with_mss()
            
            # Fallback to PIL
            if PIL_AVAILABLE and ImageGrab:
                return self._capture_with_pil()
            
            self.logger.error("No screenshot library available")
            return None
        
        except Exception as e:
            self.logger.error(f"Error capturing screenshot: {str(e)}")
            return None
    
    def _capture_with_mss(self) -> Optional[np.ndarray]:
        """Capture screenshot using MSS library (faster)."""
        try:
            with mss.mss() as sct:
                monitor = {
                    "top": self.selected_area['y'],
                    "left": self.selected_area['x'],
                    "width": self.selected_area['width'],
                    "height": self.selected_area['height']
                }
                
                self.logger.info(f"Capturing with MSS: {monitor}")
                
                screenshot = sct.grab(monitor)
                
                self.logger.info(f"Captured screenshot size: {screenshot.size} (expecting {self.selected_area['width']}x{self.selected_area['height']})")
                
                # Convert to numpy array using PIL
                if PIL_AVAILABLE:
                    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                    img_array = np.array(img)
                    return img_array
                else:
                    # Fallback without PIL
                    return np.array(screenshot)
        
        except Exception as e:
            self.logger.error(f"Error with MSS capture: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def _capture_with_pil(self) -> Optional[np.ndarray]:
        """Capture screenshot using PIL library."""
        try:
            # Calculate screen coordinates
            x = self.selected_area['x']
            y = self.selected_area['y']
            width = self.selected_area['width']
            height = self.selected_area['height']
            
            # Log for debugging
            self.logger.info(f"Capturing with PIL: x={x}, y={y}, width={width}, height={height}")
            
            # Capture screen - bbox format: (left, top, right, bottom)
            bbox = (x, y, x + width, y + height)
            self.logger.info(f"PIL ImageGrab bbox: {bbox}")
            
            screenshot = ImageGrab.grab(bbox=bbox)
            
            # Log captured size
            self.logger.info(f"Captured screenshot size: {screenshot.size} (expecting {width}x{height})")
            
            # Verify size matches selected area
            if screenshot.size[0] != width or screenshot.size[1] != height:
                self.logger.warning(f"Screenshot size mismatch! Got {screenshot.size}, expected ({width}, {height})")
            
            # Convert to numpy array
            img = np.array(screenshot)
            
            # Ensure 3D array (height, width, channels)
            if len(img.shape) == 2:
                # Grayscale to RGB
                img = np.stack([img, img, img], axis=-1)
            
            return img
        
        except Exception as e:
            self.logger.error(f"Error with PIL capture: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def _save_screenshot(self, screenshot: np.ndarray):
        """
        Save screenshot to file (overwrites previous).
        
        Args:
            screenshot: Screenshot as numpy array
        """
        try:
            if PIL_AVAILABLE:
                # Convert numpy array to PIL Image
                img = Image.fromarray(screenshot)
                
                # Save to file (overwrites previous)
                img.save(self.screenshot_path, "PNG")
        
        except Exception as e:
            self.logger.error(f"Error saving screenshot: {str(e)}")
    
    def get_last_screenshot_path(self) -> Path:
        """
        Get path to the last screenshot.
        
        Returns:
            Path to screenshot file
        """
        return self.screenshot_path
    
    def get_last_screenshot_exists(self) -> bool:
        """Check if screenshot file exists."""
        return self.screenshot_path.exists()
    
    def set_capture_interval(self, interval: float):
        """
        Set capture interval in seconds.
        
        Args:
            interval: Interval in seconds
        """
        self.capture_interval = max(0.5, interval)  # Minimum 0.5 seconds
        self.logger.info(f"Capture interval set to {self.capture_interval}s")
    
    def set_callbacks(self,
                     on_screenshot: Optional[Callable] = None,
                     on_area_selected: Optional[Callable] = None):
        """
        Set callback functions.
        
        Args:
            on_screenshot: Called when screenshot is captured
            on_area_selected: Called when area is selected
        """
        self.on_screenshot_captured = on_screenshot
        self.on_area_selected = on_area_selected
    
    def cleanup(self):
        """Cleanup resources."""
        self.stop_capturing_screenshots()

