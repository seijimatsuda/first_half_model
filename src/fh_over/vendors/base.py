"""Base classes for data provider adapters."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LeagueInfo:
    """League information from data providers."""
    provider_id: str
    provider_name: str
    name: str
    country: Optional[str] = None
    season: Optional[str] = None


@dataclass
class TeamInfo:
    """Team information from data providers."""
    provider_id: str
    provider_name: str
    name: str
    country: Optional[str] = None
    league_id: Optional[str] = None


@dataclass
class FixtureInfo:
    """Fixture information from data providers."""
    provider_id: str
    provider_name: str
    home_team_id: str
    away_team_id: str
    league_id: str
    league_name: str
    match_date: datetime
    season: Optional[str] = None
    status: str = "scheduled"
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    home_first_half_score: Optional[int] = None
    away_first_half_score: Optional[int] = None


@dataclass
class FirstHalfSample:
    """First-half goal sample from a match."""
    team_id: str
    fixture_id: str
    scope: str  # "home" or "away"
    first_half_goals: int  # Total first-half goals (home + away)
    match_date: datetime
    season: str


class DataProviderAdapter(ABC):
    """Base class for data provider adapters."""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.provider_name = self.__class__.__name__.replace("Adapter", "").lower()
    
    @abstractmethod
    async def list_leagues(self) -> List[LeagueInfo]:
        """List all available leagues."""
        pass
    
    @abstractmethod
    async def list_fixtures(
        self,
        date_range: Optional[tuple[datetime, datetime]] = None,
        season: Optional[str] = None,
        league_ids: Optional[List[str]] = None
    ) -> List[FixtureInfo]:
        """List fixtures for given criteria."""
        pass
    
    @abstractmethod
    async def get_team_first_half_samples(
        self,
        team_id: str,
        scope: str = "home",
        season: Optional[str] = None,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> List[FirstHalfSample]:
        """Get first-half goal samples for a team."""
        pass
    
    @abstractmethod
    async def get_fixture_details(self, fixture_id: str) -> Optional[FixtureInfo]:
        """Get detailed fixture information."""
        pass


class OddsProviderAdapter(ABC):
    """Base class for odds provider adapters."""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.provider_name = self.__class__.__name__.replace("Adapter", "").lower()
    
    @abstractmethod
    async def get_first_half_over_odds(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        """Get first-half over 0.5 odds for a fixture."""
        pass
    
    @abstractmethod
    async def get_available_markets(self, fixture_id: str) -> List[Dict[str, Any]]:
        """Get available markets for a fixture."""
        pass
