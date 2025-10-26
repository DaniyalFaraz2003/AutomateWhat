"""
WhatsApp AI Response Pipeline
==============================
Complete end-to-end pipeline that takes a WhatsApp chat screenshot and generates
an AI-powered suggestion for your next message.

This script combines two powerful modules:
1. Message Extraction (YOLO + OCR): Detects and extracts messages from screenshots
2. AI Response Generation (LLM): Generates natural next message suggestions

Workflow:
---------
1. Load WhatsApp chat screenshot
2. Detect message bubbles using YOLO
3. Identify sender (YOU vs OTHER) based on position
4. Extract text from messages using OCR
5. Feed conversation context to local LLM
6. Generate AI-powered next message suggestion

Requirements:
-------------
    pip install ultralytics opencv-python pytesseract pillow torch transformers accelerate

Usage Examples:
---------------
    # Basic usage - just get the AI suggestion
    python whatsapp_ai_pipeline.py --image "chat.png" --model_weights "runs/train/whatsapp_chat/weights/best.pt"
    
    # Save everything (messages, crops, visualization)
    python whatsapp_ai_pipeline.py --image "chat.png" --model_weights "best.pt" --save_messages "output.txt" --save_crops "crops" --visualize
    
    # Use different LLM model (Use this one)
    python whatsapp_ai_pipeline.py --image "more_images/chat2.png" --model_weights "yolo_models/message_detector.pt" --llm_model "Qwen/Qwen2.5-3B-Instruct" --llm_model_path "./hf_models/qwen2" --verbose
    
    # Adjust AI creativity and response length
    python whatsapp_ai_pipeline.py --image "chat.png" --model_weights "best.pt" --temperature 0.3 --max_tokens 30

Arguments:
----------
    --image              Path to WhatsApp chat screenshot (required)
    --model_weights      Path to trained YOLO model weights (required)
    --confidence         YOLO confidence threshold (default: 0.25)
    --llm_model          HuggingFace model name (default: microsoft/Phi-3-mini-4k-instruct)
    --llm_model_path     Local path to save/load LLM (default: ./hf_models/phi3-mini)
    --temperature        AI creativity level 0.0-1.0 (default: 0.5)
    --max_tokens         Max response length in tokens (default: 100)
    --device             Device for LLM: cuda or cpu (default: cuda)
    --save_messages      Save extracted messages to text file (optional)
    --save_json          Save extracted messages to JSON file (optional)
    --save_crops         Save cropped message images to folder (optional)
    --visualize          Save annotated image with bounding boxes (optional)
    --viz_output         Path for annotated image (default: annotated_pipeline.png)
    --verbose            Show detailed processing information (default: False)

Author: Built with love and AI magic! 🚀
"""

import os
import sys
import argparse
import cv2
import numpy as np
import json
import re
from pathlib import Path

# CRITICAL: Set HuggingFace cache directories BEFORE importing transformers
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HF_CACHE_DIR = os.path.join(SCRIPT_DIR, 'hf_models')
os.environ['HF_HOME'] = HF_CACHE_DIR
os.environ['HF_HUB_CACHE'] = os.path.join(HF_CACHE_DIR, 'hub')
os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.join(HF_CACHE_DIR, 'hub')
os.environ['TRANSFORMERS_CACHE'] = os.path.join(HF_CACHE_DIR, 'transformers')
os.environ['HF_DATASETS_CACHE'] = os.path.join(HF_CACHE_DIR, 'datasets')

# Now import AI libraries
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from ultralytics import YOLO
import pytesseract
from PIL import Image

# Configure Tesseract path (modify if needed on Windows)
pytesseract.pytesseract.tesseract_cmd = r'D:\Tesseract-OCR\tesseract.exe'


# ============================================================================
# MODULE 1: MESSAGE EXTRACTION (YOLO + OCR)
# ============================================================================

