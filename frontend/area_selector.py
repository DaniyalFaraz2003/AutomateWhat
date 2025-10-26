"""
Area Selection Overlay Window for AutomateWhat.
Provides visual area selection with drag & drop functionality.
"""

import tkinter as tk
from typing import Optional, Callable


class AreaSelector:
    """Overlay window for selecting screen area."""
    
    def __init__(self, parent_window):
        """
        Initialize the area selector.
        
        Args:
            parent_window: Parent window to minimize
        """
        self.parent_window = parent_window
        
        self.overlay = None
        self.canvas = None
        self.start_x = 0
        self.start_y = 0
        self.current_rect = None
        self.selected_area = None
        self.is_selecting = False
        
        # Overlay position offsets for coordinate conversion
        self.overlay_offset_x = 0
        self.overlay_offset_y = 0
        
        # Callback for area selection
        self.on_area_selected: Optional[Callable] = None
    
    def show_selector(self):
        """Show the area selection overlay."""
        # Clean up any existing overlay first
        if self.overlay:
            try:
                self.overlay.destroy()
            except:
                pass
            self.overlay = None
            self.canvas = None
        
        # Reset selection state
        self.is_selecting = False
        self.current_rect = None
        
        # Hide parent window
        self.parent_window.withdraw()
        
        # Wait for window to be hidden
        self.parent_window.update()
        
        # Small delay to ensure parent is fully hidden
        import time
        time.sleep(0.1)
        
        # Get screen dimensions - force update
        screen_width = self.parent_window.winfo_screenwidth()
        screen_height = self.parent_window.winfo_screenheight()
        
        # Create overlay window at (0, 0) to cover entire screen
        self.overlay = tk.Toplevel()
        self.overlay.title("Select Area - Drag to Select")
        
        # Set geometry FIRST before attributes to ensure proper fullscreen positioning
        # Use negative coordinates to account for potential window manager offsets
        self.overlay.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # Update to apply geometry
        self.overlay.update_idletasks()
        
        # Now set attributes after geometry is applied
        self.overlay.overrideredirect(True)  # Remove window decorations
        self.overlay.attributes('-alpha', 0.3)
        self.overlay.configure(bg='black')
        self.overlay.attributes('-topmost', True)
        
        # Update after setting attributes
        self.overlay.update_idletasks()
        
        # Force position to exactly (0, 0) multiple times to ensure it sticks
        for _ in range(3):
            self.overlay.geometry(f"+0+0")
            self.overlay.update_idletasks()
        
        # On Windows, try to force fullscreen
        try:
            self.overlay.wm_attributes('-fullscreen', True)
        except:
            pass
        
        # Final geometry update
        self.overlay.geometry(f"{screen_width}x{screen_height}+0+0")
        self.overlay.update_idletasks()
        
        self.overlay.focus_force()
        
        # Store the actual overlay position for coordinate conversion
        self.overlay.update_idletasks()
        self.overlay_offset_x = self.overlay.winfo_x()
        self.overlay_offset_y = self.overlay.winfo_y()
        
        # Create canvas for drawing - use same size as overlay
        self.canvas = tk.Canvas(
            self.overlay,
            highlightthickness=0,
            bg='black',
            width=screen_width,
            height=screen_height,
            scrollregion=(0, 0, screen_width, screen_height)
        )
        self.canvas.pack(fill='both', expand=True)
        
        # Bind events to canvas
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Escape>", self._on_cancel)
        
        # Also bind Escape to overlay
        self.overlay.bind("<Escape>", self._on_cancel)
        
        # Focus on overlay
        self.overlay.focus_set()
        
        # Add instructions
        self._add_instructions()
    
    def _add_instructions(self):
        """Add instructions to the overlay."""
        # Add instructions to canvas
        self.canvas.create_text(
            self.overlay.winfo_screenwidth() // 2,
            50,
            text="Drag to select area • Press ESC to cancel",
            font=('Segoe UI', 20),
            fill='white',
            tags='instruction'
        )
    
    def _on_mouse_down(self, event):
        """Handle mouse down event."""
        self.start_x = event.x
        self.start_y = event.y
        self.is_selecting = True
        
        # Clear previous selection
        if self.current_rect:
            self.canvas.delete(self.current_rect)
    
    def _on_mouse_drag(self, event):
        """Handle mouse drag event."""
        if not self.is_selecting:
            return
        
        # Clear previous rectangle
        if self.current_rect:
            self.canvas.delete(self.current_rect)
        
        # Get current coordinates
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)
        
        # Draw selection rectangle with bright colors for visibility
        self.current_rect = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill='lightgreen',
            outline='red',
            width=3,
            stipple='gray50',  # Makes it semi-transparent
            tags='selection'
        )
    
    def _on_mouse_up(self, event):
        """Handle mouse up event."""
        if not self.is_selecting:
            return
        
        self.is_selecting = False
        
        # Get final coordinates (in canvas space)
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)
        
        # Calculate selected area dimensions
        width = x2 - x1
        height = y2 - y1
        
        # Validate minimum size
        if width < 50 or height < 50:
            self._show_error_message("Selection too small. Minimum size: 50x50 pixels.")
            return
        
        # Convert canvas coordinates to screen coordinates
        # Use the stored overlay offset to account for any window manager positioning
        screen_x = x1 + self.overlay_offset_x
        screen_y = y1 + self.overlay_offset_y
        screen_width = width
        screen_height = height
        
        # Store selected area in screen coordinates
        self.selected_area = {
            'x': int(screen_x),
            'y': int(screen_y),
            'width': int(screen_width),
            'height': int(screen_height)
        }
        
        # Call callback
        if self.on_area_selected:
            self.on_area_selected(self.selected_area)
        
        # Close overlay
        self._close_overlay()
    
    def _on_cancel(self, event):
        """Handle cancel event (ESC key)."""
        self._close_overlay()
    
    def _show_error_message(self, message):
        """Show error message to user."""
        # Get screen dimensions
        screen_width = self.overlay.winfo_screenwidth()
        screen_height = self.overlay.winfo_screenheight()
        
        # Create error text on canvas
        error_id = self.canvas.create_text(
            screen_width // 2,
            screen_height - 100,
            text=message,
            font=('Segoe UI', 14),
            fill='yellow',
            tags='error'
        )
        
        # Auto-dismiss after 2 seconds
        self.overlay.after(2000, lambda: self.canvas.delete(error_id))
    
    def _close_overlay(self):
        """Close the overlay and restore parent window."""
        if self.overlay:
            self.overlay.destroy()
            self.overlay = None
        
        # Restore parent window
        self.parent_window.deiconify()
    
    def set_callback(self, callback: Callable):
        """
        Set callback for area selection.
        
        Args:
            callback: Function to call when area is selected
        """
        self.on_area_selected = callback

