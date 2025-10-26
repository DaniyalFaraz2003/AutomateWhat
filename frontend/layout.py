"""
Main application layout for AutomateWhat GUI.
This module contains the complete layout structure with all panels.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from pathlib import Path
import os
import threading

from config.theme import WhatsAppTheme
from backend.model_manager import ModelManager
from backend.screen_capture import ScreenCaptureManager
from frontend.area_selector import AreaSelector


class MainLayout:
    """Main application layout manager."""
    
    def __init__(self, root, config):
        """
        Initialize the main layout.
        
        Args:
            root: Tkinter root window
            config: Application configuration
        """
        self.root = root
        self.config = config
        self.logger = logging.getLogger("AutomateWhat.Layout")
        self.theme = WhatsAppTheme()
        
        # Layout state
        self.is_recording = False
        self.selected_model = None
        self.recording_area = None
        
        # Initialize managers
        self.model_manager = ModelManager(config)
        self._setup_model_callbacks()
        
        self.screen_capture = ScreenCaptureManager(config)
        self._setup_screen_capture_callbacks()
        
        # Initialize area selector
        self.area_selector = AreaSelector(root)
        self.area_selector.set_callback(self._on_area_selected)
        
        self._create_main_structure()
        self._apply_whatsapp_theme()
        
        # Populate model dropdown (lazy loading - no scanning on startup)
        self._populate_model_dropdown()
        
        self.logger.info("Main layout initialized with WhatsApp theme")
    
    def _create_main_structure(self):
        """Create the main application structure."""
        # Main container with padding
        self.main_container = tk.Frame(self.root, bg=self.theme.DARK_BG_PRIMARY)
        self.main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create all panels
        self._create_header()
        self._create_content_area()
        self._create_footer()
    
    def _create_header(self):
        """Create the header section."""
        self.header_frame = tk.Frame(
            self.main_container, 
            bg=self.theme.DARK_BG_SECONDARY,
            height=70,
            relief='solid',
            bd=1
        )
        self.header_frame.pack(fill='x', pady=(0, 10))
        self.header_frame.pack_propagate(False)
        
        # Title
        self.title_label = tk.Label(
            self.header_frame,
            text="🤖 AutomateWhat - WhatsApp AI Assistant",
            font=('Segoe UI', 18, 'bold'),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_PRIMARY
        )
        self.title_label.pack(side='left', padx=25, pady=20)
        
        # Status indicator
        self.status_indicator = tk.Label(
            self.header_frame,
            text="● Ready",
            font=('Segoe UI', 12, 'bold'),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.SUCCESS
        )
        self.status_indicator.pack(side='right', padx=25, pady=20)
    
    def _create_content_area(self):
        """Create the main content area with three panels."""
        self.content_frame = tk.Frame(
            self.main_container,
            bg=self.theme.DARK_BG_PRIMARY
        )
        self.content_frame.pack(fill='both', expand=True)
        
        # Left Panel - Model Selection & Controls
        self._create_left_panel()
        
        # Center Panel - Live Preview & Recording Area
        self._create_center_panel()
        
        # Right Panel - AI Response & Conversation
        self._create_right_panel()
    
    def _create_left_panel(self):
        """Create the left control panel."""
        self.left_panel = tk.Frame(
            self.content_frame,
            bg=self.theme.DARK_BG_SECONDARY,
            width=350,
            relief='solid',
            bd=1
        )
        self.left_panel.pack(side='left', fill='y', padx=(0, 10))
        self.left_panel.pack_propagate(False)
        
        # Panel title
        self.left_title = tk.Label(
            self.left_panel,
            text="Control Panel",
            font=('Segoe UI', 14, 'bold'),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_PRIMARY
        )
        self.left_title.pack(pady=15)
        
        # Model Selection Section
        self._create_model_section()
        
        # Recording Controls Section
        self._create_recording_section()
        
        # Settings Section
        self._create_settings_section()
    
    def _create_model_section(self):
        """Create the model selection section."""
        # Model section frame
        model_frame = tk.LabelFrame(
            self.left_panel,
            text="🤖 AI Model",
            font=('Segoe UI', 11, 'bold'),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_PRIMARY,
            relief='solid',
            bd=1,
            padx=15,
            pady=15
        )
        model_frame.pack(fill='x', padx=15, pady=10)
        
        # Model selection dropdown
        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            state='readonly',
            width=28,
            font=('Segoe UI', 10)
        )
        self.model_dropdown.pack(pady=(0, 10))
        
        # Load model button
        self.load_model_btn = tk.Button(
            model_frame,
            text="📥 Load Model",
            command=self._load_model,
            bg=self.theme.WHATSAPP_GREEN,
            fg=self.theme.TEXT_PRIMARY,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            padx=25,
            pady=8,
            cursor='hand2',
            activebackground=self.theme.WHATSAPP_DARK_GREEN,
            activeforeground=self.theme.TEXT_PRIMARY
        )
        self.load_model_btn.pack(pady=(0, 10))
        
        # Model status
        self.model_status = tk.Label(
            model_frame,
            text="No model loaded",
            font=('Segoe UI', 9),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_SECONDARY
        )
        self.model_status.pack(pady=(0, 8))
        
        # Progress bar for model loading
        self.model_progress = ttk.Progressbar(
            model_frame,
            mode='indeterminate',
            length=250
        )
        self.model_progress.pack(pady=(0, 5))
        self.model_progress.pack_forget()  # Hide initially
    
    def _create_recording_section(self):
        """Create the recording controls section."""
        # Recording section frame
        recording_frame = tk.LabelFrame(
            self.left_panel,
            text="📹 Screen Recording",
            font=('Segoe UI', 11, 'bold'),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_PRIMARY,
            relief='solid',
            bd=1,
            padx=15,
            pady=15
        )
        recording_frame.pack(fill='x', padx=15, pady=10)
        
        # Select area button
        self.select_area_btn = tk.Button(
            recording_frame,
            text="🎯 Select Recording Area",
            command=self._select_recording_area,
            bg=self.theme.ACCENT_BLUE,
            fg=self.theme.TEXT_PRIMARY,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            padx=20,
            pady=8,
            cursor='hand2',
            activebackground='#3A9BC1',
            activeforeground=self.theme.TEXT_PRIMARY
        )
        self.select_area_btn.pack(pady=(0, 10))
        
        # Start/Stop recording button
        self.record_btn = tk.Button(
            recording_frame,
            text="▶️ Start Recording",
            command=self._toggle_recording,
            bg=self.theme.WHATSAPP_GREEN,
            fg=self.theme.TEXT_PRIMARY,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            padx=25,
            pady=8,
            cursor='hand2',
            state='disabled',
            activebackground=self.theme.WHATSAPP_DARK_GREEN,
            activeforeground=self.theme.TEXT_PRIMARY
        )
        self.record_btn.pack(pady=(0, 10))
        
        # Recording status
        self.recording_status = tk.Label(
            recording_frame,
            text="No area selected",
            font=('Segoe UI', 9),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_SECONDARY
        )
        self.recording_status.pack(pady=(0, 5))
    
    def _create_settings_section(self):
        """Create the settings section."""
        # Settings section frame
        settings_frame = tk.LabelFrame(
            self.left_panel,
            text="⚙️ Settings",
            font=('Segoe UI', 11, 'bold'),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_PRIMARY,
            relief='solid',
            bd=1,
            padx=15,
            pady=15
        )
        settings_frame.pack(fill='x', padx=15, pady=10)
        
        # Screenshot interval
        interval_label = tk.Label(
            settings_frame,
            text="Screenshot Interval (seconds):",
            font=('Segoe UI', 10),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_PRIMARY
        )
        interval_label.pack(anchor='w', pady=(0, 5))
        
        self.interval_var = tk.StringVar(value="2")
        self.interval_entry = tk.Entry(
            settings_frame,
            textvariable=self.interval_var,
            width=12,
            font=('Segoe UI', 10),
            bg=self.theme.DARK_BG_TERTIARY,
            fg=self.theme.TEXT_PRIMARY,
            relief='flat',
            bd=5
        )
        self.interval_entry.pack(anchor='w', pady=(0, 15))
        
        # Auto-response toggle
        self.auto_response_var = tk.BooleanVar()
        self.auto_response_check = tk.Checkbutton(
            settings_frame,
            text="Auto-generate responses",
            variable=self.auto_response_var,
            font=('Segoe UI', 10),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_PRIMARY,
            selectcolor=self.theme.DARK_BG_TERTIARY,
            activebackground=self.theme.DARK_BG_SECONDARY,
            activeforeground=self.theme.TEXT_PRIMARY
        )
        self.auto_response_check.pack(anchor='w', pady=(0, 5))
    
    def _create_center_panel(self):
        """Create the center preview panel."""
        self.center_panel = tk.Frame(
            self.content_frame,
            bg=self.theme.DARK_BG_TERTIARY,
            relief='solid',
            bd=1
        )
        self.center_panel.pack(side='left', fill='both', expand=True, padx=10)
        
        # Panel title
        self.center_title = tk.Label(
            self.center_panel,
            text="Live Preview",
            font=('Segoe UI', 14, 'bold'),
            bg=self.theme.DARK_BG_TERTIARY,
            fg=self.theme.TEXT_PRIMARY
        )
        self.center_title.pack(pady=20)
        
        # Preview area
        self.preview_frame = tk.Frame(
            self.center_panel,
            bg=self.theme.DARK_BG_PRIMARY,
            relief='sunken',
            bd=3
        )
        self.preview_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Preview label
        self.preview_label = tk.Label(
            self.preview_frame,
            text="🎯 Select a recording area to start live preview",
            font=('Segoe UI', 12),
            bg=self.theme.DARK_BG_PRIMARY,
            fg=self.theme.TEXT_SECONDARY
        )
        self.preview_label.pack(expand=True)
        
        # Preview info
        self.preview_info = tk.Label(
            self.center_panel,
            text="No recording area selected",
            font=('Segoe UI', 10),
            bg=self.theme.DARK_BG_TERTIARY,
            fg=self.theme.TEXT_SECONDARY
        )
        self.preview_info.pack(pady=(0, 15))
    
    def _create_right_panel(self):
        """Create the right response panel."""
        self.right_panel = tk.Frame(
            self.content_frame,
            bg=self.theme.DARK_BG_SECONDARY,
            width=400,
            relief='solid',
            bd=1
        )
        self.right_panel.pack(side='right', fill='y', padx=(10, 0))
        self.right_panel.pack_propagate(False)
        
        # Panel title
        self.right_title = tk.Label(
            self.right_panel,
            text="AI Response",
            font=('Segoe UI', 14, 'bold'),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_PRIMARY
        )
        self.right_title.pack(pady=15)
        
        # AI Response Section
        self._create_response_section()
        
        # Conversation History Section
        self._create_conversation_section()
    
    def _create_response_section(self):
        """Create the AI response section."""
        # Response section frame
        response_frame = tk.LabelFrame(
            self.right_panel,
            text="🤖 AI Generated Response",
            font=('Segoe UI', 11, 'bold'),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_PRIMARY,
            relief='solid',
            bd=1,
            padx=15,
            pady=15
        )
        response_frame.pack(fill='x', padx=15, pady=10)
        
        # Response text area
        self.response_text = tk.Text(
            response_frame,
            height=6,
            width=40,
            font=('Segoe UI', 11),
            bg=self.theme.DARK_BG_PRIMARY,
            fg=self.theme.TEXT_PRIMARY,
            relief='flat',
            bd=8,
            wrap='word'
        )
        self.response_text.pack(pady=(0, 15), padx=5)
        
        # Response actions
        actions_frame = tk.Frame(
            response_frame,
            bg=self.theme.DARK_BG_SECONDARY
        )
        actions_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        # Copy button
        self.copy_btn = tk.Button(
            actions_frame,
            text="📋 Copy",
            command=self._copy_response,
            bg=self.theme.ACCENT_BLUE,
            fg=self.theme.TEXT_PRIMARY,
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            padx=15,
            pady=6,
            cursor='hand2',
            activebackground='#3A9BC1',
            activeforeground=self.theme.TEXT_PRIMARY
        )
        self.copy_btn.pack(side='left', padx=(0, 8))
        
        # Regenerate button
        self.regenerate_btn = tk.Button(
            actions_frame,
            text="🔄 Regenerate",
            command=self._regenerate_response,
            bg=self.theme.ACCENT_PURPLE,
            fg=self.theme.TEXT_PRIMARY,
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            padx=15,
            pady=6,
            cursor='hand2',
            activebackground='#9C27B0',
            activeforeground=self.theme.TEXT_PRIMARY
        )
        self.regenerate_btn.pack(side='left', padx=(0, 8))
        
        # Send button
        self.send_btn = tk.Button(
            actions_frame,
            text="📤 Send",
            command=self._send_response,
            bg=self.theme.WHATSAPP_GREEN,
            fg=self.theme.TEXT_PRIMARY,
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            padx=15,
            pady=6,
            cursor='hand2',
            activebackground=self.theme.WHATSAPP_DARK_GREEN,
            activeforeground=self.theme.TEXT_PRIMARY
        )
        self.send_btn.pack(side='left', padx=(0, 8))
    
    def _create_conversation_section(self):
        """Create the conversation history section."""
        # Conversation section frame
        conversation_frame = tk.LabelFrame(
            self.right_panel,
            text="💭 Conversation History",
            font=('Segoe UI', 11, 'bold'),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_PRIMARY,
            relief='solid',
            bd=1,
            padx=15,
            pady=15
        )
        conversation_frame.pack(fill='both', expand=True, padx=15, pady=10)
        
        # Conversation text area with scrollbar
        text_frame = tk.Frame(
            conversation_frame,
            bg=self.theme.DARK_BG_SECONDARY
        )
        text_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.conversation_text = tk.Text(
            text_frame,
            font=('Segoe UI', 10),
            bg=self.theme.DARK_BG_PRIMARY,
            fg=self.theme.TEXT_PRIMARY,
            relief='flat',
            bd=8,
            wrap='word',
            state='disabled'
        )
        
        # Scrollbar
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.conversation_text.pack(side='left', fill='both', expand=True)
        self.conversation_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.conversation_text.yview)
    
    def _create_footer(self):
        """Create the footer section."""
        self.footer_frame = tk.Frame(
            self.main_container,
            bg=self.theme.DARK_BG_SECONDARY,
            height=50,
            relief='solid',
            bd=1
        )
        self.footer_frame.pack(fill='x', pady=(10, 0))
        self.footer_frame.pack_propagate(False)
        
        # Status text
        self.status_text = tk.Label(
            self.footer_frame,
            text="Ready to start",
            font=('Segoe UI', 10),
            bg=self.theme.DARK_BG_SECONDARY,
            fg=self.theme.TEXT_SECONDARY
        )
        self.status_text.pack(side='left', padx=25, pady=15)
        
        # Progress bar
        self.main_progress = ttk.Progressbar(
            self.footer_frame,
            mode='determinate',
            length=250
        )
        self.main_progress.pack(side='right', padx=25, pady=15)
        self.main_progress.pack_forget()  # Hide initially
    
    def _apply_whatsapp_theme(self):
        """Apply WhatsApp theme to all components."""
        colors = self.theme.get_theme_colors()
        
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles
        style.configure('TFrame', background=colors['bg_primary'])
        style.configure('TLabel', background=colors['bg_primary'], foreground=colors['text_primary'])
        style.configure('TButton', background=colors['whatsapp_green'], foreground=colors['text_primary'])
        style.configure('TEntry', fieldbackground=colors['bg_tertiary'], foreground=colors['text_primary'])
        style.configure('TCombobox', fieldbackground=colors['bg_tertiary'], foreground=colors['text_primary'])
        style.configure('TCheckbutton', background=colors['bg_secondary'], foreground=colors['text_primary'])
        style.configure('TProgressbar', background=colors['whatsapp_green'], troughcolor=colors['bg_tertiary'])
        
        # Configure combobox dropdown
        style.configure('TCombobox', 
                       fieldbackground=colors['bg_tertiary'],
                       background=colors['bg_tertiary'],
                       foreground=colors['text_primary'],
                       borderwidth=1,
                       relief='solid')
        
        # Configure entry styling
        style.configure('TEntry',
                       fieldbackground=colors['bg_tertiary'],
                       background=colors['bg_tertiary'],
                       foreground=colors['text_primary'],
                       borderwidth=1,
                       relief='solid')
    
    # Model management methods
    def _load_model(self):
        """Load selected AI model."""
        selected_model = self.model_var.get()
        if not selected_model:
            messagebox.showwarning("No Model Selected", "Please select a model from the dropdown.")
            return
        
        self.logger.info(f"Loading model: {selected_model}")
        
        # Check if model is already loaded
        if self.model_manager.is_model_loaded():
            current_model = self.model_manager.get_current_model_info()
            if current_model and current_model.name == selected_model:
                messagebox.showinfo("Model Already Loaded", f"Model {selected_model} is already loaded.")
                return
        
        # Start loading
        success = self.model_manager.load_model(selected_model, device="cuda")
        if not success:
            messagebox.showerror("Loading Failed", f"Failed to start loading model {selected_model}")
    
    def get_loaded_model(self):
        """Get the currently loaded model."""
        return self.model_manager.get_loaded_model()
    
    def get_model_status(self):
        """Get current model status."""
        return self.model_manager.get_model_status()
    
    def _setup_model_callbacks(self):
        """Setup callbacks for model manager events."""
        self.model_manager.set_callbacks(
            on_loading=self._on_model_loading,
            on_loaded=self._on_model_loaded,
            on_error=self._on_model_error,
            on_progress=self._on_model_progress
        )
    
    def _populate_model_dropdown(self):
        """Populate model dropdown with predefined models (lazy loading)."""
        try:
            model_names = self.model_manager.get_model_names()
            
            # Update dropdown
            self.model_dropdown['values'] = model_names
            
            if model_names:
                self.model_dropdown.set(model_names[0])  # Select first model
                self.logger.info(f"Populated dropdown with {len(model_names)} models: {model_names}")
            else:
                self.logger.warning("No models available")
                self.model_status.config(text="No models available")
                
        except Exception as e:
            self.logger.error(f"Error populating model dropdown: {str(e)}")
            self.model_status.config(text="Error loading models")
    
    def _on_model_loading(self, model_name):
        """Called when model starts loading."""
        def update_ui():
            self.model_status.config(text=f"Loading {model_name}...")
            self.model_progress.pack(pady=(0, 5))
            self.model_progress.start()
            self.load_model_btn.config(state='disabled', text="Loading...")
        
        # Update UI in main thread
        self.root.after(0, update_ui)
        self.logger.info(f"Model {model_name} started loading")
    
    def _on_model_loaded(self, model_name):
        """Called when model is loaded successfully."""
        def update_ui():
            self.model_status.config(text=f"✓ {model_name} loaded successfully")
            self.model_progress.stop()
            self.model_progress.pack_forget()
            self.load_model_btn.config(state='normal', text="📥 Load Model")
            
            # Update status indicator
            if hasattr(self, 'status_indicator'):
                self.status_indicator.config(text="● Model Ready", fg=self.theme.SUCCESS)
        
        # Update UI in main thread
        self.root.after(0, update_ui)
        self.logger.info(f"Model {model_name} loaded successfully")
    
    def _on_model_error(self, error_message):
        """Called when model loading fails."""
        def update_ui():
            self.model_status.config(text=f"✗ Error: {error_message}")
            self.model_progress.stop()
            self.model_progress.pack_forget()
            self.load_model_btn.config(state='normal', text="📥 Load Model")
            
            # Update status indicator
            if hasattr(self, 'status_indicator'):
                self.status_indicator.config(text="● Error", fg=self.theme.ERROR)
            
            # Show error message
            messagebox.showerror("Model Loading Error", error_message)
        
        # Update UI in main thread
        self.root.after(0, update_ui)
        self.logger.error(f"Model loading error: {error_message}")
    
    def _on_model_progress(self, progress):
        """Called for progress updates."""
        def update_ui():
            # Update progress bar if needed
            if hasattr(self, 'model_progress') and self.model_progress.winfo_viewable():
                # Update progress text
                if isinstance(progress, str):
                    self.model_status.config(text=progress)
        
        # Update UI in main thread
        self.root.after(0, update_ui)
        
    def _setup_screen_capture_callbacks(self):
        """Setup callbacks for screen capture manager."""
        self.screen_capture.set_callbacks(
            on_screenshot=self._on_screenshot_captured,
            on_area_selected=self._on_screen_area_selected
        )
    
    def _on_screenshot_captured(self, screenshot):
        """Called when a screenshot is captured."""
        def update_ui():
            # Update live preview with new screenshot
            self._update_live_preview()
        
        # Update UI in main thread
        self.root.after(0, update_ui)
        self.logger.info("Screenshot captured")
    
    def _on_screen_area_selected(self, area):
        """Called when screen area is selected."""
        def update_ui():
            # Update recording status
            self.recording_status.config(text=f"Area selected: {area['width']}x{area['height']}")
            self.record_btn.config(state='normal')
        
        # Update UI in main thread
        self.root.after(0, update_ui)
        self.logger.info(f"Screen area selected: {area}")
    
    def _on_area_selected(self, area):
        """Called when area selector completes selection."""
        # Set the selected area in screen capture manager
        self.screen_capture.set_selected_area(
            area['x'], area['y'], area['width'], area['height']
        )
        
        self.logger.info(f"Area selection completed: {area}")
        
        # Immediately capture and display the screenshot
        self._capture_initial_preview()
    
    def _capture_initial_preview(self):
        """Capture and display initial preview of selected area."""
        try:
            # Capture screenshot
            screenshot = self.screen_capture.capture_area()
            
            if screenshot is not None and len(screenshot.shape) == 3:
                # Save screenshot
                self.screen_capture._save_screenshot(screenshot)
                
                # Update preview
                self.root.after(50, self._update_live_preview)
                
                self.logger.info("Initial preview captured")
        
        except Exception as e:
            self.logger.error(f"Error capturing initial preview: {str(e)}")
    
    def _update_live_preview(self):
        """Update the live preview panel with captured screenshot."""
        try:
            if not self.screen_capture.get_last_screenshot_exists():
                return
            
            screenshot_path = self.screen_capture.get_last_screenshot_path()
            
            # Load screenshot using PIL
            from PIL import Image, ImageTk
            
            img = Image.open(screenshot_path)
            
            # Get the actual screenshot size (should match selected area exactly)
            actual_width, actual_height = img.size
            
            # Get preview frame size
            self.preview_frame.update_idletasks()
            preview_frame_width = self.preview_frame.winfo_width()
            preview_frame_height = self.preview_frame.winfo_height()
            
            # Calculate maximum size to fit in preview area (leave padding)
            max_width = max(preview_frame_width - 40, 100)  # Minimum 100px
            max_height = max(preview_frame_height - 40, 100)  # Minimum 100px
            
            # Calculate scaling to fit preview area while maintaining aspect ratio
            scale_w = max_width / actual_width
            scale_h = max_height / actual_height
            scale = min(scale_w, scale_h)  # Fit to preview area, maintaining aspect ratio
            
            # Resize image to fit in preview
            display_width = int(actual_width * scale)
            display_height = int(actual_height * scale)
            
            # Resize image
            img_resized = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img_resized)
            
            # Clear any previous image
            if hasattr(self.preview_label, 'image'):
                del self.preview_label.image
            
            # Update preview label with the image
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo  # Keep a reference
            
            # Update preview info
            area = self.screen_capture.get_selected_area()
            if area:
                self.preview_info.config(
                    text=f"Capturing: {actual_width}x{actual_height} @ {self.screen_capture.capture_interval}s intervals"
                )
            
            self.logger.info(f"Preview updated: screenshot={actual_width}x{actual_height}, display={display_width}x{display_height}, scale={scale:.2f}")
        
        except Exception as e:
            self.logger.error(f"Error updating live preview: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _select_recording_area(self):
        """Select screen recording area."""
        self.logger.info("Starting area selection")
        
        # Show area selector overlay
        self.area_selector.show_selector()
    
    def _toggle_recording(self):
        """Toggle recording state."""
        if self.is_recording:
            # Stop recording
            self.screen_capture.stop_capturing_screenshots()
            self.is_recording = False
            self.record_btn.config(
                text="▶️ Start Recording",
                bg=self.theme.WHATSAPP_GREEN
            )
            self.recording_status.config(text="Recording stopped")
            self.logger.info("Recording stopped")
        else:
            # Update capture interval from settings
            try:
                interval = float(self.interval_var.get())
                self.screen_capture.set_capture_interval(interval)
            except ValueError:
                self.logger.warning("Invalid interval value, using default")
            
            # Start recording
            if self.screen_capture.start_capturing():
                self.is_recording = True
                self.record_btn.config(
                    text="⏹️ Stop Recording",
                    bg=self.theme.ACCENT_RED
                )
                self.recording_status.config(text="Recording...")
                self.logger.info("Recording started")
            else:
                messagebox.showerror("Recording Error", "Could not start recording. Please select an area first.")
        
    def _copy_response(self):
        """Copy AI response to clipboard."""
        self.logger.info("Copy response requested")
        # TODO: Implement copy functionality
        
    def _regenerate_response(self):
        """Regenerate AI response."""
        self.logger.info("Regenerate response requested")
        # TODO: Implement regeneration
        
    def _send_response(self):
        """Send response to WhatsApp."""
        self.logger.info("Send response requested")
        # TODO: Implement send functionality
