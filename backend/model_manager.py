"""
Model Manager for AutomateWhat application.
Handles model detection, loading, and management with proper HuggingFace integration.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable
import threading
import time

# CRITICAL: Set HuggingFace cache directories BEFORE importing transformers
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = Path(SCRIPT_DIR).parent
MODELS_DIR = PROJECT_ROOT / "models"
HF_CACHE_DIR = MODELS_DIR / "hf_models"

# Set HuggingFace environment variables
os.environ['HF_HOME'] = str(HF_CACHE_DIR)
os.environ['HF_HUB_CACHE'] = str(HF_CACHE_DIR / 'hub')
os.environ['HUGGINGFACE_HUB_CACHE'] = str(HF_CACHE_DIR / 'hub')
os.environ['TRANSFORMERS_CACHE'] = str(HF_CACHE_DIR / 'transformers')
os.environ['HF_DATASETS_CACHE'] = str(HF_CACHE_DIR / 'datasets')


# Now import AI libraries
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Transformers not available: {e}")
    TRANSFORMERS_AVAILABLE = False
    AutoModelForCausalLM = None
    AutoTokenizer = None
    pipeline = None
    torch = None


class ModelInfo:
    """Information about an available model."""
    
    def __init__(self, name: str, model_id: str, model_type: str = "llm"):
        self.name = name  # Display name
        self.model_id = model_id  # HuggingFace model ID
        self.model_type = model_type
        self.is_loaded = False
        self.loading = False
        self.error = None
        self.local_path = None
        self.size_mb = 0.0
    
    def get_local_path(self) -> str:
        """Get local path for the model."""
        if self.local_path:
            return self.local_path
        
        # Create local path based on model ID
        model_name = self.model_id.replace("/", "--")
        return str(HF_CACHE_DIR / model_name)
    
    def is_downloaded(self) -> bool:
        """Check if model is downloaded locally."""
        local_path = self.get_local_path()
        config_file = Path(local_path) / "config.json"
        return config_file.exists()
    
    def __str__(self):
        status = "Loaded" if self.is_loaded else ("Downloaded" if self.is_downloaded() else "Available")
        return f"{self.name} ({self.model_id}) - {status}"


class ModelManager:
    """Manages AI models for the AutomateWhat application."""
    
    def __init__(self, config):
        """
        Initialize the model manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger("AutomateWhat.ModelManager")
        
        # Model storage
        self.available_models: List[ModelInfo] = []
        self.loaded_model = None
        self.current_model: Optional[ModelInfo] = None
        
        # Callbacks for UI updates
        self.on_model_loading: Optional[Callable] = None
        self.on_model_loaded: Optional[Callable] = None
        self.on_model_error: Optional[Callable] = None
        self.on_progress_update: Optional[Callable] = None
        
        # Threading
        self.loading_thread: Optional[threading.Thread] = None
        self._stop_loading = threading.Event()
        
        # Predefined models (like in whatsapp_ai_pipeline.py)
        self.predefined_models = [
            ModelInfo("Qwen2.5-3B-Instruct", "Qwen/Qwen2.5-3B-Instruct"),
            ModelInfo("TinyLlama-1.1B-Chat", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
        ]
        
        self.logger.info("Model Manager initialized")
    
    def get_available_models(self) -> List[ModelInfo]:
        """
        Get list of available models (lazy loading).
        
        Returns:
            List of ModelInfo objects
        """
        if not self.available_models:
            self.available_models = self.predefined_models.copy()
            self.logger.info(f"Initialized {len(self.available_models)} predefined models")
        
        return self.available_models
    
    def get_model_names(self) -> List[str]:
        """
        Get list of available model names.
        
        Returns:
            List of model names
        """
        models = self.get_available_models()
        return [model.name for model in models]
    
    def load_model(self, model_name: str, device: str = "cuda") -> bool:
        """
        Load a model asynchronously.
        
        Args:
            model_name: Name of the model to load
            device: Device to load on (cuda/cpu)
            
        Returns:
            True if loading started successfully
        """
        if not TRANSFORMERS_AVAILABLE:
            error_msg = "Transformers library not available. Please install transformers."
            self.logger.error(error_msg)
            if self.on_model_error:
                self.on_model_error(error_msg)
            return False
        
        # Find the model
        model_info = None
        for model in self.get_available_models():
            if model.name == model_name:
                model_info = model
                break
        
        if not model_info:
            self.logger.error(f"Model not found: {model_name}")
            if self.on_model_error:
                self.on_model_error(f"Model not found: {model_name}")
            return False
        
        if model_info.is_loaded:
            self.logger.info(f"Model {model_name} is already loaded")
            return True
        
        if model_info.loading:
            self.logger.info(f"Model {model_name} is already loading")
            return True
        
        # Start loading in a separate thread
        self.loading_thread = threading.Thread(
            target=self._load_model_thread,
            args=(model_info, device),
            daemon=True
        )
        self.loading_thread.start()
        
        return True
    
    def _load_model_thread(self, model_info: ModelInfo, device: str):
        """
        Load model in a separate thread.
        
        Args:
            model_info: Model information
            device: Device to load on
        """
        try:
            self.logger.info(f"Starting to load model: {model_info.name} ({model_info.model_id})")
            
            # Update model status
            model_info.loading = True
            model_info.error = None
            
            if self.on_model_loading:
                self.on_model_loading(model_info.name)
            
            # Check CUDA availability
            if device == "cuda" and torch and not torch.cuda.is_available():
                self.logger.warning("CUDA not available, falling back to CPU")
                device = "cpu"
            
            # Load model and tokenizer
            model_path = model_info.get_local_path()
            
            # Download model if not present
            if not model_info.is_downloaded():
                self.logger.info(f"Downloading model {model_info.model_id}...")
                if self.on_progress_update:
                    self.on_progress_update("Downloading model...")
                
                model = AutoModelForCausalLM.from_pretrained(
                    model_info.model_id,
                    trust_remote_code=True,
                    cache_dir=str(HF_CACHE_DIR),
                )
                tokenizer = AutoTokenizer.from_pretrained(
                    model_info.model_id,
                    cache_dir=str(HF_CACHE_DIR)
                )
                
                # Save locally
                model.save_pretrained(model_path)
                tokenizer.save_pretrained(model_path)
                
                self.logger.info(f"Model {model_info.model_id} downloaded and saved")
            
            # Load from local path
            self.logger.info(f"Loading model from: {model_path}")
            
            torch.random.manual_seed(0)
            
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                local_files_only=True,
                device_map=device,
                torch_dtype="auto",
                trust_remote_code=True,
            )
            
            tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                local_files_only=True
            )
            
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
            )
            
            if not self._stop_loading.is_set():
                # Model loaded successfully
                self.loaded_model = pipe
                self.current_model = model_info
                model_info.is_loaded = True
                model_info.loading = False
                
                self.logger.info(f"Model {model_info.name} loaded successfully")
                
                if self.on_model_loaded:
                    self.on_model_loaded(model_info.name)
            else:
                # Loading was cancelled
                model_info.loading = False
                self.logger.info(f"Model loading cancelled: {model_info.name}")
        
        except Exception as e:
            # Handle any errors
            model_info.loading = False
            model_info.error = str(e)
            
            self.logger.error(f"Error loading model {model_info.name}: {str(e)}")
            
            if self.on_model_error:
                self.on_model_error(f"Error loading model {model_info.name}: {str(e)}")
    
    def unload_model(self):
        """Unload the currently loaded model."""
        if self.loaded_model:
            self.logger.info(f"Unloading model: {self.current_model.name}")
            
            # Stop any ongoing loading
            self._stop_loading.set()
            
            # Clear loaded model
            self.loaded_model = None
            if self.current_model:
                self.current_model.is_loaded = False
                self.current_model = None
            
            self.logger.info("Model unloaded")
    
    def get_loaded_model(self):
        """
        Get the currently loaded model.
        
        Returns:
            Loaded pipeline or None
        """
        return self.loaded_model
    
    def get_current_model_info(self) -> Optional[ModelInfo]:
        """
        Get information about the currently loaded model.
        
        Returns:
            Current model info or None
        """
        return self.current_model
    
    def is_model_loaded(self) -> bool:
        """
        Check if a model is currently loaded.
        
        Returns:
            True if model is loaded
        """
        return self.loaded_model is not None
    
    def get_model_status(self) -> Dict[str, any]:
        """
        Get current model status.
        
        Returns:
            Dictionary with model status information
        """
        if self.current_model:
            return {
                "name": self.current_model.name,
                "model_id": self.current_model.model_id,
                "loaded": self.current_model.is_loaded,
                "loading": self.current_model.loading,
                "error": self.current_model.error,
                "downloaded": self.current_model.is_downloaded()
            }
        else:
            return {
                "name": None,
                "model_id": None,
                "loaded": False,
                "loading": False,
                "error": None,
                "downloaded": False
            }
    
    def set_callbacks(self, 
                     on_loading: Optional[Callable] = None,
                     on_loaded: Optional[Callable] = None,
                     on_error: Optional[Callable] = None,
                     on_progress: Optional[Callable] = None):
        """
        Set callback functions for UI updates.
        
        Args:
            on_loading: Called when model starts loading
            on_loaded: Called when model is loaded
            on_error: Called when model loading fails
            on_progress: Called for progress updates
        """
        self.on_model_loading = on_loading
        self.on_model_loaded = on_loaded
        self.on_model_error = on_error
        self.on_progress_update = on_progress
