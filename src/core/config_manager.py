"""
Configuration Manager - Dev/prod profiles with environment switching.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """
    Manages configuration profiles for development and production.

    Supports:
    - Environment-based profile switching (dev/prod)
    - Local overrides via config/local.json
    - Dot-notation key access
    """

    ENVIRONMENTS = ("development", "production", "testing")

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._config: Dict[str, Any] = {}
        self._env = os.environ.get("JARVIS_ENV", "development")
        self._load()

    def _load(self) -> None:
        """Load base config then apply environment overrides."""
        base_path = self.config_dir / "config.json"
        if base_path.exists():
            with open(base_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)

        # Apply environment-specific overrides
        env_path = self.config_dir / f"config.{self._env}.json"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                env_config = json.load(f)
            self._deep_merge(self._config, env_config)

        # Apply local overrides (not committed to git)
        local_path = self.config_dir / "local.json"
        if local_path.exists():
            with open(local_path, "r", encoding="utf-8") as f:
                local_config = json.load(f)
            self._deep_merge(self._config, local_config)

        # Set environment in config
        self._config["environment"] = self._env

    def _deep_merge(self, base: dict, override: dict) -> None:
        """Recursively merge override into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a config value using dot notation.

        Args:
            key: Dot-separated key path (e.g. 'ollama.port')
            default: Default value if key not found

        Returns:
            Config value or default
        """
        parts = key.split(".")
        value = self._config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a config value using dot notation (in-memory only)."""
        parts = key.split(".")
        target = self._config
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value

    @property
    def environment(self) -> str:
        return self._env

    @property
    def is_development(self) -> bool:
        return self._env == "development"

    @property
    def is_production(self) -> bool:
        return self._env == "production"

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._config)
