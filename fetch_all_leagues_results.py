#!/usr/bin/env python3
"""
Fetch fresh match results from API-Football for all GB leagues
"""

import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import json

# API-Football configuration
API_KEY = "your_api_key_here"  # Will be replaced with actual key
BASE_URL = "https://v3.football.api-sports.io"

def get_api_key():
    """Get API key from environment or config."""
    try:
        with open('config.yaml', 'r') as f:
            import yaml
            config = yaml.safe_load(f)
            return config.get('keys', {}).get('api_football_key', '')
    except:
        return ""

def fetch_league_fixtures(league_name, season=2024):
    """Fetch fixtures for a specific league from API-Football."""
    
    headers = {
        'x-apisports-key': API_KEY
    }
    
    # Map league names to API-Football league IDs
    league_mapping = {
        'Premier League': 39,  # England Premier League
        'Championship': 40,    # England Championship
        'League One': 41,      # England League One
        'League Two': 42,      # England League Two
        'Scottish Premiership': 179,  # Scotland Premiership
        'Scottish Championship': 180, # Scotland Championship
        'Scottish League One': 181,   # Scotland League One
        'Scottish League Two': 182,   # Scotland League Two
        'National League': 43,        # England National League
    }
    
    league_id = league_mapping.get(league_name)
    if not league_id:
        print(f"⚠️  No API mapping for league: {league_name}")
        return []
    
    print(f"🔍 Fetching fixtures for {league_name} (ID: {league_id})...")
    
    fixtures = []
    
    # Try different seasons
    seasons_to_try = [2024, 2023, 2022]
    
    for season in seasons_to_try:
        print(f"   Trying season {season}...")
        page = 1
        
        while True:
            url = f"{BASE_URL}/fixtures"
            params = {
                'league': league_id,
                'season': season,
                'page': page
            }
            
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Debug: print response info
                if page == 1:
                    print(f"     Response: {data.get('results', 0)} total results available")
                    if 'errors' in data:
                        print(f"     Errors: {data['errors']}")
                
                if 'response' not in data or not data['response']:
                    break
                
                for fixture in data['response']:
                    # Extract relevant information
                    fixture_info = {
                        'fixture_id': fixture['fixture']['id'],
                        'date': fixture['fixture']['date'][:10],
                        'home_team': fixture['teams']['home']['name'],
                        'away_team': fixture['teams']['away']['name'],
                        'home_goals': fixture['goals']['home'],
                        'away_goals': fixture['goals']['away'],
                        'home_goals_ht': fixture['score']['halftime']['home'],
                        'away_goals_ht': fixture['score']['halftime']['away'],
                        'status': fixture['fixture']['status']['short'],
                        'league_name': league_name,
                        'season': season
                    }
                    
                    fixtures.append(fixture_info)
                
                print(f"     Page {page}: {len(data['response'])} fixtures")
                page += 1
                
                # Rate limiting
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                print(f"     ❌ Error fetching {league_name} season {season}: {e}")
                break
            except Exception as e:
                print(f"     ❌ Unexpected error for {league_name} season {season}: {e}")
                break
        
        # If we got fixtures, break out of season loop
        if fixtures:
            break
    
    print(f"✅ {league_name}: {len(fixtures)} fixtures fetched")
    return fixtures

def fetch_all_leagues_results():
    """Fetch results for all leagues found in the GB dataset."""
    
    # Load the leagues we found
    try:
        df = pd.read_csv('all_gb_leagues_matches.csv')
        leagues = df['League'].unique()
        print(f"📊 Found {len(leagues)} leagues to fetch results for:")
        for league in leagues:
            print(f"   - {league}")
    except FileNotFoundError:
        print("❌ all_gb_leagues_matches.csv not found. Run extract_all_gb_leagues.py first.")
        return []
    
    all_fixtures = []
    
    for league in leagues:
        if league == 'Unknown':
            print(f"⚠️  Skipping Unknown league")
            continue
            
        fixtures = fetch_league_fixtures(league)
        all_fixtures.extend(fixtures)
        
        # Rate limiting between leagues
        time.sleep(1)
    
    return all_fixtures

def calculate_first_half_goals(fixtures):
    """Calculate first half goals for each fixture."""
    
    for fixture in fixtures:
        home_ht = fixture.get('home_goals_ht', 0)
        away_ht = fixture.get('away_goals_ht', 0)
        
        if home_ht is not None and away_ht is not None:
            total_ht_goals = home_ht + away_ht
            fixture['total_ht_goals'] = total_ht_goals
            fixture['has_ht_goals'] = total_ht_goals > 0
        else:
            fixture['total_ht_goals'] = None
            fixture['has_ht_goals'] = None
    
    return fixtures

def main():
    """Main function to fetch all league results."""
    
    global API_KEY
    API_KEY = get_api_key()
    
    if not API_KEY:
        print("❌ API key not found. Please set it in config.yaml")
        return
    
    print("🏴󠁧󠁢󠁥󠁮󠁧󠁿 Fetching All GB Leagues Results from API-Football")
    print("=" * 60)
    
    all_fixtures = fetch_all_leagues_results()
    
    if all_fixtures:
        print(f"\n📊 FETCH SUMMARY")
        print(f"   Total fixtures fetched: {len(all_fixtures)}")
        
        # Calculate first half goals
        all_fixtures = calculate_first_half_goals(all_fixtures)
        
        # Convert to DataFrame
        df = pd.DataFrame(all_fixtures)
        
        # Filter for completed matches only
        completed_df = df[df['status'] == 'FT'].copy()
        print(f"   Completed matches: {len(completed_df)}")
        
        # Show summary by league
        league_summary = completed_df.groupby('league_name').agg({
            'fixture_id': 'count',
            'has_ht_goals': lambda x: x.sum() if x.notna().any() else 0,
            'total_ht_goals': 'mean'
        }).round(2)
        
        league_summary.columns = ['Total_Matches', 'Matches_With_HT_Goals', 'Avg_HT_Goals']
        league_summary['HT_Goal_Rate'] = (league_summary['Matches_With_HT_Goals'] / league_summary['Total_Matches'] * 100).round(1)
        
        print(f"\n📈 LEAGUE SUMMARY")
        print(league_summary)
        
        # Save results
        completed_df.to_csv('all_leagues_api_results.csv', index=False)
        league_summary.to_csv('all_leagues_summary.csv')
        
        print(f"\n💾 Results saved to:")
        print(f"   - all_leagues_api_results.csv")
        print(f"   - all_leagues_summary.csv")
        
        # Show sample data
        print(f"\n📋 SAMPLE DATA")
        sample_cols = ['date', 'league_name', 'home_team', 'away_team', 'home_goals_ht', 'away_goals_ht', 'total_ht_goals', 'has_ht_goals']
        print(completed_df[sample_cols].head(10).to_string(index=False))
        
    else:
        print("❌ No fixtures fetched")

if __name__ == "__main__":
    main()
