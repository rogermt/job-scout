"""Configuration management for Job Scout using Pydantic Settings.

This module provides centralized configuration management with validation,
type safety, and environment variable support following ForgeSyte standards.
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class SalaryPreferences(BaseModel):
    """Salary and compensation preferences."""

    min_gbp: int = Field(default=30000, description="Minimum salary in GBP")
    max_gbp: Optional[int] = Field(default=None, description="Maximum salary in GBP")
    currency_preference: str = Field(
        default="GBP", description="Preferred currency for display"
    )


class JobPreferences(BaseModel):
    """Job search preferences and filters."""

    titles: list[str] = Field(default_factory=list, description="Desired job titles")
    keywords: list[str] = Field(
        default_factory=list, description="Required keywords in job description"
    )
    experience_level: str = Field(
        default="mid",
        description="Experience level: junior, mid, senior, lead, principal",
    )
    remote_only: bool = Field(default=True, description="Only remote positions")
    locations: list[str] = Field(
        default_factory=lambda: ["UK Remote", "Europe Remote", "Worldwide Remote"],
        description="Acceptable location/remote policies",
    )
    exclude_keywords: list[str] = Field(
        default_factory=lambda: ["recruiter", "commission", "sales"],
        description="Keywords to exclude from jobs",
    )
    company_size: list[str] = Field(
        default_factory=lambda: ["10-50", "50-200", "200+"],
        description="Preferred company sizes",
    )
    contract_types: list[str] = Field(
        default_factory=lambda: ["permanent", "contract"],
        description="UK contract types: permanent, contract, freelance",
    )
    salary: SalaryPreferences = Field(default_factory=SalaryPreferences)


class PlatformConfig(BaseModel):

    # Extended fields for testing
    keywords: str = ""
    location: str = ""
    max_results: int = 50
    api_key: str | None = None
    endpoint: str | None = None
    extra_config: dict = {}
    """Individual platform configuration."""

    enabled: bool = Field(default=True, description="Whether this platform is enabled")
    region: str = Field(default="uk", description="Region filter for the platform")


class AIConfig(BaseModel):
    """AI/ML API configuration."""

    provider: str = Field(
        default="openai", description="AI provider: openai or anthropic"
    )
    api_key: Optional[str] = Field(default=None, description="API key for AI service")
    model: str = Field(default="gpt-4", description="Model to use")
    cv_tailoring: bool = Field(default=True, description="Enable CV tailoring")
    cover_letter_generation: bool = Field(
        default=True, description="Enable cover letter generation"
    )
    max_retries: int = Field(default=3, description="Max retries for API calls")
    timeout_seconds: int = Field(default=60, description="API timeout in seconds")


class DatabaseConfig(BaseModel):
    """Database configuration."""

    path: Path = Field(
        default=Path("output/job_scout.db"), description="Path to SQLite database file"
    )
    echo: bool = Field(default=False, description="Enable SQL echo for debugging")


class OutputConfig(BaseModel):
    """Output directory configuration."""

    applications_dir: Path = Field(
        default=Path("output/applications"),
        description="Directory for application packages",
    )
    tailored_cv_dir: Path = Field(
        default=Path("output/tailored_cvs"), description="Directory for tailored CVs"
    )
    cover_letter_dir: Path = Field(
        default=Path("output/cover_letters"), description="Directory for cover letters"
    )
    analytics_dir: Path = Field(
        default=Path("output/analytics"), description="Directory for analytics reports"
    )
    log_file: Path = Field(
        default=Path("logs/job_scout.log"), description="Path to log file"
    )


class SchedulingConfig(BaseModel):
    """Scheduling configuration for automated searches."""

    search_frequency_hours: int = Field(
        default=6, description="How often to run job searches (hours)"
    )
    enabled: bool = Field(default=False, description="Enable scheduled searches")


class PersonalDetails(BaseModel):
    """Personal details for applications."""

    name: str = Field(default="", description="Full name")
    email: EmailStr = Field(default="example@email.com", description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: str = Field(default="", description="Current location")
    right_to_work: str = Field(
        default="",
        description="UK right to work status (UK Citizen, Visa details, etc.)",
    )
    linkedin_profile: Optional[HttpUrl] = Field(
        default=None, description="LinkedIn profile URL"
    )
    github_profile: Optional[HttpUrl] = Field(
        default=None, description="GitHub profile URL"
    )
    website: Optional[HttpUrl] = Field(
        default=None, description="Personal website/portfolio"
    )


class Settings(BaseSettings):
    """Main application settings loaded from environment and config files.

    Configuration priority (highest to lowest):
    1. Environment variables (JOB_SCOUT_*)
    2. .env file
    3. config/config.yaml
    4. config/.env file
    """

    model_config = SettingsConfigDict(
        env_prefix="JOB_SCOUT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Core application settings
    personal: PersonalDetails = Field(default_factory=PersonalDetails)
    job_preferences: JobPreferences = Field(default_factory=JobPreferences)
    ai: AIConfig = Field(default_factory=AIConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    scheduling: SchedulingConfig = Field(default_factory=SchedulingConfig)

    # Platform-specific settings
    platforms: dict[str, PlatformConfig] = Field(
        default_factory=lambda: {
            "indeed": PlatformConfig(enabled=True, region="uk"),
            "reed": PlatformConfig(enabled=True),
            "totaljobs": PlatformConfig(enabled=True),
            "cvlibrary": PlatformConfig(enabled=True),
            "stackoverflow": PlatformConfig(enabled=True),
            "weworkremotely": PlatformConfig(enabled=True),
            "remoteok": PlatformConfig(enabled=True),
            "workingnomads": PlatformConfig(enabled=True),
        }
    )

    # Application behavior
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    max_concurrent_requests: int = Field(
        default=5, description="Max concurrent HTTP requests"
    )

    def get_platform_config(self, platform_name: str) -> PlatformConfig:
        """Get configuration for a specific platform.

        Args:
            platform_name: Name of the platform (e.g., 'indeed', 'reed')

        Returns:
            PlatformConfig for the specified platform

        Raises:
            KeyError: If platform is not configured
        """
        if platform_name not in self.platforms:
            raise KeyError(f"Platform '{platform_name}' not configured")
        return self.platforms[platform_name]

    def is_platform_enabled(self, platform_name: str) -> bool:
        """Check if a platform is enabled.

        Args:
            platform_name: Name of the platform

        Returns:
            True if platform is enabled and configured
        """
        try:
            return self.get_platform_config(platform_name).enabled
        except KeyError:
            return False

    def get_enabled_platforms(self) -> dict[str, PlatformConfig]:
        """Get all enabled platforms.

        Returns:
            Dictionary of enabled platforms with their configurations
        """
        return {
            name: config for name, config in self.platforms.items() if config.enabled
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance.

    Lazily loads settings on first call.

    Returns:
        The global Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from configuration files.

    Useful when configuration files have been modified.

    Returns:
        The reloaded Settings instance
    """
    global _settings
    _settings = Settings()
    return _settings


__all__ = [
    "Settings",
    "PersonalDetails",
    "JobPreferences",
    "SalaryPreferences",
    "PlatformConfig",
    "AIConfig",
    "DatabaseConfig",
    "OutputConfig",
    "SchedulingConfig",
    "get_settings",
    "reload_settings",
]
