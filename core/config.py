"""
Configuration loader for Anvil.
Handles API keys and other settings.
"""

from pathlib import Path
from typing import Optional
import os

try:
    import yaml
except ImportError:
    yaml = None


def get_config_dir() -> Path:
    """Get the config directory path."""
    return Path(__file__).parent.parent / "config"


def load_api_key() -> Optional[str]:
    """
    Load Anthropic API key from config or environment.

    Priority:
    1. ANTHROPIC_API_KEY environment variable
    2. config/api_keys.yaml file

    Returns:
        API key string or None if not found
    """
    # Check environment first
    env_key = os.environ.get('ANTHROPIC_API_KEY')
    if env_key:
        return env_key

    # Check config file
    config_path = get_config_dir() / "api_keys.yaml"
    if config_path.exists() and yaml:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config and 'api_key' in config:
                    return config['api_key']
        except Exception:
            pass

    return None


def has_api_key() -> bool:
    """Check if API key is configured."""
    return load_api_key() is not None
