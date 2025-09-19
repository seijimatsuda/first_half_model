"""Configuration management for the First-Half Over scanner."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import toml
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ProviderConfig(BaseModel):
    """Configuration for data and odds providers."""
    
    priority: List[str] = Field(
        default=["api_football", "flashscore", "sportradar", "opta", "sportmonks"],
        description="Priority order for data providers"
    )
    api_football_enabled: bool = Field(default=True)
    flashscore_enabled: bool = Field(default=True)
    sportradar_enabled: bool = Field(default=False)
    opta_enabled: bool = Field(default=False)
    sportmonks_enabled: bool = Field(default=False)
    theoddsapi_enabled: bool = Field(default=True)
    betfair_enabled: bool = Field(default=False)


class PathConfig(BaseModel):
    """Configuration for file paths."""
    
    sqlite_path: str = Field(default="data/fh_scanner.db")


class ScanConfig(BaseModel):
    """Configuration for scanning parameters."""
    
    scan_horizon_days: int = Field(default=2, ge=1, le=30)
    season_scope: str = Field(default="season_to_date")
    league_allowlist: List[str] = Field(default_factory=list)


class ThresholdConfig(BaseModel):
    """Configuration for value detection thresholds."""
    
    lambda_threshold: float = Field(default=1.5, gt=0)
    min_samples_home: int = Field(default=8, ge=1)
    min_samples_away: int = Field(default=8, ge=1)
    min_edge_pct: float = Field(default=3.0, ge=0)
    max_prob_ci_width: float = Field(default=0.20, gt=0, le=1)


class StakingConfig(BaseModel):
    """Configuration for staking strategies."""
    
    mode: str = Field(default="dynamic")
    bankroll: float = Field(default=1000.0, gt=0)
    kelly_fraction: float = Field(default=0.5, ge=0, le=1)
    tau_conf: float = Field(default=0.20, gt=0, le=1)
    target_edge_pct: float = Field(default=5.0, ge=0)
    stake_cap: float = Field(default=0.03, ge=0, le=1)
    flat_size: float = Field(default=10.0, gt=0)
    
    @validator("mode")
    def validate_mode(cls, v: str) -> str:
        if v not in ["dynamic", "flat"]:
            raise ValueError("staking.mode must be 'dynamic' or 'flat'")
        return v


class Config(BaseModel):
    """Main configuration class."""
    
    providers: ProviderConfig = Field(default_factory=ProviderConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    staking: StakingConfig = Field(default_factory=StakingConfig)
    
    # API Keys (loaded from environment)
    sportradar_api_key: Optional[str] = Field(default=None)
    opta_auth: Optional[str] = Field(default=None)
    sportmonks_key: Optional[str] = Field(default=None)
    apifootball_key: Optional[str] = Field(default=None)
    theoddsapi_key: Optional[str] = Field(default=None)
    betfair_app_key: Optional[str] = Field(default=None)
    betfair_cert: Optional[str] = Field(default=None)
    betfair_key: Optional[str] = Field(default=None)
    database_url: Optional[str] = Field(default=None)
    
    def __init__(self, **data: Any) -> None:
        # Load from environment variables first
        env_data = {
            "sportradar_api_key": os.getenv("SPORTRADAR_API_KEY"),
            "opta_auth": os.getenv("OPTA_AUTH"),
            "sportmonks_key": os.getenv("SPORTMONKS_KEY"),
            "apifootball_key": os.getenv("APIFOOTBALL_KEY"),
            "theoddsapi_key": os.getenv("THEODDSAPI_KEY"),
            "betfair_app_key": os.getenv("BETFAIR_APP_KEY"),
            "betfair_cert": os.getenv("BETFAIR_CERT"),
            "betfair_key": os.getenv("BETFAIR_KEY"),
            "database_url": os.getenv("DATABASE_URL"),
        }
        
        # Override with provided data
        env_data.update(data)
        super().__init__(**env_data)
    
    @classmethod
    def from_file(cls, config_path: str = "config.toml") -> "Config":
        """Load configuration from TOML file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            # Return default config if file doesn't exist
            return cls()
        
        with open(config_file, "r") as f:
            config_data = toml.load(f)
        
        return cls(**config_data)
    
    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled data providers in priority order."""
        enabled = []
        for provider in self.providers.priority:
            if getattr(self.providers, f"{provider}_enabled", False):
                enabled.append(provider)
        return enabled
    
    def get_provider_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        key_mapping = {
            "api_football": "apifootball_key",
            "sportradar": "sportradar_api_key",
            "opta": "opta_auth",
            "sportmonks": "sportmonks_key",
            "theoddsapi": "theoddsapi_key",
            "betfair": "betfair_app_key"
        }
        
        key_attr = key_mapping.get(provider)
        if key_attr:
            return getattr(self, key_attr)
        return None
    
    def get_enabled_odds_providers(self) -> List[str]:
        """Get list of enabled odds providers."""
        enabled = []
        if self.providers.theoddsapi_enabled and self.theoddsapi_key:
            enabled.append("theoddsapi")
        if self.providers.betfair_enabled and self.betfair_app_key:
            enabled.append("betfair")
        return enabled


# Global config instance
config = Config.from_file()
