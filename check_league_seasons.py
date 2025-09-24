#!/usr/bin/env python3
"""
Check what seasons are available for any league through API-Football
"""

import asyncio
import httpx
import os
from datetime import datetime

async def check_available_seasons():
    """Check what seasons are available for any league"""
    
    api_key = os.getenv('APIFOOTBALL_KEY')
    
    if not api_key or api_key == 'your_api_football_key_here':
        print("❌ API-Football key not configured")
        print("To check available seasons, you need:")
        print("1. Get a free API key from: https://rapidapi.com/api-sports/api/api-football")
        print("2. Set it in your .env file: APIFOOTBALL_KEY=your_actual_key_here")
        return
    
    headers = {
        'x-apisports-key': api_key,
        'Accept': 'application/json'
    }
    
    print("=== CHECKING LEAGUE SEASONS ===")
    print(f"League ID: 282 (Peru Segunda División)")
    print(f"Today's date: {datetime.now().strftime('%Y-%m-%d')}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First, get league information to see available seasons
            print("1. Getting league information...")
            response = await client.get(
                "https://v3.football.api-sports.io/leagues",
                headers=headers,
                params={"id": 282}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("response"):
                    league_info = data["response"][0]["league"]
                    country_info = data["response"][0]["country"]
                    seasons_info = data["response"][0]["seasons"]
                    
                    print(f"✅ League found: {league_info['name']}")
                    print(f"Country: {country_info['name']}")
                    print(f"Type: {league_info['type']}")
                    print(f"Available seasons: {seasons_info}")
                    print()
                    
                    # Check each available season for fixtures
                    available_seasons = []
                    for season in seasons_info:
                        season_year = season["year"]
                        print(f"2. Checking season {season_year}...")
                        
                        # Get fixtures for this season
                        fixtures_response = await client.get(
                            "https://v3.football.api-sports.io/fixtures",
                            headers=headers,
                            params={
                                "league": 282,
                                "season": season_year
                            }
                        )
                        
                        if fixtures_response.status_code == 200:
                            fixtures_data = fixtures_response.json()
                            fixtures_count = len(fixtures_data.get("response", []))
                            
                            if fixtures_count > 0:
                                print(f"   ✅ Season {season_year}: {fixtures_count} fixtures found")
                                
                                # Check if any fixtures have halftime data
                                halftime_count = 0
                                for fixture in fixtures_data.get("response", []):
                                    if fixture.get("score", {}).get("halftime"):
                                        halftime_count += 1
                                
                                print(f"   📊 Halftime data available: {halftime_count}/{fixtures_count} fixtures")
                                available_seasons.append({
                                    "year": season_year,
                                    "fixtures": fixtures_count,
                                    "halftime_data": halftime_count
                                })
                            else:
                                print(f"   ❌ Season {season_year}: No fixtures found")
                        else:
                            print(f"   ❌ Season {season_year}: API error {fixtures_response.status_code}")
                        
                        # Small delay between requests
                        await asyncio.sleep(1)
                    
                    print(f"\n=== SUMMARY ===")
                    if available_seasons:
                        print("Available seasons with data:")
                        for season in available_seasons:
                            print(f"  {season['year']}: {season['fixtures']} fixtures, {season['halftime_data']} with halftime data")
                        
                        # Recommend the season with most data
                        best_season = max(available_seasons, key=lambda x: x['halftime_data'])
                        print(f"\n🎯 Recommended season: {best_season['year']}")
                        print(f"   - {best_season['fixtures']} total fixtures")
                        print(f"   - {best_season['halftime_data']} with halftime data")
                    else:
                        print("❌ No seasons with fixture data found")
                
                else:
                    print("❌ League not found")
            else:
                print(f"❌ API error: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    await check_available_seasons()

if __name__ == "__main__":
    asyncio.run(main())
