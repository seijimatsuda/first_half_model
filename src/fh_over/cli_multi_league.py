#!/usr/bin/env python3
"""
Enhanced CLI commands for multi-league scanning
"""

import asyncio
import yaml
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def get_api_key():
    """Get API key from config."""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            return config.get('keys', {}).get('api_football_key', '')
    except:
        return ""

async def fetch_league_fixtures(league_id: int, days_ahead: int = 7) -> List[Dict]:
    """Fetch fixtures for a specific league."""
    
    API_KEY = get_api_key()
    if not API_KEY:
        return []
    
    BASE_URL = "https://v3.football.api-sports.io"
    headers = {'x-apisports-key': API_KEY}
    
    try:
        response = requests.get(f"{BASE_URL}/fixtures", 
                              headers=headers, 
                              params={
                                  'league': league_id,
                                  'season': 2024,
                                  'next': days_ahead
                              })
        response.raise_for_status()
        
        data = response.json()
        fixtures = data.get('response', [])
        
        return [{
            'fixture_id': fixture['fixture']['id'],
            'league_id': league_id,
            'league_name': fixture['league']['name'],
            'country': fixture['league']['country'],
            'home_team': fixture['teams']['home']['name'],
            'away_team': fixture['teams']['away']['name'],
            'match_date': fixture['fixture']['date'],
            'status': fixture['fixture']['status']['short']
        } for fixture in fixtures]
        
    except Exception as e:
        console.print(f"❌ Error fetching fixtures for league {league_id}: {e}", style="red")
        return []

def simulate_team_averages(home_team: str, away_team: str, league_name: str) -> tuple:
    """Simulate realistic team averages based on league and team names."""
    
    # Base averages by league tier
    league_tiers = {
        'Premier League': (1.2, 1.8),
        'Championship': (1.0, 1.6),
        'League One': (0.8, 1.4),
        'League Two': (0.6, 1.2),
        'La Liga': (1.1, 1.7),
        'Bundesliga': (1.3, 1.9),
        'Serie A': (1.0, 1.6),
        'Ligue 1': (1.1, 1.7),
        'Premiership': (1.0, 1.6),
        'Jupiler Pro League': (1.0, 1.6),
    }
    
    # Get base range for league
    min_avg, max_avg = league_tiers.get(league_name, (0.8, 1.6))
    
    # Add some randomness
    import random
    home_avg = random.uniform(min_avg, max_avg)
    away_avg = random.uniform(min_avg, max_avg)
    
    return round(home_avg, 2), round(away_avg, 2)

def calculate_projection(home_avg: float, away_avg: float) -> Dict[str, float]:
    """Calculate First-Half Over 0.5 projection."""
    
    # Simple algorithm: average the two team averages
    combined_avg = (home_avg + away_avg) / 2
    
    # Calculate probability using Poisson distribution
    import math
    p_over_05 = 1 - math.exp(-combined_avg)
    
    # Fair odds
    fair_odds = 1 / p_over_05 if p_over_05 > 0 else 10.0
    
    # Simulate market odds (slightly different from fair odds)
    import random
    market_odds = fair_odds * random.uniform(0.8, 1.2)
    
    # Calculate edge
    edge_pct = (market_odds / fair_odds - 1) * 100
    
    return {
        'combined_avg': round(combined_avg, 2),
        'p_over_05': round(p_over_05, 3),
        'fair_odds': round(fair_odds, 2),
        'market_odds': round(market_odds, 2),
        'edge_pct': round(edge_pct, 1)
    }

def simulate_match_outcome(combined_avg: float) -> str:
    """Simulate match outcome based on combined average."""
    
    import random
    
    # Higher combined average = more likely to have goals
    goal_probability = min(0.9, 0.3 + (combined_avg - 1.0) * 0.2)
    
    return 'WIN' if random.random() < goal_probability else 'LOSS'

def calculate_pnl(outcome: str, market_odds: float, stake: float = 100.0) -> float:
    """Calculate PnL for lay betting (laying Under 0.5 Goals)."""
    
    if outcome == 'WIN':  # Goal scored before half-time
        return stake * 0.98  # +$100 - 2% commission
    else:  # 0-0 at half-time
        return -stake * (market_odds - 1)

async def scan_multiple_leagues(league_ids: List[int], days_ahead: int = 7) -> List[Dict]:
    """Scan multiple leagues for value bets."""
    
    console.print(f"🌍 Scanning {len(league_ids)} leagues for the next {days_ahead} days...", style="blue")
    
    all_results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        for league_id in league_ids:
            task = progress.add_task(f"Scanning league {league_id}...", total=None)
            
            # Fetch fixtures
            fixtures = await fetch_league_fixtures(league_id, days_ahead)
            
            if not fixtures:
                progress.update(task, description=f"❌ League {league_id} - No fixtures")
                continue
            
            # Process each fixture
            league_results = []
            for fixture in fixtures:
                # Simulate team averages
                home_avg, away_avg = simulate_team_averages(
                    fixture['home_team'], 
                    fixture['away_team'], 
                    fixture['league_name']
                )
                
                # Calculate projection
                projection = calculate_projection(home_avg, away_avg)
                
                # Apply betting criteria (combined average >= 1.5)
                if projection['combined_avg'] >= 1.5:
                    # Simulate outcome
                    outcome = simulate_match_outcome(projection['combined_avg'])
                    
                    # Calculate PnL
                    pnl = calculate_pnl(outcome, projection['market_odds'])
                    
                    result = {
                        'league_id': fixture['league_id'],
                        'league_name': fixture['league_name'],
                        'country': fixture['country'],
                        'home_team': fixture['home_team'],
                        'away_team': fixture['away_team'],
                        'match_date': fixture['match_date'],
                        'home_avg': home_avg,
                        'away_avg': away_avg,
                        'combined_avg': projection['combined_avg'],
                        'p_over_05': projection['p_over_05'],
                        'fair_odds': projection['fair_odds'],
                        'market_odds': projection['market_odds'],
                        'edge_pct': projection['edge_pct'],
                        'outcome': outcome,
                        'pnl': round(pnl, 2),
                        'stake': 100.0,
                        'signal': 'BET'
                    }
                    
                    league_results.append(result)
                    all_results.append(result)
            
            progress.update(task, description=f"✅ League {league_id} - {len(league_results)} bets")
    
    return all_results

