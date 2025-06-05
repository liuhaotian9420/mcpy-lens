"""Configuration management for mcpy-lens."""

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings configuration."""

    # ——— Application settings ———
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # ——— Directory paths ———
    data_dir: Path = Field(
        default_factory=lambda: Path("data"),
        description="Base directory for application data",
    )

    @property
    def uploaded_scripts_dir(self) -> Path:
        """Directory for uploaded Python scripts."""
        return self.data_dir / "uploaded_scripts"

    @property
    def wrappers_dir(self) -> Path:
        """Directory for generated wrapper scripts."""
        return self.data_dir / "wrappers"

    @property
    def metadata_dir(self) -> Path:
        """Directory for tool metadata and schemas."""
        return self.data_dir / "metadata"

    @property
    def services_dir(self) -> Path:
        """Directory for service configuration files."""
        return self.data_dir / "services"

    @property
    def logs_dir(self) -> Path:
        """Directory for application logs."""
        return self.data_dir / "logs"

    def create_directories(self) -> None:
        """Create all necessary directories if they don't exist."""
        directories = [
            self.data_dir,
            self.uploaded_scripts_dir,
            self.wrappers_dir,
            self.metadata_dir,
            self.services_dir,
            self.logs_dir,
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"Ensured directory exists: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                raise

    def validate_directories(self) -> bool:
        """Validate that all required directories exist and are writable."""
        directories = [
            self.data_dir,
            self.uploaded_scripts_dir,
            self.wrappers_dir,
            self.metadata_dir,
            self.services_dir,
            self.logs_dir,
        ]

        for directory in directories:
            if not directory.exists():
                logger.error(f"Required directory does not exist: {directory}")
                return False
            if not directory.is_dir():
                logger.error(f"Path is not a directory: {directory}")
                return False
            # Test write permissions by creating a temporary file
            test_file = directory / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                logger.error(f"Directory is not writable: {directory} - {e}")
                return False

        logger.info("All directories validated successfully")
        return True

    # ——— Service settings ———
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum file upload size in bytes",
    )

    allowed_extensions: list[str] = Field(
        default=[".py"], description="Allowed file extensions for upload"
    )

    # ——— Server settings ———
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8090, description="Server port")
    reload: bool = Field(default=True, description="Enable auto-reload in development")

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_prefix = "MCPY_LENS_"


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
