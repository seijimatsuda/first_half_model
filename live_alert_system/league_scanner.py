"""League discovery module for the live betting alert system."""

import asyncio
import httpx
from typing import List, Dict, Optional
from config import API_KEY, BASE_URL, REQUEST_DELAY


class LeagueScanner:
    """Handles discovery of all available leagues from API-Football."""
    
    def __init__(self):
        self.headers = {
            'x-apisports-key': API_KEY,
            'Accept': 'application/json'
        }
    
    async def get_all_leagues(self) -> List[Dict]:
        """Get all available leagues from API-Football."""
        print("🔍 Discovering all available leagues...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{BASE_URL}/leagues",
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()
                
                leagues = []
                for league_data in data.get("response", []):
                    league = league_data["league"]
                    country = league_data["country"]
                    seasons = league_data["seasons"]
                    
                    # Get current season (most recent)
                    current_season = max([s["year"] for s in seasons]) if seasons else None
                    
                    leagues.append({
                        "id": league["id"],
                        "name": league["name"],
                        "country": country["name"],
                        "type": league["type"],
                        "current_season": current_season,
                        "available_seasons": [s["year"] for s in seasons]
                    })
                
                print(f"✅ Found {len(leagues)} leagues worldwide")
                return leagues
                
            except Exception as e:
                print(f"❌ Error fetching leagues: {e}")
                return []
    
    async def get_upcoming_matches(self, league_ids: List[int]) -> List[Dict]:
        """Get all upcoming matches for the specified leagues."""
        print(f"🏈 Scanning {len(league_ids)} leagues for upcoming matches...")
        
        matches = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for league_id in league_ids:
                try:
                    # Get current season for this league
                    league_season = await self._get_current_season(league_id, client)
                    if not league_season:
                        continue
                    
                    response = await client.get(
                        f"{BASE_URL}/fixtures",
                        headers=self.headers,
                        params={
                            "league": league_id,
                            "season": league_season,
                            "next": 50  # Get next 50 fixtures
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for fixture_data in data.get("response", []):
                        fixture = fixture_data["fixture"]
                        teams = fixture_data["teams"]
                        league_info = fixture_data.get("league", {})
                        
                        # Only include upcoming matches (not started)
                        if fixture["status"]["short"] == "NS":
                            matches.append({
                                "fixture_id": fixture["id"],
                                "league_id": league_id,
                                "league_name": league_info.get("name", "Unknown"),
                                "country": league_info.get("country", "Unknown"),
                                "home_team_id": teams["home"]["id"],
                                "home_team_name": teams["home"]["name"],
                                "away_team_id": teams["away"]["id"],
                                "away_team_name": teams["away"]["name"],
                                "match_date": fixture["date"],
                                "season": league_season
                            })
                    
                    # Rate limiting
                    await asyncio.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    print(f"⚠️ Error fetching matches for league {league_id}: {e}")
                    continue
        
        print(f"✅ Found {len(matches)} upcoming matches")
        return matches
    
    async def _get_current_season(self, league_id: int, client: httpx.AsyncClient) -> Optional[int]:
        """Get the current season for a specific league."""
        try:
            response = await client.get(
                f"{BASE_URL}/leagues",
                headers=self.headers,
                params={"id": league_id}
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("response"):
                seasons = data["response"][0]["seasons"]
                return max([s["year"] for s in seasons]) if seasons else None
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error getting season for league {league_id}: {e}")
            return None