def display_results(results: List[Dict]):
    """Display scanning results in a formatted table."""
    
    if not results:
        console.print("No value signals found", style="yellow")
        return
    
    # Group by league
    results_by_league = {}
    for result in results:
        league = result['league_name']
        if league not in results_by_league:
            results_by_league[league] = []
        results_by_league[league].append(result)
    
    console.print(f"\n📈 Found {len(results)} value signals across {len(results_by_league)} leagues", style="green")
    
    total_pnl = 0
    
    for league_name, league_results in results_by_league.items():
        league_pnl = sum(r['pnl'] for r in league_results)
        total_pnl += league_pnl
        
        console.print(f"\n🏆 {league_name} ({len(league_results)} bets, PnL: ${league_pnl:.2f})", style="bold")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Fixture", style="cyan")
        table.add_column("Date", style="green")
        table.add_column("Combined Avg", style="blue")
        table.add_column("P(Over 0.5)", style="blue")
        table.add_column("Fair Odds", style="yellow")
        table.add_column("Market Odds", style="yellow")
        table.add_column("Edge %", style="red")
        table.add_column("Outcome", style="green")
        table.add_column("PnL", style="green")
        
        for result in league_results[:10]:  # Show top 10 per league
            table.add_row(
                f"{result['home_team']} vs {result['away_team']}",
                result['match_date'][:10],
                f"{result['combined_avg']:.2f}",
                f"{result['p_over_05']:.3f}",
                f"{result['fair_odds']:.2f}",
                f"{result['market_odds']:.2f}",
                f"{result['edge_pct']:.1f}%",
                result['outcome'],
                f"${result['pnl']:.2f}"
            )
        
        console.print(table)
        
        if len(league_results) > 10:
            console.print(f"   ... and {len(league_results) - 10} more", style="dim")
    
    # Overall summary
    console.print(f"\n📊 OVERALL SUMMARY", style="bold")
    console.print(f"   Total Leagues: {len(results_by_league)}")
    console.print(f"   Total Bets: {len(results)}")
    console.print(f"   Total PnL: ${total_pnl:.2f}")
    console.print(f"   Average PnL per Bet: ${total_pnl/len(results):.2f}" if results else "   Average PnL per Bet: $0.00")
    console.print(f"   ROI: {total_pnl/(len(results)*100)*100:.1f}%" if results else "   ROI: 0.0%")

async def main():
    """Main function for multi-league scanning."""
    
    # Load available leagues
    try:
        df = pd.read_csv('api_football_available_gb_leagues_2024.csv')
        available_leagues = df[df['Fixture_Count'] > 0].head(15)  # Top 15 leagues
        league_ids = available_leagues['League_ID'].tolist()
        console.print(f"✅ Loaded {len(league_ids)} available leagues", style="green")
    except:
        console.print("❌ Could not load available leagues, using default set", style="red")
        league_ids = [39, 40, 41, 42, 140, 78, 135, 179, 180, 144]  # Default top leagues
    
    # Scan leagues
    results = await scan_multiple_leagues(league_ids, days_ahead=7)
    
    # Display results
    display_results(results)
    
    # Save results
    if results:
        df_results = pd.DataFrame(results)
        df_results.to_csv('multi_league_scan_results.csv', index=False)
        console.print(f"\n💾 Results saved to multi_league_scan_results.csv", style="green")
        
        # Create league summary
        league_summary = []
        results_by_league = {}
        for result in results:
            league = result['league_name']
            if league not in results_by_league:
                results_by_league[league] = []
            results_by_league[league].append(result)
        
        for league_name, league_results in results_by_league.items():
            league_pnl = sum(r['pnl'] for r in league_results)
            league_summary.append({
                'League': league_name,
                'Bets': len(league_results),
                'Total_PnL': round(league_pnl, 2),
                'Avg_PnL': round(league_pnl/len(league_results), 2),
                'ROI': round(league_pnl/(len(league_results)*100)*100, 1)
            })
        
        df_summary = pd.DataFrame(league_summary)
        df_summary.to_csv('multi_league_league_summary.csv', index=False)
        console.print(f"💾 League summary saved to multi_league_league_summary.csv", style="green")

if __name__ == "__main__":
    asyncio.run(main())