class MessageExtractor:
    """
    Extracts text messages from WhatsApp screenshots using YOLO detection and OCR.
    
    This module handles the computer vision pipeline:
    - YOLO object detection for message bubbles
    - Sender identification (YOU vs OTHER)
    - Chronological sorting
    - OCR text extraction
    """
    
    def __init__(self, model_weights, confidence_threshold=0.25, verbose=False):
        """
        Initialize the message extractor.
        
        Args:
            model_weights (str): Path to trained YOLO model weights
            confidence_threshold (float): Confidence threshold for detections
            verbose (bool): Enable detailed logging
        """
        self.confidence_threshold = confidence_threshold
        self.verbose = verbose
        self.model = self._load_model(model_weights)
        self.image = None
        self.detections = []
        self.messages = []
    
    def _log(self, message):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def _load_model(self, model_weights):
        """Load YOLO model from weights file."""
        if not os.path.exists(model_weights):
            raise FileNotFoundError(f"Model weights not found: {model_weights}")
        
        self._log(f"Loading YOLO model from: {model_weights}")
        model = YOLO(model_weights)
        self._log(f"✓ Model loaded! Classes: {model.names}")
        return model
    
    def load_image(self, image_path):
        """
        Load image from file path.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            numpy.ndarray: Loaded image in BGR format
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        self._log(f"Loading image: {image_path}")
        self.image = cv2.imread(image_path)
        
        if self.image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        self._log(f"✓ Image loaded! Size: {self.image.shape[1]}x{self.image.shape[0]}")
        return self.image
    
    def detect_messages(self):
        """
        Run YOLO inference to detect message bubbles.
        
        Returns:
            list: List of detection dictionaries with bbox and confidence
        """
        if self.image is None:
            raise ValueError("No image loaded. Call load_image() first.")
        
        self._log(f"Running YOLO inference (threshold: {self.confidence_threshold})...")
        results = self.model.predict(
            source=self.image,
            conf=self.confidence_threshold,
            save=False,
            verbose=False
        )
        
        result = results[0]
        
        if len(result.boxes) == 0:
            print("⚠️  No messages detected in the image!")
            return []
        
        boxes = result.boxes.xyxy.cpu().numpy()
        confidences = result.boxes.conf.cpu().numpy()
        class_ids = result.boxes.cls.cpu().numpy().astype(int)
        
        self.detections = []
        for i, (box, conf, cls_id) in enumerate(zip(boxes, confidences, class_ids)):
            x1, y1, x2, y2 = box.astype(int)
            
            detection = {
                'id': i,
                'class_name': self.model.names[cls_id],
                'confidence': float(conf),
                'bbox': {'x1': int(x1), 'y1': int(y1), 'x2': int(x2), 'y2': int(y2)},
                'center_y': int((y1 + y2) / 2),
                'center_x': int((x1 + x2) / 2)
            }
            self.detections.append(detection)
        
        self._log(f"✓ Detected {len(self.detections)} message bubbles")
        return self.detections
    
    def identify_sender(self, detection):
        """
        Identify if message is from YOU or OTHER based on X-coordinate.
        
        WhatsApp design: Your messages appear on the right side (>50% width),
        other person's messages appear on the left side (<=50% width).
        
        Args:
            detection (dict): Detection dictionary with bbox information
            
        Returns:
            str: 'YOU' or 'OTHER'
        """
        if self.image is None:
            return 'UNKNOWN'
        
        image_width = self.image.shape[1]
        relative_position = detection['center_x'] / image_width
        
        return 'YOU' if relative_position > 0.5 else 'OTHER'
    
    def sort_chronologically(self):
        """
        Sort detections by Y-coordinate (top to bottom) and identify senders.
        
        Returns:
            list: Sorted list of detections with sender information
        """
        if not self.detections:
            return []
        
        self._log("Sorting messages chronologically and identifying senders...")
        
        for detection in self.detections:
            detection['sender'] = self.identify_sender(detection)
        
        self.detections.sort(key=lambda x: x['center_y'])
        
        you_count = sum(1 for d in self.detections if d['sender'] == 'YOU')
        other_count = sum(1 for d in self.detections if d['sender'] == 'OTHER')
        
        self._log(f"✓ Sorted {len(self.detections)} messages (YOU: {you_count}, OTHER: {other_count})")
        return self.detections
    
    def extract_text(self, crop):
        """
        Extract text from cropped image using Tesseract OCR.
        
        Args:
            crop (numpy.ndarray): Cropped image
            
        Returns:
            str: Extracted text
        """
        # Preprocess: convert to grayscale
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        pil_image = Image.fromarray(gray)
        
        # OCR configuration
        custom_config = r'--oem 3 --psm 6'
        
        try:
            text = pytesseract.image_to_string(pil_image, config=custom_config)
            return text.strip()
        except Exception as e:
            self._log(f"⚠️  OCR failed: {str(e)}")
            return ""
    
    def extract_all_messages(self, save_crops=None):
        """
        Extract text from all detected messages.
        
        Args:
            save_crops (str): Directory to save cropped images (optional)
            
        Returns:
            list: List of message dictionaries with text and metadata
        """
        if not self.detections:
            return []
        
        print(f"Extracting text from {len(self.detections)} messages...")
        
        if save_crops:
            os.makedirs(save_crops, exist_ok=True)
        
        self.messages = []
        
        for idx, detection in enumerate(self.detections, 1):
            bbox = detection['bbox']
            x1, y1, x2, y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']
            
            # Add padding
            padding = 5
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(self.image.shape[1], x2 + padding)
            y2 = min(self.image.shape[0], y2 + padding)
            
            # Crop message
            crop = self.image[y1:y2, x1:x2]
            
            # Save crop if requested
            if save_crops:
                crop_filename = f"msg_{idx:03d}_{detection['sender']}_conf{detection['confidence']:.2f}.png"
                cv2.imwrite(os.path.join(save_crops, crop_filename), crop)
            
            # Extract text
            text = self.extract_text(crop)
            
            message = {
                'index': idx,
                'text': text,
                'sender': detection['sender'],
                'confidence': detection['confidence'],
                'bbox': bbox,
                'is_empty': len(text) == 0
            }
            self.messages.append(message)
            
            self._log(f"  Message {idx}: [{detection['sender']}] {'✓' if text else '✗ (empty)'}")
        
        print(f"✓ Extracted {len(self.messages)} messages")
        return self.messages
    
    def get_conversation_context(self):
        """
        Get conversation context as a list of non-empty messages.
        
        Returns:
            list: List of message dictionaries with sender and text
        """
        return [
            {'sender': msg['sender'], 'text': msg['text']}
            for msg in self.messages
            if not msg['is_empty']
        ]
    
    def save_to_file(self, output_path):
        """Save extracted messages to text file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("EXTRACTED WHATSAPP MESSAGES\n")
            f.write("=" * 80 + "\n\n")
            
            for msg in self.messages:
                f.write(f"Message #{msg['index']} [{msg['sender']}] (Confidence: {msg['confidence']:.2f})\n")
                f.write("-" * 80 + "\n")
                f.write(msg['text'] if msg['text'] else "[No text detected]\n")
                f.write("-" * 80 + "\n\n")
        
        print(f"✓ Messages saved to: {output_path}")
    
    def save_to_json(self, output_path):
        """Save extracted messages to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.messages, f, indent=2, ensure_ascii=False)
        print(f"✓ JSON saved to: {output_path}")
    
    def visualize(self, save_path=None):
        """
        Create annotated image with bounding boxes.
        
        Args:
            save_path (str): Path to save annotated image (optional)
            
        Returns:
            numpy.ndarray: Annotated image
        """
        if self.image is None or not self.detections:
            return None
        
        annotated = self.image.copy()
        color_you = (255, 0, 0)    # Blue for YOU
        color_other = (0, 255, 0)  # Green for OTHER
        
        for idx, detection in enumerate(self.detections, 1):
            bbox = detection['bbox']
            x1, y1, x2, y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']
            sender = detection['sender']
            conf = detection['confidence']
            
            color = color_you if sender == 'YOU' else color_other
            
            # Draw rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"#{idx} [{sender}] ({conf:.2f})"
            (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (x1, y1 - text_height - 10), (x1 + text_width + 5, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 2, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        if save_path:
            cv2.imwrite(save_path, annotated)
            print(f"✓ Annotated image saved to: {save_path}")
        
        return annotated


# ============================================================================
# MODULE 2: AI RESPONSE GENERATOR (LLM)
# ============================================================================

class AIResponseGenerator:
    """
    Generates natural WhatsApp message suggestions using local LLM.
    
    This module handles the AI pipeline:
    - Model downloading and caching
    - Conversation formatting
    - Response generation
    - Post-processing and cleanup
    """
    
    def __init__(self, model_name, model_path, device="cuda", verbose=False):
        """
        Initialize the AI response generator.
        
        Args:
            model_name (str): HuggingFace model name
            model_path (str): Local path to save/load model
            device (str): Device to use (cuda/cpu)
            verbose (bool): Enable detailed logging
        """
        self.model_name = model_name
        self.model_path = model_path
        self.device = device
        self.verbose = verbose
        self.model = None
        self.tokenizer = None
        self.pipe = None
    
    def _log(self, message):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def load_model(self):
        """
        Load or download the LLM model.
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if model exists locally
        config_file = os.path.join(self.model_path, "config.json")
        if os.path.exists(config_file):
            print(f"✓ Model found locally at: {self.model_path}")
            return self._load_from_local()
        
        # Download model
        print(f"📥 Downloading model '{self.model_name}'...")
        print(f"📁 Cache directory: {os.environ['HF_HOME']}")
        print("This may take several minutes...\n")
        
        success = self._download_model()
        if not success:
            return False
        
        return self._load_from_local()
    
    def _download_model(self):
        """Download model and tokenizer from HuggingFace."""
        try:
            os.makedirs(self.model_path, exist_ok=True)
            
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                cache_dir=os.environ['HF_HUB_CACHE'],
            )
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=os.environ['HF_HUB_CACHE']
            )
            
            model.save_pretrained(self.model_path)
            tokenizer.save_pretrained(self.model_path)
            
            print(f"✓ Model downloaded and saved to: {self.model_path}\n")
            return True
        except Exception as e:
            print(f"❌ Download failed: {str(e)}")
            return False
    
    def _load_from_local(self):
        """Load model from local directory."""
        try:
            print(f"Loading model from: {self.model_path}")
            
            # Check CUDA availability
            if self.device == "cuda" and not torch.cuda.is_available():
                print("⚠️  CUDA not available, falling back to CPU")
                self.device = "cpu"
            
            torch.random.manual_seed(0)
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                local_files_only=True,
                device_map=self.device,
                torch_dtype="auto",
                trust_remote_code=True,
            )
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=True
            )
            
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
            )
            
            print(f"✓ Model loaded successfully on {self.device}!\n")
            return True
        except Exception as e:
            print(f"❌ Failed to load model: {str(e)}")
            return False
    
    def format_conversation(self, messages):
        """
        Format conversation messages for LLM prompt.
        
        Args:
            messages (list): List of message dicts with 'sender' and 'text'
            
        Returns:
            str: Formatted conversation string
        """
        conversation = "Here is a WhatsApp conversation:\n\n"
        
        for msg in messages:
            sender_label = "You" if msg['sender'] == 'YOU' else "Other person"
            conversation += f"{sender_label}: {msg['text']}\n"
        
        return conversation
    
    def generate_response(self, messages, temperature=0.5, max_tokens=100):
        """
        Generate AI response based on conversation context.
        
        Args:
            messages (list): List of message dicts with 'sender' and 'text'
            temperature (float): Creativity level (0.0-1.0)
            max_tokens (int): Maximum response length
            
        Returns:
            str: Generated response text or None if failed
        """
        if not messages:
            print("⚠️  No messages to process!")
            return None
        
        if self.pipe is None:
            print("⚠️  Model not loaded!")
            return None
        
        print(f"Generating AI response (temp={temperature}, max_tokens={max_tokens})...")
        
        # Format conversation
        conversation_text = self.format_conversation(messages)
        
        # Build prompt
        user_prompt = f"""{conversation_text}

Write the next message from "You" in this WhatsApp chat. Write ONLY the message text itself, nothing else.

Rules:
- NO explanations, NO introductions, NO "here's a message" 
- ONLY write the actual message you would send
- Keep it short (1-2 sentences max)
- Be natural and conversational

Message:"""
        
        # Prepare chat messages
        chat_messages = [
            {
                "role": "system",
                "content": "You are a helpful AI assistant that suggests natural WhatsApp message responses. You provide only the message text without any commentary or explanations."
            },
            {"role": "user", "content": user_prompt}
        ]
        
        # Generation parameters
        generation_args = {
            "max_new_tokens": max_tokens,
            "return_full_text": False,
            "temperature": temperature,
            "do_sample": True,
        }
        
        try:
            # Generate
            output = self.pipe(chat_messages, **generation_args)
            generated_text = output[0]['generated_text'].strip()
            
            # Post-process to clean up
            generated_text = self._clean_response(generated_text)
            
            print(f"✓ Response generated!\n")
            return generated_text
        except Exception as e:
            print(f"❌ Generation failed: {str(e)}")
            return None
    
    def _clean_response(self, text):
        """
        Clean up generated response by removing meta-commentary.
        
        Args:
            text (str): Raw generated text
            
        Returns:
            str: Cleaned text
        """
        # Remove meta-commentary patterns
        meta_patterns = [
            r'^(Sure,?\s+)?(here\'s|here is)\s+(a\s+)?(short\s+)?(message|response).*?:\s*',
            r'^(You:|Your message:|Response:|Message:)\s*',
            r'^"',  # Leading quote
            r'"$',  # Trailing quote
        ]
        
        for pattern in meta_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        text = text.strip()
        
        # Take only first line
        text = text.split('\n')[0].strip()
        
        # Remove if it starts generating other person's response
        if 'Other person:' in text or 'Other:' in text:
            text = text.split('Other')[0].strip()
        
        # Remove remaining quotes
        text = text.strip('"\'')
        
        # Limit to 2 sentences max
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) > 2:
            text = '. '.join(sentences[:2]).strip() + '.'
        
        return text


