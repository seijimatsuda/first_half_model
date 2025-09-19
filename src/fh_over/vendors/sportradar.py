"""Sportradar data provider adapter."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import DataProviderAdapter, LeagueInfo, TeamInfo, FixtureInfo, FirstHalfSample


class SportradarAdapter(DataProviderAdapter):
    """Sportradar API adapter for soccer data."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.sportradar.com/soccer/v4")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make authenticated request to Sportradar API."""
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def list_leagues(self) -> List[LeagueInfo]:
        """List all available leagues from Sportradar."""
        try:
            data = await self._make_request("competitions")
            leagues = []
            
            for competition in data.get("competitions", []):
                leagues.append(LeagueInfo(
                    provider_id=competition["id"],
                    provider_name=self.provider_name,
                    name=competition["name"],
                    country=competition.get("country", {}).get("name"),
                    season=competition.get("season", {}).get("name")
                ))
            
            return leagues
        except Exception as e:
            print(f"Error fetching leagues from Sportradar: {e}")
            return []
    
    async def list_fixtures(
        self,
        date_range: Optional[tuple[datetime, datetime]] = None,
        season: Optional[str] = None,
        league_ids: Optional[List[str]] = None
    ) -> List[FixtureInfo]:
        """List fixtures from Sportradar."""
        fixtures = []
        
        try:
            # If no specific leagues provided, get all available leagues
            if not league_ids:
                leagues = await self.list_leagues()
                league_ids = [league.provider_id for league in leagues]
            
            # Get fixtures for each league
            for league_id in league_ids:
                try:
                    # Get fixtures for the league
                    data = await self._make_request(f"competitions/{league_id}/schedules")
                    
                    for match in data.get("schedules", []):
                        # Parse match date
                        match_date = datetime.fromisoformat(
                            match["scheduled"].replace("Z", "+00:00")
                        )
                        
                        # Check date range filter
                        if date_range:
                            start_date, end_date = date_range
                            if not (start_date <= match_date <= end_date):
                                continue
                        
                        # Extract team information
                        home_team = match["home"]
                        away_team = match["away"]
                        
                        # Get first-half scores if available
                        home_first_half_score = None
                        away_first_half_score = None
                        
                        if match.get("status") == "closed" and "period_scores" in match:
                            periods = match["period_scores"]
                            if len(periods) >= 1:  # First half
                                home_first_half_score = periods[0].get("home_score")
                                away_first_half_score = periods[0].get("away_score")
                        
                        fixtures.append(FixtureInfo(
                            provider_id=match["id"],
                            provider_name=self.provider_name,
                            home_team_id=home_team["id"],
                            away_team_id=away_team["id"],
                            league_id=league_id,
                            league_name=match.get("competition", {}).get("name", ""),
                            match_date=match_date,
                            season=season,
                            status=match.get("status", "scheduled"),
                            home_score=match.get("home", {}).get("score"),
                            away_score=match.get("away", {}).get("score"),
                            home_first_half_score=home_first_half_score,
                            away_first_half_score=away_first_half_score
                        ))
                
                except Exception as e:
                    print(f"Error fetching fixtures for league {league_id}: {e}")
                    continue
            
            return fixtures
            
        except Exception as e:
            print(f"Error listing fixtures from Sportradar: {e}")
            return []
    
    async def get_team_first_half_samples(
        self,
        team_id: str,
        scope: str = "home",
        season: Optional[str] = None,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> List[FirstHalfSample]:
        """Get first-half goal samples for a team from Sportradar."""
        samples = []
        
        try:
            # Get team's match history
            data = await self._make_request(f"teams/{team_id}/results")
            
            for match in data.get("results", []):
                # Parse match date
                match_date = datetime.fromisoformat(
                    match["scheduled"].replace("Z", "+00:00")
                )
                
                # Check date range filter
                if date_range:
                    start_date, end_date = date_range
                    if not (start_date <= match_date <= end_date):
                        continue
                
                # Only process completed matches
                if match.get("status") != "closed":
                    continue
                
                # Determine if this is a home or away match for the team
                is_home = match["home"]["id"] == team_id
                is_away = match["away"]["id"] == team_id
                
                # Check scope filter
                if scope == "home" and not is_home:
                    continue
                if scope == "away" and not is_away:
                    continue
                
                # Get first-half scores
                home_first_half_score = 0
                away_first_half_score = 0
                
                if "period_scores" in match and len(match["period_scores"]) >= 1:
                    first_half = match["period_scores"][0]
                    home_first_half_score = first_half.get("home_score", 0)
                    away_first_half_score = first_half.get("away_score", 0)
                
                # Calculate total first-half goals
                total_first_half_goals = home_first_half_score + away_first_half_score
                
                samples.append(FirstHalfSample(
                    team_id=team_id,
                    fixture_id=match["id"],
                    scope=scope,
                    first_half_goals=total_first_half_goals,
                    match_date=match_date,
                    season=season or "current"
                ))
            
            return samples
            
        except Exception as e:
            print(f"Error fetching first-half samples for team {team_id}: {e}")
            return []
    
    async def get_fixture_details(self, fixture_id: str) -> Optional[FixtureInfo]:
        """Get detailed fixture information from Sportradar."""
        try:
            data = await self._make_request(f"schedules/{fixture_id}")
            
            match = data.get("schedules", [{}])[0]
            if not match:
                return None
            
            # Parse match date
            match_date = datetime.fromisoformat(
                match["scheduled"].replace("Z", "+00:00")
            )
            
            # Extract team information
            home_team = match["home"]
            away_team = match["away"]
            
            # Get first-half scores if available
            home_first_half_score = None
            away_first_half_score = None
            
            if match.get("status") == "closed" and "period_scores" in match:
                periods = match["period_scores"]
                if len(periods) >= 1:  # First half
                    home_first_half_score = periods[0].get("home_score")
                    away_first_half_score = periods[0].get("away_score")
            
            return FixtureInfo(
                provider_id=match["id"],
                provider_name=self.provider_name,
                home_team_id=home_team["id"],
                away_team_id=away_team["id"],
                league_id=match.get("competition", {}).get("id", ""),
                league_name=match.get("competition", {}).get("name", ""),
                match_date=match_date,
                season=match.get("season", {}).get("name"),
                status=match.get("status", "scheduled"),
                home_score=match.get("home", {}).get("score"),
                away_score=match.get("away", {}).get("score"),
                home_first_half_score=home_first_half_score,
                away_first_half_score=away_first_half_score
            )
            
        except Exception as e:
            print(f"Error fetching fixture details for {fixture_id}: {e}")
            return None
