"""API-Football data provider adapter."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import DataProviderAdapter, LeagueInfo, TeamInfo, FixtureInfo, FirstHalfSample


class ApiFootballAdapter(DataProviderAdapter):
    """API-Football adapter for soccer data."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://v3.football.api-sports.io")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.client.headers.update({
            'x-apisports-key': api_key
        })
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make authenticated request to API-Football."""
        if params is None:
            params = {}
        
        url = f"{self.base_url}/{endpoint}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def list_leagues(self) -> List[LeagueInfo]:
        """List all available leagues from API-Football."""
        try:
            data = await self._make_request("leagues", {"season": 2024})
            leagues = []
            
            for league_data in data.get("response", []):
                league = league_data["league"]
                country = league_data["country"]
                
                leagues.append(LeagueInfo(
                    provider_id=str(league["id"]),
                    provider_name=self.provider_name,
                    name=league["name"],
                    country=country["name"],
                    season="2024-25"
                ))
            
            return leagues
            
        except Exception as e:
            print(f"Error fetching leagues from API-Football: {e}")
            return []
    
    async def list_fixtures(
        self,
        date_range: Optional[tuple[datetime, datetime]] = None,
        season: Optional[str] = None,
        league_ids: Optional[List[str]] = None
    ) -> List[FixtureInfo]:
        """List fixtures from API-Football."""
        fixtures = []
        
        try:
            # If no specific leagues provided, get top leagues
            if not league_ids:
                leagues = await self.list_leagues()
                league_ids = [league.provider_id for league in leagues[:10]]  # Top 10 leagues
            
            # Get fixtures for each league
            for league_id in league_ids:
                try:
                    params = {
                        "league": league_id,
                        "season": 2024,
                        "last": 50  # Get last 50 fixtures
                    }
                    
                    data = await self._make_request("fixtures", params)
                    
                    for fixture_data in data.get("response", []):
                        fixture = fixture_data["fixture"]
                        teams = fixture_data["teams"]
                        goals = fixture_data.get("goals", {})
                        score = fixture_data.get("score", {})
                        
                        # Parse match date
                        match_date = datetime.fromisoformat(
                            fixture["date"].replace("Z", "+00:00")
                        ).replace(tzinfo=None)  # Convert to naive datetime
                        
                        # Check date range filter
                        if date_range:
                            start_date, end_date = date_range
                            if not (start_date <= match_date <= end_date):
                                continue
                        
                        # Extract first-half scores
                        home_first_half_score = None
                        away_first_half_score = None
                        
                        if "halftime" in score:
                            halftime = score["halftime"]
                            home_first_half_score = halftime.get("home")
                            away_first_half_score = halftime.get("away")
                        
                        fixtures.append(FixtureInfo(
                            provider_id=str(fixture["id"]),
                            provider_name=self.provider_name,
                            home_team_id=str(teams["home"]["id"]),
                            away_team_id=str(teams["away"]["id"]),
                            league_id=league_id,
                            league_name=fixture_data.get("league", {}).get("name", ""),
                            match_date=match_date,
                            season="2024-25",
                            status=fixture["status"]["short"],
                            home_score=goals.get("home"),
                            away_score=goals.get("away"),
                            home_first_half_score=home_first_half_score,
                            away_first_half_score=away_first_half_score
                        ))
                
                except Exception as e:
                    print(f"Error fetching fixtures for league {league_id}: {e}")
                    continue
            
            return fixtures
            
        except Exception as e:
            print(f"Error listing fixtures from API-Football: {e}")
            return []
    
    async def get_team_first_half_samples(
        self,
        team_id: str,
        scope: str = "home",
        season: Optional[str] = None,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> List[FirstHalfSample]:
        """Get first-half goal samples for a team from API-Football."""
        samples = []
        
        try:
            params = {
                "team": team_id,
                "season": 2024,
                "last": 50
            }
            
            data = await self._make_request("fixtures", params)
            
            for fixture_data in data.get("response", []):
                fixture = fixture_data["fixture"]
                teams = fixture_data["teams"]
                score = fixture_data.get("score", {})
                
                # Parse match date
                match_date = datetime.fromisoformat(
                    fixture["date"].replace("Z", "+00:00")
                ).replace(tzinfo=None)  # Convert to naive datetime
                
                # Check date range filter
                if date_range:
                    start_date, end_date = date_range
                    if not (start_date <= match_date <= end_date):
                        continue
                
                # Determine if this is a home or away match for the team
                is_home = teams["home"]["id"] == int(team_id)
                is_away = teams["away"]["id"] == int(team_id)
                
                # Check scope filter
                if scope == "home" and not is_home:
                    continue
                if scope == "away" and not is_away:
                    continue
                
                # Get first-half scores
                home_first_half_score = 0
                away_first_half_score = 0
                
                if "halftime" in score:
                    halftime = score["halftime"]
                    home_first_half_score = halftime.get("home", 0)
                    away_first_half_score = halftime.get("away", 0)
                
                # Calculate total first-half goals
                total_first_half_goals = home_first_half_score + away_first_half_score
                
                samples.append(FirstHalfSample(
                    team_id=team_id,
                    fixture_id=str(fixture["id"]),
                    scope=scope,
                    first_half_goals=total_first_half_goals,
                    match_date=match_date,
                    season=season or "2024-25"
                ))
            
            return samples
            
        except Exception as e:
            print(f"Error fetching first-half samples for team {team_id}: {e}")
            return []
    
    async def get_fixture_details(self, fixture_id: str) -> Optional[FixtureInfo]:
        """Get detailed fixture information from API-Football."""
        try:
            data = await self._make_request("fixtures", {"id": fixture_id})
            
            if not data.get("response"):
                return None
            
            fixture_data = data["response"][0]
            fixture = fixture_data["fixture"]
            teams = fixture_data["teams"]
            goals = fixture_data.get("goals", {})
            score = fixture_data.get("score", {})
            
            # Parse match date
            match_date = datetime.fromisoformat(
                fixture["date"].replace("Z", "+00:00")
            ).replace(tzinfo=None)  # Convert to naive datetime
            
            # Extract first-half scores
            home_first_half_score = None
            away_first_half_score = None
            
            if "halftime" in score:
                halftime = score["halftime"]
                home_first_half_score = halftime.get("home")
                away_first_half_score = halftime.get("away")
            
            return FixtureInfo(
                provider_id=str(fixture["id"]),
                provider_name=self.provider_name,
                home_team_id=str(teams["home"]["id"]),
                away_team_id=str(teams["away"]["id"]),
                league_id=str(fixture_data.get("league", {}).get("id", "")),
                league_name=fixture_data.get("league", {}).get("name", ""),
                match_date=match_date,
                season="2023-24",
                status=fixture["status"]["short"],
                home_score=goals.get("home"),
                away_score=goals.get("away"),
                home_first_half_score=home_first_half_score,
                away_first_half_score=away_first_half_score
            )
            
        except Exception as e:
            print(f"Error fetching fixture details for {fixture_id}: {e}")
            return None