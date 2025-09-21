#!/usr/bin/env python3
"""
List all available leagues from API-Football
"""

import requests
import yaml
import pandas as pd
import time

def get_api_key():
    """Get API key from config."""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            return config.get('keys', {}).get('api_football_key', '')
    except:
        return ""

def fetch_all_leagues():
    """Fetch all available leagues from API-Football."""
    
    API_KEY = get_api_key()
    if not API_KEY:
        print("❌ API key not found")
        return None
    
    BASE_URL = "https://v3.football.api-sports.io"
    headers = {'x-apisports-key': API_KEY}
    
    print("🔍 Fetching all available leagues from API-Football...")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/leagues", headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        if 'response' not in data:
            print("❌ No response data found")
            return None
        
        leagues = data['response']
        print(f"✅ Found {len(leagues)} leagues")
        
        # Process and categorize leagues
        league_data = []
        
        for league in leagues:
            league_info = {
                'League_ID': league['league']['id'],
                'League_Name': league['league']['name'],
                'League_Type': league['league']['type'],
                'Country': league['country']['name'],
                'Country_Code': league['country']['code'],
                'Country_Flag': league['country']['flag'],
                'Seasons': [season['year'] for season in league['seasons']],
                'Current_Season': league['seasons'][-1]['year'] if league['seasons'] else None,
                'Logo': league['league']['logo']
            }
            league_data.append(league_info)
        
        return league_data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching leagues: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def categorize_leagues(leagues):
    """Categorize leagues by country and type."""
    
    if not leagues:
        return
    
    # Group by country
    by_country = {}
    for league in leagues:
        country = league['Country']
        if country not in by_country:
            by_country[country] = []
        by_country[country].append(league)
    
    # Sort countries by number of leagues
    sorted_countries = sorted(by_country.items(), key=lambda x: len(x[1]), reverse=True)
    
    print(f"\n📊 LEAGUES BY COUNTRY")
    print("=" * 60)
    
    for country, country_leagues in sorted_countries:
        print(f"\n🏴 {country} ({len(country_leagues)} leagues)")
        for league in country_leagues:
            seasons_str = f"{min(league['Seasons'])}-{max(league['Seasons'])}" if league['Seasons'] else "No seasons"
            print(f"   {league['League_ID']:3d} | {league['League_Name']:30s} | {league['League_Type']:10s} | {seasons_str}")
    
    return by_country

def filter_gb_leagues(leagues):
    """Filter for Great Britain leagues specifically."""
    
    gb_countries = ['England', 'Scotland', 'Wales', 'Northern Ireland']
    gb_leagues = []
    
    for league in leagues:
        if league['Country'] in gb_countries:
            gb_leagues.append(league)
    
    print(f"\n🏴󠁧󠁢󠁥󠁮󠁧󠁿 GREAT BRITAIN LEAGUES")
    print("=" * 60)
    
    for country in gb_countries:
        country_leagues = [l for l in gb_leagues if l['Country'] == country]
        if country_leagues:
            print(f"\n🏴 {country} ({len(country_leagues)} leagues)")
            for league in country_leagues:
                seasons_str = f"{min(league['Seasons'])}-{max(league['Seasons'])}" if league['Seasons'] else "No seasons"
                print(f"   {league['League_ID']:3d} | {league['League_Name']:40s} | {league['League_Type']:10s} | {seasons_str}")
    
    return gb_leagues

def check_league_fixtures(league_id, league_name, season=2024):
    """Check if a league has fixtures available for a specific season."""
    
    API_KEY = get_api_key()
    BASE_URL = "https://v3.football.api-sports.io"
    headers = {'x-apisports-key': API_KEY}
    
    try:
        response = requests.get(f"{BASE_URL}/fixtures", headers=headers, params={
            'league': league_id,
            'season': season
        })
        response.raise_for_status()
        
        data = response.json()
        fixture_count = len(data.get('response', []))
        
        return fixture_count > 0, fixture_count
        
    except:
        return False, 0

def main():
    """Main function to list all available leagues."""
    
    print("🌍 API-Football Leagues Explorer")
    print("=" * 60)
    
    # Fetch all leagues
    leagues = fetch_all_leagues()
    if not leagues:
        return
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(leagues)
    
    # Show basic stats
    print(f"\n📈 BASIC STATISTICS")
    print(f"   Total leagues: {len(leagues)}")
    print(f"   Countries: {df['Country'].nunique()}")
    print(f"   League types: {df['League_Type'].unique().tolist()}")
    
    # Categorize by country
    by_country = categorize_leagues(leagues)
    
    # Filter for GB leagues
    gb_leagues = filter_gb_leagues(leagues)
    
    # Save results
    df.to_csv('api_football_all_leagues.csv', index=False)
    
    gb_df = pd.DataFrame(gb_leagues)
    gb_df.to_csv('api_football_gb_leagues.csv', index=False)
    
    print(f"\n💾 Results saved to:")
    print(f"   - api_football_all_leagues.csv")
    print(f"   - api_football_gb_leagues.csv")
    
    # Check availability for 2024 season for GB leagues
    print(f"\n🔍 CHECKING 2024 SEASON AVAILABILITY FOR GB LEAGUES")
    print("=" * 60)
    
    available_leagues = []
    for league in gb_leagues:
        league_id = league['League_ID']
        league_name = league['League_Name']
        
        print(f"Checking {league_name}...", end=" ")
        
        has_fixtures, count = check_league_fixtures(league_id, league_name, 2024)
        
        if has_fixtures:
            print(f"✅ {count} fixtures")
            available_leagues.append({
                'League_ID': league_id,
                'League_Name': league_name,
                'Country': league['Country'],
                'Fixture_Count': count
            })
        else:
            print("❌ No fixtures")
        
        # Rate limiting
        time.sleep(0.1)
    
    if available_leagues:
        print(f"\n✅ AVAILABLE GB LEAGUES FOR 2024 SEASON")
        print("=" * 60)
        for league in available_leagues:
            print(f"   {league['League_ID']:3d} | {league['League_Name']:40s} | {league['Country']:10s} | {league['Fixture_Count']:4d} fixtures")
        
        # Save available leagues
        available_df = pd.DataFrame(available_leagues)
        available_df.to_csv('api_football_available_gb_leagues_2024.csv', index=False)
        print(f"\n💾 Available leagues saved to: api_football_available_gb_leagues_2024.csv")
    
    else:
        print(f"\n❌ No GB leagues have fixtures available for 2024 season")

if __name__ == "__main__":
    main()
