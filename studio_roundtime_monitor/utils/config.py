"""
Configuration management for Studio Round Time Monitor.

Provides configuration loading and validation for the monitoring system.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)

class MonitorConfigModel(BaseModel):
    """Pydantic model for monitor configuration validation."""

    enabled: bool = Field(default=True, description="Enable monitoring")
    tableapi_enabled: bool = Field(default=True, description="Enable TableAPI monitoring")
    roulette_enabled: bool = Field(default=True, description="Enable Roulette monitoring")
    sicbo_enabled: bool = Field(default=True, description="Enable Sicbo monitoring")

class StorageConfigModel(BaseModel):
    """Pydantic model for storage configuration validation."""

    type: str = Field(default="json", description="Storage type (json, csv, database)")
    path: str = Field(default="./data/time_intervals.json", description="Storage path")
    database_url: Optional[str] = Field(default=None, description="Database URL for database storage")

class ProcessingConfigModel(BaseModel):
    """Pydantic model for processing configuration validation."""

    interval: float = Field(default=5.0, description="Processing interval in seconds")
    max_history: int = Field(default=1000, description="Maximum number of intervals to keep in memory")

@dataclass
class MonitorConfig:
    """Configuration class for the monitoring system."""

    monitor: MonitorConfigModel = field(default_factory=MonitorConfigModel)
    storage: StorageConfigModel = field(default_factory=StorageConfigModel)
    processing: ProcessingConfigModel = field(default_factory=ProcessingConfigModel)

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate configuration values."""
        if self.storage.type not in ["json", "csv", "database"]:
            raise ValueError(f"Invalid storage type: {self.storage.type}")

        if self.storage.type == "database" and not self.storage.database_url:
            raise ValueError("Database URL is required for database storage")

        if self.processing.interval <= 0:
            raise ValueError("Processing interval must be positive")

        if self.processing.max_history <= 0:
            raise ValueError("Max history must be positive")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "monitor": self.monitor.dict(),
            "storage": self.storage.dict(),
            "processing": self.processing.dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonitorConfig":
        """Create configuration from dictionary."""
        monitor_data = data.get("monitor", {})
        storage_data = data.get("storage", {})
        processing_data = data.get("processing", {})

        return cls(
            monitor=MonitorConfigModel(**monitor_data),
            storage=StorageConfigModel(**storage_data),
            processing=ProcessingConfigModel(**processing_data)
        )

def load_config(config_path: Optional[str] = None) -> MonitorConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration file. If None, uses default path.

    Returns:
        MonitorConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
        ValueError: If config validation fails
    """
    if config_path is None:
        config_path = "config/monitor_config.yaml"

    config_file = Path(config_path)

    if not config_file.exists():
        logger.warning("Config file not found, using default configuration",
                      config_path=str(config_file))
        return MonitorConfig()

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if data is None:
            logger.warning("Config file is empty, using default configuration")
            return MonitorConfig()

        config = MonitorConfig.from_dict(data)
        logger.info("Configuration loaded successfully", config_path=str(config_file))

        return config

    except yaml.YAMLError as e:
        logger.error("Invalid YAML in config file", config_path=str(config_file), error=str(e))
        raise
    except Exception as e:
        logger.error("Error loading configuration", config_path=str(config_file), error=str(e))
        raise

def save_config(config: MonitorConfig, config_path: str) -> None:
    """
    Save configuration to YAML file.

    Args:
        config: Configuration to save
        config_path: Path to save configuration file
    """
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, indent=2)

        logger.info("Configuration saved successfully", config_path=str(config_file))

    except Exception as e:
        logger.error("Error saving configuration", config_path=str(config_file), error=str(e))
        raise

def create_default_config(config_path: str) -> MonitorConfig:
    """
    Create default configuration and save to file.

    Args:
        config_path: Path to save default configuration

    Returns:
        Default MonitorConfig instance
    """
    config = MonitorConfig()
    save_config(config, config_path)
    return config

def validate_config_file(config_path: str) -> bool:
    """
    Validate configuration file without loading it.

    Args:
        config_path: Path to configuration file

    Returns:
        True if valid, False otherwise
    """
    try:
        load_config(config_path)
        return True
    except Exception as e:
        logger.error("Configuration validation failed", config_path=config_path, error=str(e))
        return False