# ============================================================================
# MODULE 3: COMPLETE PIPELINE ORCHESTRATOR
# ============================================================================

class WhatsAppAIPipeline:
    """
    Complete end-to-end pipeline that orchestrates message extraction and AI response generation.
    
    This is the main pipeline controller that:
    1. Extracts messages from screenshot
    2. Feeds context to AI
    3. Returns suggested response
    """
    
    def __init__(self, yolo_weights, llm_model, llm_path, config):
        """
        Initialize the complete pipeline.
        
        Args:
            yolo_weights (str): Path to YOLO model weights
            llm_model (str): HuggingFace model name
            llm_path (str): Local path for LLM storage
            config (dict): Configuration parameters
        """
        self.config = config
        
        print("\n" + "=" * 80)
        print("WHATSAPP AI PIPELINE - INITIALIZATION")
        print("=" * 80 + "\n")
        
        # Initialize message extractor
        print("🔧 Initializing Message Extractor...")
        self.extractor = MessageExtractor(
            model_weights=yolo_weights,
            confidence_threshold=config['confidence'],
            verbose=config['verbose']
        )
        print("✓ Message Extractor ready!\n")
        
        # Initialize AI generator
        print("🔧 Initializing AI Response Generator...")
        self.ai_generator = AIResponseGenerator(
            model_name=llm_model,
            model_path=llm_path,
            device=config['device'],
            verbose=config['verbose']
        )
        
        # Load LLM
        success = self.ai_generator.load_model()
        if not success:
            raise RuntimeError("Failed to load LLM model!")
        print("✓ AI Generator ready!\n")
    
    def run(self, image_path):
        """
        Run the complete pipeline on a WhatsApp screenshot.
        
        Args:
            image_path (str): Path to WhatsApp chat screenshot
            
        Returns:
            tuple: (messages, ai_suggestion)
        """
        print("=" * 80)
        print("RUNNING PIPELINE")
        print("=" * 80 + "\n")
        
        # Step 1: Load image
        print("📸 Step 1: Loading image...")
        self.extractor.load_image(image_path)
        print("✓ Image loaded\n")
        
        # Step 2: Detect messages
        print("🔍 Step 2: Detecting message bubbles...")
        detections = self.extractor.detect_messages()
        if not detections:
            print("❌ No messages detected. Pipeline stopped.")
            return [], None
        print("✓ Detection complete\n")
        
        # Step 3: Sort and identify senders
        print("📋 Step 3: Sorting messages chronologically...")
        self.extractor.sort_chronologically()
        print("✓ Sorting complete\n")
        
        # Step 4: Extract text with OCR
        print("📝 Step 4: Extracting text with OCR...")
        messages = self.extractor.extract_all_messages(
            save_crops=self.config.get('save_crops')
        )
        print("✓ Text extraction complete\n")
        
        # Step 5: Get conversation context
        print("💬 Step 5: Preparing conversation context...")
        conversation = self.extractor.get_conversation_context()
        
        if not conversation:
            print("⚠️  No valid messages found for AI context")
            return messages, None
        
        print(f"✓ Context ready ({len(conversation)} messages)\n")
        
        # Step 6: Generate AI response
        print("🤖 Step 6: Generating AI response...")
        ai_suggestion = self.ai_generator.generate_response(
            messages=conversation,
            temperature=self.config['temperature'],
            max_tokens=self.config['max_tokens']
        )
        print("✓ AI response generated\n")
        
        # Optional: Save outputs
        if self.config.get('save_messages'):
            self.extractor.save_to_file(self.config['save_messages'])
        
        if self.config.get('save_json'):
            self.extractor.save_to_json(self.config['save_json'])
        
        if self.config.get('visualize'):
            viz_path = self.config.get('viz_output', 'annotated_pipeline.png')
            self.extractor.visualize(save_path=viz_path)
        
        return messages, ai_suggestion
    
    def display_results(self, messages, suggestion):
        """
        Display pipeline results in a formatted way.
        
        Args:
            messages (list): Extracted messages
            suggestion (str): AI-generated suggestion
        """
        print("\n" + "=" * 80)
        print("PIPELINE RESULTS")
        print("=" * 80 + "\n")
        
        # Display conversation
        print("📱 CONVERSATION:")
        print("-" * 80)
        
        non_empty = [msg for msg in messages if not msg['is_empty']]
        
        for msg in non_empty:
            sender_label = f"[{msg['sender']}]"
            print(f"{sender_label}: {msg['text']}")
        
        print("\n" + "=" * 80)
        print("🤖 AI SUGGESTED NEXT MESSAGE")
        print("=" * 80 + "\n")
        
        if suggestion:
            print(f"💡 {suggestion}")
        else:
            print("⚠️  No suggestion available")
        
        print("\n" + "=" * 80)
        print(f"📊 STATISTICS")
        print("=" * 80)
        print(f"  • Total messages detected: {len(messages)}")
        print(f"  • Messages with text: {len(non_empty)}")
        
        you_count = sum(1 for msg in non_empty if msg['sender'] == 'YOU')
        other_count = sum(1 for msg in non_empty if msg['sender'] == 'OTHER')
        
        print(f"  • Your messages: {you_count}")
        print(f"  • Other person's messages: {other_count}")
        print("=" * 80 + "\n")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main function to run the complete WhatsApp AI pipeline."""
    
    parser = argparse.ArgumentParser(
        description='WhatsApp AI Pipeline - Extract messages and generate AI responses',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python whatsapp_ai_pipeline.py --image "chat.png" --model_weights "runs/train/whatsapp_chat/weights/best.pt"
  
  # Save everything
  python whatsapp_ai_pipeline.py --image "chat.png" --model_weights "best.pt" --save_messages "output.txt" --save_crops "crops" --visualize
  
  # Use different model
  python whatsapp_ai_pipeline.py --image "chat.png" --model_weights "best.pt" --llm_model "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        """
    )
    
    # Required arguments
    parser.add_argument('--image', type=str, required=True,
                        help='Path to WhatsApp chat screenshot image')
    parser.add_argument('--model_weights', type=str, required=True,
                        help='Path to trained YOLO model weights')
    
    # YOLO parameters
    parser.add_argument('--confidence', type=float, default=0.25,
                        help='YOLO confidence threshold (default: 0.25)')
    
    # LLM parameters
    parser.add_argument('--llm_model', type=str, default='microsoft/Phi-3-mini-4k-instruct',
                        help='HuggingFace model name (default: microsoft/Phi-3-mini-4k-instruct)')
    parser.add_argument('--llm_model_path', type=str, default='./hf_models/phi3-mini',
                        help='Local path to save/load LLM (default: ./hf_models/phi3-mini)')
    parser.add_argument('--temperature', type=float, default=0.5,
                        help='AI temperature 0.0-1.0 (default: 0.5, lower=more focused)')
    parser.add_argument('--max_tokens', type=int, default=100,
                        help='Max response length in tokens (default: 100)')
    parser.add_argument('--device', type=str, default='cuda', choices=['cuda', 'cpu'],
                        help='Device for LLM inference (default: cuda)')
    
    # Output options
    parser.add_argument('--save_messages', type=str, default=None,
                        help='Save extracted messages to text file (optional)')
    parser.add_argument('--save_json', type=str, default=None,
                        help='Save extracted messages to JSON file (optional)')
    parser.add_argument('--save_crops', type=str, default=None,
                        help='Save cropped message images to folder (optional)')
    parser.add_argument('--visualize', action='store_true',
                        help='Save annotated image with bounding boxes')
    parser.add_argument('--viz_output', type=str, default='annotated_pipeline.png',
                        help='Path for annotated image (default: annotated_pipeline.png)')
    
    # Misc options
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed processing information')
    
    args = parser.parse_args()
    
    # Prepare configuration
    config = {
        'confidence': args.confidence,
        'temperature': args.temperature,
        'max_tokens': args.max_tokens,
        'device': args.device,
        'save_messages': args.save_messages,
        'save_json': args.save_json,
        'save_crops': args.save_crops,
        'visualize': args.visualize,
        'viz_output': args.viz_output,
        'verbose': args.verbose
    }
    
    # Display configuration
    print("\n" + "=" * 80)
    print("WHATSAPP AI PIPELINE")
    print("=" * 80)
    print("\n📋 Configuration:")
    print(f"  • Input image: {args.image}")
    print(f"  • YOLO weights: {args.model_weights}")
    print(f"  • YOLO confidence: {args.confidence}")
    print(f"  • LLM model: {args.llm_model}")
    print(f"  • LLM path: {args.llm_model_path}")
    print(f"  • Temperature: {args.temperature}")
    print(f"  • Max tokens: {args.max_tokens}")
    print(f"  • Device: {args.device}")
    if args.save_messages:
        print(f"  • Save messages: {args.save_messages}")
    if args.save_json:
        print(f"  • Save JSON: {args.save_json}")
    if args.save_crops:
        print(f"  • Save crops: {args.save_crops}")
    if args.visualize:
        print(f"  • Visualization: {args.viz_output}")
    print("=" * 80)
    
    try:
        # Initialize pipeline
        pipeline = WhatsAppAIPipeline(
            yolo_weights=args.model_weights,
            llm_model=args.llm_model,
            llm_path=args.llm_model_path,
            config=config
        )
        
        # Run pipeline
        messages, ai_suggestion = pipeline.run(args.image)
        
        # Display results
        pipeline.display_results(messages, ai_suggestion)
        
        print("\n" + "=" * 80)
        print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 80 + "\n")
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
