"""
AI Pipeline integration for AutomateWhat.

This module wires together:
- Message extraction (YOLO + OCR) from utils.whatsapp_ai_pipeline.MessageExtractor
- Response generation using an already loaded HuggingFace pipeline from ModelManager

Design goals:
- Non-blocking: background worker thread + queue
- Safe: robust error handling, recoverable failures
- Efficient: basic result caching and duplicate image suppression
"""

import os
import logging
import threading
import queue
import hashlib
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List

import cv2

# Reuse the existing extraction logic
from utils.whatsapp_ai_pipeline import MessageExtractor


class AIPipelineManager:
    """
    Manages end-to-end processing of screenshots into extracted conversation and AI response.

    It expects a HuggingFace text-generation pipeline to be already loaded via ModelManager.
    """

    def __init__(self, config, get_loaded_model_callable: Callable[[], Optional[Any]]):
        self.config = config
        self.logger = logging.getLogger("AutomateWhat.AIPipeline")
        self._get_loaded_model = get_loaded_model_callable

        # YOLO model path (must exist)
        self.yolo_weights_path = (self.config.root_dir / "models" / "yolo_models" / "message_detector.pt").resolve()

        # Processing
        self._work_queue: "queue.Queue[Path]" = queue.Queue(maxsize=4)
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_image_hash: Optional[str] = None
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._conversation_messages: List[Dict[str, Any]] = []  # persistent conversation state
        self._blocking_mode: bool = True  # default to blocking per requirements

        # Callbacks
        self.on_processing_started: Optional[Callable[[], None]] = None
        self.on_processing_finished: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        # Lazy extractor (constructed when first needed)
        self._extractor: Optional[MessageExtractor] = None

    def start(self):
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        self.logger.info("AI Pipeline worker started")

    def stop(self):
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
        self.logger.info("AI Pipeline worker stopped")

    def set_callbacks(self,
                      on_started: Optional[Callable[[], None]] = None,
                      on_finished: Optional[Callable[[Dict[str, Any]], None]] = None,
                      on_error: Optional[Callable[[str], None]] = None):
        self.on_processing_started = on_started
        self.on_processing_finished = on_finished
        self.on_error = on_error

    def enqueue_image_path(self, image_path: Path):
        try:
            if not image_path or not Path(image_path).exists():
                return

            if self._blocking_mode:
                # Run synchronously if changed
                result = self.process_latest_if_changed(Path(image_path))
                if result and self.on_processing_finished:
                    self.on_processing_finished(result)
                return
            else:
                # Async path (kept for future use)
                # Compute quick hash to suppress duplicates
                image_hash = self._hash_file(image_path)
                if self._last_image_hash == image_hash:
                    return
                self._last_image_hash = image_hash

                # Cache hit: surface result immediately
                if image_hash in self._cache:
                    if self.on_processing_finished:
                        self.on_processing_finished(self._cache[image_hash])
                    return

                # Start worker if not running
                self.start()

                # Non-blocking enqueue (drop oldest if full)
                try:
                    self._work_queue.put_nowait(Path(image_path))
                except queue.Full:
                    _ = self._work_queue.get_nowait()
                    self._work_queue.put_nowait(Path(image_path))
        except Exception as e:
            self._emit_error(f"Failed to enqueue image: {str(e)}")

    def process_latest_if_changed(self, image_path: Path, force_process: bool = False) -> Optional[Dict[str, Any]]:
        """
        Blocking path: compare current screenshot with last processed. If identical, no-op.
        If changed, run extraction, update internal conversation state, generate response, and return result.
        """
        try:
            image_hash = self._hash_file(image_path)
            if self._last_image_hash == image_hash and not force_process:
                return None
            self._last_image_hash = image_hash

            if self.on_processing_started:
                try:
                    self.on_processing_started()
                except Exception:
                    pass

            # Process image to get all messages
            tmp_result = self._process_image(image_path, generate_response=False)
            frame_messages = [m for m in tmp_result.get("conversation", []) if not m.get('is_empty')]

            # Determine newest message in this frame (chronologically sorted -> last)
            last_frame_msg = frame_messages[-1] if frame_messages else None

            last_message_is_other = False
            last_message_is_you = False
            new_messages: List[Dict[str, Any]] = []

            if not self._conversation_messages:
                # First initialization: seed full history
                self._conversation_messages = frame_messages.copy()
                if last_frame_msg:
                    if last_frame_msg.get('sender') == 'OTHER':
                        last_message_is_other = True
                    elif last_frame_msg.get('sender') == 'YOU':
                        last_message_is_you = True
                # For UI seeding purposes, expose all as new on first run
                new_messages = frame_messages[-1:] if frame_messages else []
            else:
                # Subsequent runs: append ONLY the last newest message if it differs from current last
                def norm(s: str) -> str:
                    return (s or '').strip()

                prev_last = self._conversation_messages[-1] if self._conversation_messages else None
                if last_frame_msg:
                    is_different = (
                        prev_last is None or
                        prev_last.get('sender') != last_frame_msg.get('sender') or
                        norm(prev_last.get('text')) != norm(last_frame_msg.get('text'))
                    )
                    if is_different:
                        self._conversation_messages.append(last_frame_msg)
                        new_messages = [last_frame_msg]
                        if last_frame_msg.get('sender') == 'OTHER':
                            last_message_is_other = True
                        elif last_frame_msg.get('sender') == 'YOU':
                            last_message_is_you = True

            # Decide generation strictly on newest message being OTHER, or forced, or if no history
            should_generate = force_process or last_message_is_other or len(self._conversation_messages) == 0

            # Generate response only if needed
            result = self._process_image(image_path, generate_response=should_generate)

            result_with_state = {
                **result,
                "conversation": self._conversation_messages,
                "new_messages": new_messages,
                "last_message_is_other": last_message_is_other,
                "last_message_is_you": last_message_is_you,
            }

            # Cache under hash
            self._cache[image_hash] = result_with_state

            return result_with_state
        except Exception as e:
            self._emit_error(f"Blocking processing failed: {str(e)}")
            return None

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                image_path: Path = self._work_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                if self.on_processing_started:
                    self.on_processing_started()

                result = self._process_image(image_path)

                # Cache by hash
                img_hash = self._hash_file(image_path)
                self._cache[img_hash] = result

                if self.on_processing_finished:
                    self.on_processing_finished(result)
            except Exception as e:
                self._emit_error(f"Processing failed: {str(e)}")
            finally:
                self._work_queue.task_done()

    def _process_image(self, image_path: Path, generate_response: bool = True) -> Dict[str, Any]:
        # Preconditions
        if not self.yolo_weights_path.exists():
            raise FileNotFoundError(f"YOLO weights not found at {self.yolo_weights_path}")

        # Ensure extractor exists (build with config verbosity and threshold)
        if self._extractor is None:
            self._extractor = MessageExtractor(
                model_weights=str(self.yolo_weights_path),
                confidence_threshold=0.25,
                verbose=False,
            )

        # Load image via extractor
        self._extractor.load_image(str(image_path))
        detections = self._extractor.detect_messages()
        if not detections:
            return {
                "success": False,
                "message": "No messages detected",
                "conversation": [],
                "ai_response": None,
            }

        self._extractor.sort_chronologically()
        messages = self._extractor.extract_all_messages()
        conversation = self._extractor.get_conversation_context()

        # Generate response using loaded model pipeline (conditionally)
        response_text = None
        if generate_response:
            text_gen_pipe = self._get_loaded_model()
            if text_gen_pipe and conversation:
                prompt = self._build_prompt(conversation)
                try:
                    gen = text_gen_pipe(
                        [
                            {"role": "system", "content": "You are a helpful AI assistant that suggests natural WhatsApp message responses. Provide only the message text."},
                            {"role": "user", "content": prompt},
                        ],
                        max_new_tokens=100,
                        return_full_text=False,
                        temperature=0.5,
                        do_sample=True,
                    )
                    raw_text = gen[0].get("generated_text", "").strip()
                    response_text = self._clean_response(raw_text)
                except Exception as e:
                    self.logger.error(f"Generation failed: {str(e)}")
                    response_text = None

        return {
            "success": True,
            "message": "Processed successfully",
            "conversation": messages,
            "ai_response": response_text,
        }

    def _merge_conversation(self, new_messages: List[Dict[str, Any]]):
        """Append new non-empty messages that are not already in the state.

        Uniqueness key = (sender, normalized text). Keeps chronological order.
        """
        def norm(s: str) -> str:
            return (s or '').strip()

        existing_keys = set(
            (m.get('sender'), norm(m.get('text'))) for m in self._conversation_messages if not m.get('is_empty')
        )
        for m in new_messages:
            if m.get('is_empty'):
                continue
            key = (m.get('sender'), norm(m.get('text')))
            if key not in existing_keys:
                self._conversation_messages.append(m)
                existing_keys.add(key)

    def _diff_new_messages(self, candidate_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return messages that are not yet in conversation state (non-empty)."""
        def norm(s: str) -> str:
            return (s or '').strip()
        existing_keys = set(
            (m.get('sender'), norm(m.get('text'))) for m in self._conversation_messages if not m.get('is_empty')
        )
        diff: List[Dict[str, Any]] = []
        for m in candidate_messages:
            if m.get('is_empty'):
                continue
            key = (m.get('sender'), norm(m.get('text')))
            if key not in existing_keys:
                diff.append(m)
        return diff

    def _build_prompt(self, messages: List[Dict[str, str]]) -> str:
        conversation_text = "Here is a WhatsApp conversation:\n\n"
        for msg in messages:
            sender_label = "You" if msg["sender"] == "YOU" else "Other person"
            conversation_text += f"{sender_label}: {msg['text']}\n"

        user_prompt = f"""{conversation_text}

Write the next message from \"You\" in this WhatsApp chat. Write ONLY the message text itself, nothing else.

Rules:
- NO explanations, NO introductions, NO \"here's a message\" 
- ONLY write the actual message you would send
- Keep it short (1-2 sentences max)
- Be natural and conversational

Message:"""
        return user_prompt

    def _clean_response(self, text: str) -> str:
        import re
        patterns = [
            r'^(Sure,?\s+)?(here\'s|here is)\s+(a\s+)?(short\s+)?(message|response).*?:\s*',
            r'^(You:|Your message:|Response:|Message:)\s*',
            r'^"',
            r'"$',
        ]
        for p in patterns:
            text = re.sub(p, '', text, flags=re.IGNORECASE)
        text = text.strip()
        text = text.split('\n')[0].strip()
        if 'Other person:' in text or 'Other:' in text:
            text = text.split('Other')[0].strip()
        text = text.strip('\"\'\'')
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) > 2:
            text = '. '.join(sentences[:2]).strip() + '.'
        return text

    def _hash_file(self, path: Path) -> str:
        try:
            h = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return os.path.getmtime(path.as_posix()).__repr__()

    def _emit_error(self, message: str):
        self.logger.error(message)
        if self.on_error:
            try:
                self.on_error(message)
            except Exception:
                pass


