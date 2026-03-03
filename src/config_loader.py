"""Configuration loader for the conversion system."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings


class AgentConfig(BaseSettings):
    """Configuration for AI agents."""
    
    model: str = "claude-3-5-sonnet-20240620"
    temperature: float = 0.1
    max_tokens: int = 4096


class DebuggingAgentConfig(AgentConfig):
    """Configuration for debugging agent."""
    
    temperature: float = 0.2
    max_tokens: int = 8192
    max_iterations: int = 3


class ConversionConfig(BaseSettings):
    """Configuration for conversion process."""
    
    rules_file: str = "rules/conversion_rules.yaml"
    validation_enabled: bool = True
    test_execution: bool = True


class StarRocksConfig(BaseSettings):
    """Configuration for StarRocks connection."""
    
    host: str = Field(default="localhost")
    port: int = Field(default=9030)
    database: str = Field(default="test_db")
    user: str = Field(default="root")
    password: str = Field(default="")


class LoggingConfig(BaseSettings):
    """Configuration for logging."""
    
    level: str = "INFO"
    format: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    file: str = "logs/converter.log"
    rotation: str = "10 MB"
    retention: str = "7 days"


class Settings(BaseSettings):
    """Main settings class."""
    
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    max_debug_iterations: int = Field(default=3, alias="MAX_DEBUG_ITERATIONS")
    validation_timeout: int = Field(default=30, alias="VALIDATION_TIMEOUT")
    enable_validation: bool = Field(default=True, alias="ENABLE_VALIDATION")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


class ConfigLoader:
    """Loads and manages configuration from YAML and environment variables."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration loader.
        
        Args:
            config_path: Path to config.yaml file. Defaults to project root.
        """
        load_dotenv()
        
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        self.config_path = config_path
        self._config_data: Dict[str, Any] = {}
        self._load_config()
        
        self.settings = Settings()
        self.connection_converter = AgentConfig(**self._config_data.get("agents", {}).get("connection_converter", {}))
        self.debugging_agent = DebuggingAgentConfig(**self._config_data.get("agents", {}).get("debugging_agent", {}))
        self.conversion = ConversionConfig(**self._config_data.get("conversion", {}))
        self.starrocks = self._load_starrocks_config()
        self.logging = LoggingConfig(**self._config_data.get("logging", {}))
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, "r") as f:
            self._config_data = yaml.safe_load(f) or {}
    
    def _load_starrocks_config(self) -> StarRocksConfig:
        """Load StarRocks configuration with environment variable substitution."""
        starrocks_data = self._config_data.get("starrocks", {})
        
        # Substitute environment variables
        resolved_data = {}
        for key, value in starrocks_data.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                resolved_data[key] = os.getenv(env_var, "")
            else:
                resolved_data[key] = value
        
        return StarRocksConfig(**resolved_data)
    
    def get_conversion_rules(self) -> Dict[str, Any]:
        """Load conversion rules from YAML file.
        
        Returns:
            Dictionary containing conversion rules.
        """
        rules_path = Path(__file__).parent.parent / self.conversion.rules_file
        
        if not rules_path.exists():
            raise FileNotFoundError(f"Conversion rules file not found: {rules_path}")
        
        with open(rules_path, "r") as f:
            return yaml.safe_load(f) or {}


def load_config(config_path: Optional[Path] = None) -> ConfigLoader:
    """Load configuration.
    
    Args:
        config_path: Optional path to config.yaml file.
        
    Returns:
        ConfigLoader instance.
    """
    return ConfigLoader(config_path)
