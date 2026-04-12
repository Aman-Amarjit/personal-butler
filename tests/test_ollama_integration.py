"""Unit tests for Ollama integration"""

import pytest
from src.core.ollama_integration import (
    OllamaIntegration,
    ModelSize,
    ResourceMetrics
)


class TestOllamaIntegration:
    """Test Ollama integration"""

    def test_initialization(self):
        """Test Ollama initialization"""
        ollama = OllamaIntegration(
            host="http://localhost",
            port=11434,
            model_size=ModelSize.MEDIUM
        )
        
        assert ollama.host == "http://localhost"
        assert ollama.port == 11434
        assert ollama.model_size == ModelSize.MEDIUM
        assert ollama.current_model == "mistral:7b"

    def test_model_switching(self):
        """Test switching between models"""
        ollama = OllamaIntegration()
        
        # Switch to small model
        ollama.switch_model(ModelSize.SMALL)
        assert ollama.current_model == "mistral:3b"
        
        # Switch to large model
        ollama.switch_model(ModelSize.LARGE)
        assert ollama.current_model == "mistral:13b"

    def test_resource_metrics(self):
        """Test resource metrics collection"""
        ollama = OllamaIntegration()
        metrics = ollama.get_resource_usage()
        
        assert isinstance(metrics, ResourceMetrics)
        assert 0 <= metrics.cpu_percent <= 100
        assert 0 <= metrics.memory_percent <= 100
        assert metrics.memory_mb >= 0
        assert 0 <= metrics.disk_percent <= 100

    def test_status_dict(self):
        """Test status dictionary"""
        ollama = OllamaIntegration()
        status = ollama.get_status()
        
        assert "running" in status
        assert "current_model" in status
        assert "resources" in status
        assert "available_models" in status

    def test_fallback_response(self):
        """Test fallback response generation"""
        ollama = OllamaIntegration()
        response = ollama.handle_unavailable()
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert "unavailable" in response.lower() or "unable" in response.lower()

    def test_model_size_enum(self):
        """Test ModelSize enum"""
        assert ModelSize.SMALL.value == "3b"
        assert ModelSize.MEDIUM.value == "7b"
        assert ModelSize.LARGE.value == "13b"
