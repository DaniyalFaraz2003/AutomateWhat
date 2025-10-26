"""
Test script for Model Management System.
This script tests the model detection and loading functionality.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.model_manager import ModelManager, ModelInfo
from config.settings import AppConfig


def test_model_scanning():
    """Test model scanning functionality."""
    print("🔍 Testing Model Detection...")
    
    config = AppConfig()
    manager = ModelManager(config)
    
    # Get available models (lazy loading)
    models = manager.get_available_models()
    
    print(f"Found {len(models)} predefined models:")
    for model in models:
        print(f"  - {model}")
        print(f"    Model ID: {model.model_id}")
        print(f"    Local Path: {model.get_local_path()}")
        print(f"    Downloaded: {model.is_downloaded()}")
    
    return models


def test_model_info():
    """Test ModelInfo class."""
    print("\n📋 Testing ModelInfo...")
    
    # Test with a predefined model
    model_info = ModelInfo("Test Model", "test/model-id")
    print(f"Model Info: {model_info}")
    print(f"Model ID: {model_info.model_id}")
    print(f"Local Path: {model_info.get_local_path()}")
    print(f"Downloaded: {model_info.is_downloaded()}")
    print(f"Loaded: {model_info.is_loaded}")


def test_model_manager():
    """Test ModelManager functionality."""
    print("\n🎛️ Testing ModelManager...")
    
    config = AppConfig()
    manager = ModelManager(config)
    
    # Test callbacks
    def on_loading(name):
        print(f"  Loading: {name}")
    
    def on_loaded(name):
        print(f"  Loaded: {name}")
    
    def on_error(error):
        print(f"  Error: {error}")
    
    def on_progress(progress):
        print(f"  Progress: {progress}")
    
    manager.set_callbacks(on_loading, on_loaded, on_error, on_progress)
    
    # Get available models
    models = manager.get_available_models()
    
    if models:
        print(f"Available models: {manager.get_model_names()}")
        
        # Test model status
        status = manager.get_model_status()
        print(f"Current status: {status}")
        
        print("Model manager test completed successfully!")
    else:
        print("No models found for testing")


def main():
    """Run all tests."""
    print("🚀 AutomateWhat Model Management Test")
    print("=" * 50)
    
    try:
        # Test model scanning
        models = test_model_scanning()
        
        # Test model info
        test_model_info()
        
        # Test model manager
        test_model_manager()
        
        print("\n✅ All tests completed successfully!")
        
        if models:
            print(f"\n📊 Summary:")
            print(f"  - Found {len(models)} predefined models")
            print(f"  - Model names: {[m.name for m in models]}")
            print(f"  - Model IDs: {[m.model_id for m in models]}")
            print(f"  - Downloaded models: {sum(1 for m in models if m.is_downloaded())}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
