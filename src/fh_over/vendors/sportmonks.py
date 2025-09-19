"""SportMonks data provider adapter."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import DataProviderAdapter, LeagueInfo, TeamInfo, FixtureInfo, FirstHalfSample


class SportMonksAdapter(DataProviderAdapter):
    """SportMonks API adapter for soccer data."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.sportmonks.com/v3/football")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make authenticated request to SportMonks API."""
        if params is None:
            params = {}
        params["api_token"] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def list_leagues(self) -> List[LeagueInfo]:
        """List all available leagues from SportMonks."""
        try:
            data = await self._make_request("leagues")
            leagues = []
            
            for league in data.get("data", []):
                leagues.append(LeagueInfo(
                    provider_id=str(league["id"]),
                    provider_name=self.provider_name,
                    name=league["name"],
                    country=league.get("country", {}).get("name"),
                    season=league.get("current_season", {}).get("name")
                ))
            
            return leagues
        except Exception as e:
            print(f"Error fetching leagues from SportMonks: {e}")
            return []
    
    async def list_fixtures(
        self,
        date_range: Optional[tuple[datetime, datetime]] = None,
        season: Optional[str] = None,
        league_ids: Optional[List[str]] = None
    ) -> List[FixtureInfo]:
        """List fixtures from SportMonks."""
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
                    params = {"include": "participants,league"}
                    if date_range:
                        start_date, end_date = date_range
                        params["filters"] = f"startingAt:between({start_date.isoformat()},{end_date.isoformat()})"
                    
                    data = await self._make_request(f"leagues/{league_id}/fixtures", params)
                    
                    for match in data.get("data", []):
                        # Parse match date
                        match_date = datetime.fromisoformat(
                            match["starting_at"].replace("Z", "+00:00")
                        )
                        
                        # Extract team information
                        participants = match.get("participants", [])
                        home_team = participants[0] if len(participants) > 0 else {}
                        away_team = participants[1] if len(participants) > 1 else {}
                        
                        # Get first-half scores if available
                        home_first_half_score = None
                        away_first_half_score = None
                        
                        if match.get("status") == "finished" and "scores" in match:
                            scores = match["scores"]
                            if "ht" in scores:  # Half-time scores
                                ht_scores = scores["ht"]
                                home_first_half_score = ht_scores.get("score", 0)
                                away_first_half_score = ht_scores.get("score", 0)
                        
                        fixtures.append(FixtureInfo(
                            provider_id=str(match["id"]),
                            provider_name=self.provider_name,
                            home_team_id=str(home_team.get("id", "")),
                            away_team_id=str(away_team.get("id", "")),
                            league_id=league_id,
                            league_name=match.get("league", {}).get("name", ""),
                            match_date=match_date,
                            season=season,
                            status=match.get("status", "scheduled"),
                            home_score=match.get("scores", {}).get("ft", {}).get("score"),
                            away_score=match.get("scores", {}).get("ft", {}).get("score"),
                            home_first_half_score=home_first_half_score,
                            away_first_half_score=away_first_half_score
                        ))
                
                except Exception as e:
                    print(f"Error fetching fixtures for league {league_id}: {e}")
                    continue
            
            return fixtures
            
        except Exception as e:
            print(f"Error listing fixtures from SportMonks: {e}")
            return []
    
    async def get_team_first_half_samples(
        self,
        team_id: str,
        scope: str = "home",
        season: Optional[str] = None,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> List[FirstHalfSample]:
        """Get first-half goal samples for a team from SportMonks."""
        samples = []
        
        try:
            # Get team's match history
            params = {"include": "scores,participants"}
            if date_range:
                start_date, end_date = date_range
                params["filters"] = f"startingAt:between({start_date.isoformat()},{end_date.isoformat()})"
            
            data = await self._make_request(f"teams/{team_id}/fixtures", params)
            
            for match in data.get("data", []):
                # Parse match date
                match_date = datetime.fromisoformat(
                    match["starting_at"].replace("Z", "+00:00")
                )
                
                # Only process completed matches
                if match.get("status") != "finished":
                    continue
                
                # Determine if this is a home or away match for the team
                participants = match.get("participants", [])
                if len(participants) < 2:
                    continue
                
                home_team_id = str(participants[0].get("id", ""))
                away_team_id = str(participants[1].get("id", ""))
                
                is_home = home_team_id == team_id
                is_away = away_team_id == team_id
                
                # Check scope filter
                if scope == "home" and not is_home:
                    continue
                if scope == "away" and not is_away:
                    continue
                
                # Get first-half scores
                home_first_half_score = 0
                away_first_half_score = 0
                
                scores = match.get("scores", {})
                if "ht" in scores:  # Half-time scores
                    ht_scores = scores["ht"]
                    home_first_half_score = ht_scores.get("score", 0)
                    away_first_half_score = ht_scores.get("score", 0)
                
                # Calculate total first-half goals
                total_first_half_goals = home_first_half_score + away_first_half_score
                
                samples.append(FirstHalfSample(
                    team_id=team_id,
                    fixture_id=str(match["id"]),
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
        """Get detailed fixture information from SportMonks."""
        try:
            data = await self._make_request(f"fixtures/{fixture_id}", {"include": "participants,league,scores"})
            
            match = data.get("data")
            if not match:
                return None
            
            # Parse match date
            match_date = datetime.fromisoformat(
                match["starting_at"].replace("Z", "+00:00")
            )
            
            # Extract team information
            participants = match.get("participants", [])
            home_team = participants[0] if len(participants) > 0 else {}
            away_team = participants[1] if len(participants) > 1 else {}
            
            # Get first-half scores if available
            home_first_half_score = None
            away_first_half_score = None
            
            if match.get("status") == "finished" and "scores" in match:
                scores = match["scores"]
                if "ht" in scores:  # Half-time scores
                    ht_scores = scores["ht"]
                    home_first_half_score = ht_scores.get("score", 0)
                    away_first_half_score = ht_scores.get("score", 0)
            
            return FixtureInfo(
                provider_id=str(match["id"]),
                provider_name=self.provider_name,
                home_team_id=str(home_team.get("id", "")),
                away_team_id=str(away_team.get("id", "")),
                league_id=str(match.get("league", {}).get("id", "")),
                league_name=match.get("league", {}).get("name", ""),
                match_date=match_date,
                season=match.get("season", {}).get("name"),
                status=match.get("status", "scheduled"),
                home_score=match.get("scores", {}).get("ft", {}).get("score"),
                away_score=match.get("scores", {}).get("ft", {}).get("score"),
                home_first_half_score=home_first_half_score,
                away_first_half_score=away_first_half_score
            )
            
        except Exception as e:
            print(f"Error fetching fixture details for {fixture_id}: {e}")
            return None
