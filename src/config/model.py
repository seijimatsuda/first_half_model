from pydantic import BaseModel
from typing import Optional, List

class ProviderFlags(BaseModel):
    sportradar_enabled: bool = False
    opta_enabled: bool = False
    sportmonks_enabled: bool = False
    api_football_enabled: bool = True
    theoddsapi_enabled: bool = True
    betfair_enabled: bool = False

class ProviderKeys(BaseModel):
    sportradar_api_key: Optional[str] = None
    opta_api_key: Optional[str] = None
    sportmonks_api_key: Optional[str] = None
    api_football_key: Optional[str] = None
    theoddsapi_key: Optional[str] = None
    betfair_app_key: Optional[str] = None
    betfair_cert_path: Optional[str] = None

class ScannerSettings(BaseModel):
    leagues_allowlist: List[int] = []
    min_kickoff_utc: Optional[str] = None
    max_kickoff_utc: Optional[str] = None
    poll_seconds: int = 30
    odds_refresh_seconds: int = 120
    max_backfill_days: int = 14
    timezone: str = "UTC"

class AppConfig(BaseModel):
    providers: ProviderFlags
    keys: ProviderKeys
    scanner: ScannerSettings
    db_url: str
    env: str = "prod"
