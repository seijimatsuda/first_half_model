"""Match discovery module for finding matches in the next 24 hours."""

import asyncio
import httpx
import pytz
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import API_KEY, BASE_URL, REQUEST_DELAY


class MatchDiscovery:
    """Handles discovery of matches happening in the next 24 hours."""
    
    def __init__(self, rapidapi_key: str = None):
        self.rapidapi_key = rapidapi_key
        self.headers = {
            'x-rapidapi-key': rapidapi_key if rapidapi_key else API_KEY,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        self.discovered_matches = []
    
    async def discover_matches_next_24h(self) -> List[Dict]:
        """Discover all matches happening in the next 24 hours (Pacific time)."""
        
        print("🔍 Discovering matches in next 24 hours (Pacific time)...")
        
        # Use Pacific timezone
        pacific_tz = pytz.timezone('US/Pacific')
        now_pacific = datetime.now(pacific_tz)
        next_24h_pacific = now_pacific + timedelta(hours=24)
        
        # Convert to UTC for API calls (API-Football expects UTC)
        now_utc = now_pacific.astimezone(pytz.UTC)
        next_24h_utc = next_24h_pacific.astimezone(pytz.UTC)
        
        # Format dates for API (UTC)
        from_date = now_utc.strftime("%Y-%m-%d")
        to_date = next_24h_utc.strftime("%Y-%m-%d")
        
        print(f"🕐 Pacific time range: {now_pacific.strftime('%Y-%m-%d %H:%M:%S')} to {next_24h_pacific.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌍 UTC time range: {now_utc.strftime('%Y-%m-%d %H:%M:%S')} to {next_24h_utc.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                all_fixtures = []
                
                # Get fixtures for today and tomorrow to ensure we catch all matches
                for date_str in [from_date, to_date]:
                    response = await client.get(
                        f"{BASE_URL}/fixtures",
                        headers=self.headers,
                        params={
                            "date": date_str,
                            "timezone": "UTC"
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        fixtures = data.get("response", [])
                        all_fixtures.extend(fixtures)
                        print(f"📅 Found {len(fixtures)} fixtures for {date_str}")
                    else:
                        print(f"⚠️ API Error for {date_str}: {response.status_code}")
                
                fixtures = all_fixtures
                
                # Filter for matches in next 24 hours (Pacific time window)
                next_24h_matches = []
                for fixture in fixtures:
                    match_date_str = fixture["fixture"]["date"]
                    match_date_utc = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                    
                    # Filter matches within our Pacific time window (converted to UTC for comparison)
                    if now_utc <= match_date_utc <= next_24h_utc:
                        # Convert match time to Pacific for display
                        match_date_pacific = match_date_utc.astimezone(pacific_tz)
                        match_date_display = match_date_pacific.strftime('%Y-%m-%dT%H:%M:%S%z')
                        
                        match_data = {
                            "fixture_id": fixture["fixture"]["id"],
                            "home_team_id": fixture["teams"]["home"]["id"],
                            "away_team_id": fixture["teams"]["away"]["id"],
                            "home_team_name": fixture["teams"]["home"]["name"],
                            "away_team_name": fixture["teams"]["away"]["name"],
                            "match_date": match_date_display,  # Now in Pacific time
                            "match_date_utc": match_date_str,  # Keep UTC for API calls
                            "league_id": fixture["league"]["id"],
                            "league_name": fixture["league"]["name"],
                            "country": fixture["league"]["country"],
                            "season": fixture["league"]["season"]
                        }
                        next_24h_matches.append(match_data)
                
                print(f"✅ Found {len(next_24h_matches)} matches in next 24 hours")
                self.discovered_matches = next_24h_matches
                return next_24h_matches
                    
        except Exception as e:
            print(f"❌ Error discovering matches: {e}")
            return []
    
    async def discover_matches_from_rapidapi(self, rapidapi_endpoint: str) -> List[Dict]:
        """Discover matches using a RapidAPI sports endpoint."""
        
        print("🔍 Discovering matches via RapidAPI...")
        
        # This is a placeholder for when you get a RapidAPI key
        # You'll need to replace this with the actual RapidAPI endpoint
        
        headers = {
            'x-rapidapi-key': self.rapidapi_key,
            'x-rapidapi-host': 'your-rapidapi-host'  # Replace with actual host
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # This would be the actual RapidAPI call
                # response = await client.get(rapidapi_endpoint, headers=headers)
                
                # For now, return empty list
                print("⚠️ RapidAPI integration not yet configured")
                return []
                
        except Exception as e:
            print(f"❌ Error with RapidAPI: {e}")
            return []
    
    async def discover_matches_from_flashscore_scraping(self) -> List[Dict]:
        """Discover matches by scraping FlashScore (alternative method)."""
        
        print("🔍 Discovering matches via FlashScore scraping...")
        
        # This would implement web scraping of FlashScore
        # For now, return empty list
        
        print("⚠️ FlashScore scraping not yet implemented")
        return []
    
    def get_match_summary(self) -> Dict:
        """Get a summary of discovered matches."""
        
        if not self.discovered_matches:
            return {"total_matches": 0, "countries": [], "leagues": []}
        
        countries = list(set([match["country"] for match in self.discovered_matches]))
        leagues = list(set([match["league_name"] for match in self.discovered_matches]))
        
        return {
            "total_matches": len(self.discovered_matches),
            "countries": countries,
            "leagues": leagues,
            "matches": self.discovered_matches
        }


# Example usage
async def main():
    """Example of how to use the MatchDiscovery class."""
    
    # Initialize with your current API key
    discovery = MatchDiscovery()
    
    # Discover matches using current API-Football
    matches = await discovery.discover_matches_next_24h()
    
    if matches:
        summary = discovery.get_match_summary()
        print(f"\n📊 DISCOVERY SUMMARY:")
        print(f"Total matches: {summary['total_matches']}")
        print(f"Countries: {', '.join(summary['countries'])}")
        print(f"Leagues: {len(summary['leagues'])} different leagues")
        
        # Show first few matches
        print(f"\n🏈 SAMPLE MATCHES:")
        for i, match in enumerate(matches[:5], 1):
            match_time = match['match_date'][:19].replace('T', ' ')
            print(f"{i}. {match['home_team_name']} vs {match['away_team_name']}")
            print(f"   {match['league_name']} - {match_time} UTC")
    else:
        print("❌ No matches found")


if __name__ == "__main__":
    asyncio.run(main())
