"""Team performance analysis module for the live betting alert system."""

import asyncio
import httpx
from typing import Optional, Dict
from config import API_KEY, BASE_URL, REQUEST_DELAY, MIN_MATCHES_REQUIRED


class TeamAnalyzer:
    """Handles team performance analysis and average calculations."""
    
    def __init__(self):
        self.headers = {
            'x-apisports-key': API_KEY,
            'Accept': 'application/json'
        }
        self.team_cache = {}  # Cache team averages to avoid redundant API calls
    
    async def calculate_team_averages(self, team_id: int, season: int, home_away: str) -> Optional[float]:
        """Calculate team's average first-half goals for home or away matches.
        
        The system requires 4+ total matches played (not 4+ home/away matches).
        This allows analysis even when home/away distribution is uneven early in season.
        """
        
        # Check cache first
        cache_key = f"{team_id}_{season}_{home_away}"
        if cache_key in self.team_cache:
            return self.team_cache[cache_key]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{BASE_URL}/fixtures",
                    headers=self.headers,
                    params={
                        "team": team_id,
                        "season": season,
                        "last": 50  # Get last 50 fixtures
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # First, get ALL finished matches to check total count
                all_finished_matches = []
                for fixture_data in data.get("response", []):
                    fixture = fixture_data["fixture"]
                    if fixture["status"]["short"] == "FT":
                        all_finished_matches.append(fixture_data)
                
                # Check if team has played enough total matches (4+)
                if len(all_finished_matches) < MIN_MATCHES_REQUIRED:
                    self.team_cache[cache_key] = None
                    return None
                
                # Now filter for home/away matches and calculate averages
                first_half_goals = []
                
                for fixture_data in all_finished_matches:
                    teams = fixture_data["teams"]
                    score = fixture_data.get("score", {})
                    
                    # Determine if this is a home or away match for the team
                    is_home = teams["home"]["id"] == team_id
                    is_away = teams["away"]["id"] == team_id
                    
                    # Check if this matches the requested context (home/away)
                    if home_away == "home" and not is_home:
                        continue
                    if home_away == "away" and not is_away:
                        continue
                    
                    # Get first-half scores
                    halftime_score = score.get("halftime", {})
                    home_ht = halftime_score.get("home", 0)
                    away_ht = halftime_score.get("away", 0)
                    
                    # Calculate total first-half goals for this match
                    total_ht_goals = home_ht + away_ht
                    first_half_goals.append(total_ht_goals)
                
                # Calculate average (now that we've confirmed total matches >= MIN_MATCHES_REQUIRED)
                if len(first_half_goals) > 0:
                    average = sum(first_half_goals) / len(first_half_goals)
                    self.team_cache[cache_key] = average
                    return average
                else:
                    self.team_cache[cache_key] = None
                    return None
                    
        except Exception as e:
            print(f"⚠️ Error calculating averages for team {team_id}: {e}")
            return None
    
    async def analyze_match(self, match: Dict) -> Optional[Dict]:
        """Analyze a single match and return betting recommendation."""
        try:
            # Get team averages
            home_avg = await self.calculate_team_averages(
                match["home_team_id"], 
                match["season"], 
                "home"
            )
            
            away_avg = await self.calculate_team_averages(
                match["away_team_id"], 
                match["season"], 
                "away"
            )
            
            # Skip if either team doesn't have enough data
            if home_avg is None or away_avg is None:
                return None
            
            # Calculate combined average
            combined_avg = (home_avg + away_avg) / 2
            
            return {
                "fixture_id": match["fixture_id"],
                "league_name": match["league_name"],
                "country": match["country"],
                "home_team_name": match["home_team_name"],
                "away_team_name": match["away_team_name"],
                "match_date": match["match_date"],
                "home_avg": home_avg,
                "away_avg": away_avg,
                "combined_avg": combined_avg,
                "should_alert": combined_avg >= 1.5
            }
            
        except Exception as e:
            print(f"⚠️ Error analyzing match {match.get('fixture_id', 'unknown')}: {e}")
            return None
