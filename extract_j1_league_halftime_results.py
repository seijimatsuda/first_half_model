#!/usr/bin/env python3
"""
Extract all J1 League fixtures with first-half results
"""

import asyncio
import httpx
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import os

class J1LeagueDataExtractor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://v3.football.api-sports.io"
        self.league_id = 98  # J1 League
        self.headers = {
            'x-apisports-key': api_key,
            'Accept': 'application/json'
        }
    
    async def get_fixtures(self, season: int = 2025) -> List[Dict[str, Any]]:
        """Get all fixtures for J1 League"""
        print(f"Fetching fixtures for J1 League (Season {season})...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Get all fixtures for the league
                params = {
                    "league": self.league_id,
                    "season": season
                }
                
                response = await client.get(
                    f"{self.base_url}/fixtures",
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                fixtures = []
                for fixture_data in data.get("response", []):
                    fixture_info = fixture_data.get("fixture", {})
                    teams = fixture_data.get("teams", {})
                    goals = fixture_data.get("goals", {})
                    score = fixture_data.get("score", {})
                    
                    # Extract halftime scores
                    halftime_score = score.get("halftime", {})
                    home_ht_goals = halftime_score.get("home")
                    away_ht_goals = halftime_score.get("away")
                    
                    # Extract full-time scores
                    home_ft_goals = goals.get("home")
                    away_ft_goals = goals.get("away")
                    
                    fixture_info_dict = {
                        'fixture_id': fixture_info.get("id"),
                        'league_id': self.league_id,
                        'league_name': 'J1 League',
                        'season': season,
                        'match_date': fixture_info.get("date"),
                        'match_status': fixture_info.get("status", {}).get("short"),
                        'venue': fixture_info.get("venue", {}).get("name"),
                        'venue_city': fixture_info.get("venue", {}).get("city"),
                        
                        # Teams
                        'home_team_id': teams.get("home", {}).get("id"),
                        'home_team_name': teams.get("home", {}).get("name"),
                        'away_team_id': teams.get("away", {}).get("id"),
                        'away_team_name': teams.get("away", {}).get("name"),
                        
                        # Full-time scores
                        'home_ft_score': home_ft_goals,
                        'away_ft_score': away_ft_goals,
                        
                        # Half-time scores
                        'home_ht_score': home_ht_goals,
                        'away_ht_score': away_ht_goals,
                        
                        # Total first-half goals
                        'total_ht_goals': None,
                        'has_ht_data': False
                    }
                    
                    # Calculate total first-half goals if available
                    if home_ht_goals is not None and away_ht_goals is not None:
                        fixture_info_dict['total_ht_goals'] = home_ht_goals + away_ht_goals
                        fixture_info_dict['has_ht_data'] = True
                    
                    fixtures.append(fixture_info_dict)
                
                print(f"Found {len(fixtures)} fixtures")
                return fixtures
                
            except Exception as e:
                print(f"Error fetching fixtures: {e}")
                return []
    
    def save_to_excel(self, fixtures: List[Dict[str, Any]], filename: str):
        """Save fixtures to Excel file"""
        if not fixtures:
            print("No fixtures to save")
            return
        
        df = pd.DataFrame(fixtures)
        
        # Sort by match date and remove timezone info for Excel compatibility
        df['match_date'] = pd.to_datetime(df['match_date']).dt.tz_localize(None)
        df = df.sort_values('match_date')
        
        # Save to Excel
        df.to_excel(filename, index=False)
        print(f"Saved {len(fixtures)} fixtures to {filename}")
        
        # Display summary
        self.display_summary(df)
    
    def display_summary(self, df: pd.DataFrame):
        """Display summary statistics"""
        print("\n=== J1 LEAGUE HALFTIME RESULTS SUMMARY ===")
        
        total_fixtures = len(df)
        fixtures_with_ht_data = len(df[df['has_ht_data'] == True])
        fixtures_finished = len(df[df['match_status'] == 'FT'])
        
        print(f"Total fixtures: {total_fixtures}")
        print(f"Fixtures with halftime data: {fixtures_with_ht_data}")
        print(f"Finished matches: {fixtures_finished}")
        print(f"Halftime data coverage: {(fixtures_with_ht_data/total_fixtures*100):.1f}%")
        
        if fixtures_with_ht_data > 0:
            ht_df = df[df['has_ht_data'] == True]
            
            print(f"\n=== HALFTIME GOALS STATISTICS ===")
            print(f"Average first-half goals per match: {ht_df['total_ht_goals'].mean():.2f}")
            print(f"Minimum first-half goals: {ht_df['total_ht_goals'].min()}")
            print(f"Maximum first-half goals: {ht_df['total_ht_goals'].max()}")
            
            # Goals distribution
            goal_counts = ht_df['total_ht_goals'].value_counts().sort_index()
            print(f"\nFirst-half goals distribution:")
            for goals, count in goal_counts.items():
                percentage = (count / len(ht_df)) * 100
                print(f"  {goals} goals: {count} matches ({percentage:.1f}%)")
            
            # Teams with most first-half goals
            print(f"\n=== TEAMS - FIRST HALF GOALS ===")
            home_goals = ht_df.groupby('home_team_name')['home_ht_score'].sum().sort_values(ascending=False)
            away_goals = ht_df.groupby('away_team_name')['away_ht_score'].sum().sort_values(ascending=False)
            
            print("Top 5 teams - Home first-half goals:")
            for team, goals in home_goals.head().items():
                print(f"  {team}: {goals} goals")
            
            print("\nTop 5 teams - Away first-half goals:")
            for team, goals in away_goals.head().items():
                print(f"  {team}: {goals} goals")
        
        # Sample results
        if fixtures_with_ht_data > 0:
            print(f"\n=== SAMPLE RESULTS ===")
            sample_df = ht_df[['match_date', 'home_team_name', 'away_team_name', 
                              'home_ht_score', 'away_ht_score', 'total_ht_goals']].head(10)
            print(sample_df.to_string(index=False))


async def main():
    """Main function"""
    api_key = '9620b5a904bfe764ace4bc327e9fa629'
    
    if not api_key:
        print("❌ Error: API key not found")
        return
    
    extractor = J1LeagueDataExtractor(api_key)
    
    # Get data for current season (2025)
    print("Fetching J1 League halftime results for 2025 season...")
    
    fixtures = await extractor.get_fixtures(2025)
    
    if fixtures:
        # Save to Excel
        filename = "j1_league_2025_halftime_results.xlsx"
        extractor.save_to_excel(fixtures, filename)
        
        # Also save as CSV for compatibility
        csv_filename = "j1_league_2025_halftime_results.csv"
        df = pd.DataFrame(fixtures)
        df.to_csv(csv_filename, index=False)
        print(f"Also saved as CSV: {csv_filename}")
        
        print(f"\n✅ J1 League data extraction complete!")
        print(f"📁 Excel file: {filename}")
        print(f"📁 CSV file: {csv_filename}")
    else:
        print("❌ No fixtures found")


if __name__ == "__main__":
    asyncio.run(main())
