"""
Ollama Integration Layer

Manages local LLM inference through Ollama with resource monitoring,
model management, and graceful fallback handling.
"""

import requests
import json
import logging
import psutil
import subprocess
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


logger = logging.getLogger(__name__)


class ModelSize(Enum):
    """Available Ollama model sizes"""
    SMALL = "3b"
    MEDIUM = "7b"
    LARGE = "13b"


@dataclass
class ResourceMetrics:
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_percent: float


class OllamaIntegration:
    """
    Manages Ollama LLM integration with resource monitoring.
    
    Features:
    - Connection management and health checks
    - Model download and verification
    - Resource monitoring (CPU, memory, disk)
    - Graceful fallback when unavailable
    - Model size selection and switching
    """

    def __init__(
        self,
        host: str = "http://localhost",
        port: int = 11434,
        model_size: ModelSize = ModelSize.MEDIUM,
        timeout: int = 30
    ):
        """
        Initialize Ollama integration.

        Args:
            host: Ollama server host
            port: Ollama server port
            model_size: Default model size
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.base_url = f"{host}:{port}"
        self.model_size = model_size
        self.timeout = timeout

        # Model mapping
        self.models = {
            ModelSize.SMALL: "mistral:3b",
            ModelSize.MEDIUM: "mistral:7b",
            ModelSize.LARGE: "mistral:13b"
        }

        self.current_model = self.models[model_size]
        self.is_running = False
        self.last_error = None
        self._auto_model_selected = False

    def verify_running(self) -> bool:
        """
        Verify Ollama server is running and auto-select an available model.
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=self.timeout
            )
            self.is_running = response.status_code == 200
            if self.is_running and not self._auto_model_selected:
                # Auto-select first available model instead of failing on missing model
                try:
                    data = response.json()
                    available = [m["name"] for m in data.get("models", [])]
                    if available and self.current_model not in available:
                        self.current_model = available[0]
                        logger.info(f"Auto-selected Ollama model: {self.current_model}")
                    self._auto_model_selected = True
                except Exception:
                    pass
            return self.is_running
        except requests.exceptions.RequestException as e:
            self.is_running = False
            self.last_error = str(e)
            logger.warning(f"Ollama server not accessible: {e}")
            return False

    def start_ollama(self) -> bool:
        """
        Attempt to start Ollama server.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            logger.info("Attempting to start Ollama server...")
            # Try to start Ollama (Windows)
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for server to start
            import time
            for _ in range(10):
                if self.verify_running():
                    logger.info("Ollama server started successfully")
                    return True
                time.sleep(1)
            
            logger.error("Ollama server failed to start")
            return False
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            self.last_error = str(e)
            return False

    def pull_model(self, model_name: str) -> bool:
        """
        Download a model from Ollama registry.

        Args:
            model_name: Model name (e.g., "mistral:7b")

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Pulling model: {model_name}")
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=300  # Long timeout for download
            )
            
            if response.status_code == 200:
                logger.info(f"Model {model_name} pulled successfully")
                return True
            else:
                logger.error(f"Failed to pull model: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            self.last_error = str(e)
            return False

    def list_models(self) -> List[str]:
        """
        List available models on Ollama server.

        Returns:
            List of model names
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                logger.info(f"Available models: {models}")
                return models
            else:
                logger.warning("Failed to list models")
                return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    def send_request(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Send a request to Ollama for text generation.

        Args:
            prompt: Input prompt
            context: Optional context for the prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text or None if failed
        """
        if not self.is_running:
            if not self.verify_running():
                logger.error("Ollama not running")
                return None

        try:
            full_prompt = f"{context}\n{prompt}" if context else prompt

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.current_model,
                    "prompt": full_prompt,
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "stream": False
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                generated_text = data.get("response", "").strip()
                logger.debug(f"Generated response: {generated_text[:100]}...")
                return generated_text
            else:
                logger.error(f"Ollama request failed: {response.text}")
                self.last_error = response.text
                return None
        except Exception as e:
            logger.error(f"Error sending request to Ollama: {e}")
            self.last_error = str(e)
            return None

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Send a chat request to Ollama using the /api/chat endpoint with message history.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                      Roles: 'system', 'user', 'assistant'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Assistant reply text or None if failed
        """
        if not self.is_running:
            if not self.verify_running():
                logger.error("Ollama not running")
                return None

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.current_model,
                    "messages": messages,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                    "stream": False,
                },
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                reply = data.get("message", {}).get("content", "").strip()
                logger.debug(f"Chat response: {reply[:100]}...")
                return reply
            else:
                logger.error(f"Ollama chat request failed: {response.text}")
                self.last_error = response.text
                return None
        except Exception as e:
            logger.error(f"Error sending chat request to Ollama: {e}")
            self.last_error = str(e)
            return None

    def switch_model(self, model_size: ModelSize) -> bool:
        """
        Switch to a different model size.

        Args:
            model_size: Target model size

        Returns:
            True if successful, False otherwise
        """
        try:
            new_model = self.models[model_size]
            
            # Check if model is available
            available_models = self.list_models()
            if not any(new_model in m for m in available_models):
                logger.warning(f"Model {new_model} not available, pulling...")
                if not self.pull_model(new_model):
                    return False

            self.current_model = new_model
            self.model_size = model_size
            logger.info(f"Switched to model: {new_model}")
            return True
        except Exception as e:
            logger.error(f"Error switching model: {e}")
            self.last_error = str(e)
            return False

    def get_resource_usage(self) -> ResourceMetrics:
        """
        Get current system resource usage.

        Returns:
            ResourceMetrics with CPU, memory, and disk usage
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            metrics = ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=memory.used / (1024 * 1024),
                disk_percent=disk.percent
            )

            logger.debug(
                f"Resources - CPU: {cpu_percent}%, "
                f"Memory: {memory.percent}% ({memory.used / (1024**3):.1f}GB), "
                f"Disk: {disk.percent}%"
            )

            return metrics
        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return ResourceMetrics(0, 0, 0, 0)

    def check_resource_constraints(self) -> bool:
        """
        Check if system has sufficient resources for LLM.

        Returns:
            True if resources are sufficient, False otherwise
        """
        metrics = self.get_resource_usage()

        # Check memory (need at least 2GB free)
        total_memory = psutil.virtual_memory().total / (1024**3)
        free_memory = (total_memory - metrics.memory_mb / 1024)

        if free_memory < 2:
            logger.warning(f"Insufficient memory: {free_memory:.1f}GB free")
            return False

        # Check disk (need at least 5GB free)
        disk = psutil.disk_usage("/")
        free_disk = disk.free / (1024**3)

        if free_disk < 5:
            logger.warning(f"Insufficient disk space: {free_disk:.1f}GB free")
            return False

        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive Ollama status.

        Returns:
            Dictionary with status information
        """
        metrics = self.get_resource_usage()
        models = self.list_models()

        return {
            "running": self.is_running,
            "current_model": self.current_model,
            "available_models": models,
            "resources": {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "memory_mb": metrics.memory_mb,
                "disk_percent": metrics.disk_percent
            },
            "last_error": self.last_error
        }

    def handle_unavailable(self) -> str:
        """
        Generate fallback response when Ollama is unavailable.

        Returns:
            Fallback response text
        """
        logger.warning("Ollama unavailable, using fallback response")
        return (
            "I'm currently unable to process that request as my AI engine "
            "is not available. Please ensure Ollama is running and try again."
        )

    def generate_fallback_response(self, prompt: str) -> str:
        """
        Return a fallback response without calling Ollama.

        Args:
            prompt: User prompt (used for context only)

        Returns:
            Fallback response string
        """
        return self.handle_unavailable()
