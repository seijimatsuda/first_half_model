#!/usr/bin/env python3
"""
Premier League Odds Matcher

This module processes GB_BF_Data.tar to extract Premier League First Half Goals 0.5 odds
and matches them with existing bet predictions to create accurate PnL calculations.
"""

import json
import bz2
import tarfile
import pandas as pd
import numpy as np
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
from collections import defaultdict

class PremierLeagueOddsMatcher:
    """Matches Premier League odds with bet predictions."""
    
    def __init__(self, tar_path: str, temp_dir: str = "temp_gb_odds"):
        self.tar_path = tar_path
        self.temp_dir = temp_dir
        self.odds_data = {}
        self.premier_league_teams = {
            'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton', 'Chelsea',
            'Crystal Palace', 'Everton', 'Fulham', 'Ipswich', 'Leicester', 'Liverpool',
            'Luton', 'Manchester City', 'Manchester United', 'Newcastle', 'Nottingham Forest',
            'Sheffield United', 'Southampton', 'Tottenham', 'West Ham', 'Wolves'
        }
        
        # Common team name variations for matching
        self.team_aliases = {
            'Arsenal': ['Arsenal'],
            'Aston Villa': ['Aston Villa', 'Villa'],
            'Bournemouth': ['Bournemouth', 'AFC Bournemouth'],
            'Brentford': ['Brentford'],
            'Brighton': ['Brighton', 'Brighton & Hove Albion', 'Brighton & Hove'],
            'Chelsea': ['Chelsea'],
            'Crystal Palace': ['Crystal Palace', 'Palace'],
            'Everton': ['Everton'],
            'Fulham': ['Fulham'],
            'Ipswich': ['Ipswich', 'Ipswich Town'],
            'Leicester': ['Leicester', 'Leicester City'],
            'Liverpool': ['Liverpool'],
            'Luton': ['Luton', 'Luton Town'],
            'Manchester City': ['Manchester City', 'Man City', 'Man. City'],
            'Manchester United': ['Manchester United', 'Man United', 'Man Utd', 'Man. United'],
            'Newcastle': ['Newcastle', 'Newcastle United'],
            'Nottingham Forest': ['Nottingham Forest', 'Nott\'m Forest', 'Notts Forest'],
            'Sheffield United': ['Sheffield United', 'Sheff Utd'],
            'Southampton': ['Southampton'],
            'Tottenham': ['Tottenham', 'Tottenham Hotspur', 'Spurs'],
            'West Ham': ['West Ham', 'West Ham United'],
            'Wolves': ['Wolves', 'Wolverhampton', 'Wolverhampton Wanderers']
        }
    
    def extract_archive(self) -> None:
        """Extract the tar archive to temporary directory."""
        print(f"Extracting {self.tar_path} to {self.temp_dir}...")
        with tarfile.open(self.tar_path, 'r') as tar:
            tar.extractall(self.temp_dir)
        print("Extraction complete.")
    
    def parse_bz2_file(self, file_path: str) -> List[Dict]:
        """Parse a single .bz2 file and extract market data."""
        data = []
        try:
            with bz2.open(file_path, 'rt') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        data.append(record)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
        return data
    
    def is_premier_league_match(self, event_name: str) -> bool:
        """Check if an event is a Premier League match."""
        event_lower = event_name.lower()
        
        # Check for Premier League team names
        for team, aliases in self.team_aliases.items():
            for alias in aliases:
                if alias.lower() in event_lower:
                    return True
        
        return False
    
    def extract_premier_league_odds(self, records: List[Dict]) -> Dict:
        """Extract Premier League First Half Goals 0.5 odds from records."""
        market_data = {}
        
        for record in records:
            if record.get('op') != 'mcm':
                continue
                
            mc = record.get('mc', [])
            for market in mc:
                market_id = market.get('id')
                if not market_id:
                    continue
                
                # Extract market definition
                if 'marketDefinition' in market:
                    md = market['marketDefinition']
                    event_id = md.get('eventId')
                    event_name = md.get('eventName', '')
                    market_type = md.get('marketType', '')
                    market_time = md.get('marketTime', '')
                    country_code = md.get('countryCode', '')
                    
                    # Only process UK First Half Goals 0.5 markets
                    if (country_code == 'GB' and 
                        'FIRST_HALF_GOALS_05' in market_type and
                        self.is_premier_league_match(event_name)):
                        
                        if market_id not in market_data:
                            market_data[market_id] = {
                                'event_id': event_id,
                                'event_name': event_name,
                                'market_type': market_type,
                                'market_time': market_time,
                                'odds_history': [],
                                'runners': {}
                            }
                        
                        # Extract runner information
                        runners = md.get('runners', [])
                        for runner in runners:
                            runner_id = runner.get('id')
                            runner_name = runner.get('name', '')
                            market_data[market_id]['runners'][runner_id] = runner_name
                
                # Extract price changes
                if 'rc' in market and market_id in market_data:
                    price_changes = market['rc']
                    for change in price_changes:
                        runner_id = change.get('id')
                        ltp = change.get('ltp')  # Last traded price
                        if ltp and runner_id:
                            market_data[market_id]['odds_history'].append({
                                'runner_id': runner_id,
                                'price': ltp,
                                'timestamp': record.get('pt', 0)
                            })
        
        return market_data
    
    def parse_all_files(self) -> None:
        """Parse all .bz2 files in the extracted archive."""
        print("Parsing all GB Betfair data files...")
        
        temp_path = Path(self.temp_dir)
        bz2_files = list(temp_path.rglob("*.bz2"))
        print(f"Found {len(bz2_files)} .bz2 files to process")
        
        all_market_data = {}
        
        for i, file_path in enumerate(bz2_files):
            if i % 50 == 0:
                print(f"Processing file {i+1}/{len(bz2_files)}: {file_path.name}")
            
            records = self.parse_bz2_file(str(file_path))
            market_data = self.extract_premier_league_odds(records)
            all_market_data.update(market_data)
        
        self.odds_data = all_market_data
        print(f"Parsed {len(self.odds_data)} Premier League markets")
    
    def get_closing_odds(self, market_id: str) -> Optional[Dict[str, float]]:
        """Get the closing odds for a market before kickoff."""
        if market_id not in self.odds_data:
            return None
        
        market = self.odds_data[market_id]
        odds_history = market['odds_history']
        
        if not odds_history:
            return None
        
        # Get the last price for each runner before kickoff
        market_time = datetime.fromisoformat(market['market_time'].replace('Z', '+00:00'))
        
        # Filter prices before kickoff and get the latest for each runner
        pre_kickoff_prices = {}
        for price_record in odds_history:
            price_time = datetime.fromtimestamp(price_record['timestamp'] / 1000, tz=timezone.utc)
            if price_time < market_time:
                runner_id = price_record['runner_id']
                price = price_record['price']
                if runner_id not in pre_kickoff_prices or price_time > pre_kickoff_prices[runner_id]['time']:
                    pre_kickoff_prices[runner_id] = {
                        'price': price,
                        'time': price_time
                    }
        
        # Convert to closing odds format
        closing_odds = {}
        for runner_id, price_data in pre_kickoff_prices.items():
            runner_name = market['runners'].get(runner_id, f'Runner_{runner_id}')
            closing_odds[runner_name] = price_data['price']
        
        return closing_odds if closing_odds else None
    
    def normalize_team_name(self, name: str) -> str:
        """Normalize team names for matching."""
        name = name.strip()
        
        # Direct mapping
        for normalized, aliases in self.team_aliases.items():
            if name in aliases:
                return normalized
        
        # Try partial matching
        for normalized, aliases in self.team_aliases.items():
            for alias in aliases:
                if alias.lower() in name.lower() or name.lower() in alias.lower():
                    return normalized
        
        return name
    
    def extract_teams_from_event_name(self, event_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract home and away team names from Betfair event name."""
        # Common patterns: "Team A v Team B", "Team A vs Team B"
        patterns = [
            r'(.+?)\s+v\s+(.+)',
            r'(.+?)\s+vs\s+(.+)',
            r'(.+?)\s+-\s+(.+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, event_name, re.IGNORECASE)
            if match:
                home_team = match.group(1).strip()
                away_team = match.group(2).strip()
                return home_team, away_team
        
        return None, None
    
    def match_odds_to_predictions(self, predictions_df: pd.DataFrame) -> pd.DataFrame:
        """Match Betfair odds to model predictions."""
        print("Matching Betfair odds to model predictions...")
        
        matched_predictions = []
        
        for _, pred in predictions_df.iterrows():
            home_team = self.normalize_team_name(pred['Home Team'])
            away_team = self.normalize_team_name(pred['Away Team'])
            pred_date = pd.to_datetime(pred['Date']).date()
            
            # Find matching Betfair event
            best_match = None
            best_score = 0
            
            for market_id, market in self.odds_data.items():
                event_name = market['event_name']
                market_time = datetime.fromisoformat(market['market_time'].replace('Z', '+00:00')).date()
                
                # Check if dates match (within 1 day tolerance)
                if abs((market_time - pred_date).days) <= 1:
                    # Extract teams from event name
                    event_home, event_away = self.extract_teams_from_event_name(event_name)
                    
                    if event_home and event_away:
                        # Normalize event team names
                        event_home_norm = self.normalize_team_name(event_home)
                        event_away_norm = self.normalize_team_name(event_away)
                        
                        # Calculate match score
                        score = 0
                        if event_home_norm == home_team:
                            score += 1
                        if event_away_norm == away_team:
                            score += 1
                        
                        # Check for common variations
                        if (event_home_norm in self.team_aliases.get(home_team, []) or
                            home_team in self.team_aliases.get(event_home_norm, [])):
                            score += 0.5
                        if (event_away_norm in self.team_aliases.get(away_team, []) or
                            away_team in self.team_aliases.get(event_away_norm, [])):
                            score += 0.5
                        
                        if score > best_score:
                            best_score = score
                            best_match = {
                                'market_id': market_id,
                                'event_name': event_name,
                                'market_time': market_time,
                                'score': score,
                                'event_home': event_home,
                                'event_away': event_away
                            }
            
            if best_match and best_score >= 1.5:  # Require at least partial match
                # Get closing odds for this market
                closing_odds = self.get_closing_odds(best_match['market_id'])
                
                if closing_odds and 'Over 0.5 Goals' in closing_odds:
                    matched_pred = pred.copy()
                    matched_pred['betfair_market_id'] = best_match['market_id']
                    matched_pred['betfair_event_name'] = best_match['event_name']
                    matched_pred['betfair_home_team'] = best_match['event_home']
                    matched_pred['betfair_away_team'] = best_match['event_away']
                    matched_pred['over_odds'] = closing_odds['Over 0.5 Goals']
                    matched_pred['under_odds'] = closing_odds.get('Under 0.5 Goals', None)
                    matched_pred['match_score'] = best_score
                    matched_predictions.append(matched_pred)
                    print(f"✓ Matched: {home_team} vs {away_team} -> {best_match['event_name']} (odds: {closing_odds['Over 0.5 Goals']})")
                else:
                    print(f"✗ No closing odds found for {home_team} vs {away_team} on {pred_date}")
            else:
                print(f"✗ No Betfair match found for {home_team} vs {away_team} on {pred_date}")
        
        return pd.DataFrame(matched_predictions)
    
    def calculate_pnl_with_real_odds(self, matched_predictions: pd.DataFrame, stake: float = 100.0) -> Dict:
        """Calculate PnL using real Betfair closing odds."""
        print(f"Calculating PnL with real Betfair odds and ${stake} flat stakes...")
        
        total_bets = len(matched_predictions)
        total_staked = total_bets * stake
        total_winnings = 0.0
        winning_bets = 0
        losing_bets = 0
        
        bet_details = []
        
        for _, bet in matched_predictions.iterrows():
            odds = bet['over_odds']
            model_result = bet['ModelResult']
            
            if model_result == 'WIN':
                winnings = stake * (odds - 1)  # Profit = stake * (odds - 1)
                total_winnings += winnings
                winning_bets += 1
                bet_result = 'WIN'
            else:  # LOSS
                winnings = -stake  # Lose the stake
                total_winnings += winnings
                losing_bets += 1
                bet_result = 'LOSS'
            
            bet_details.append({
                'Date': bet['Date'],
                'Home Team': bet['Home Team'],
                'Away Team': bet['Away Team'],
                'Betfair Event': bet['betfair_event_name'],
                'Betfair Home': bet['betfair_home_team'],
                'Betfair Away': bet['betfair_away_team'],
                'Over Odds': odds,
                'Under Odds': bet.get('under_odds'),
                'Stake': stake,
                'Model Result': model_result,
                'Bet Result': bet_result,
                'Profit/Loss': winnings,
                'Match Score': bet.get('match_score', 0)
            })
        
        net_profit = total_winnings
        roi = (net_profit / total_staked) * 100 if total_staked > 0 else 0
        win_rate = (winning_bets / total_bets) * 100 if total_bets > 0 else 0
        
        return {
            'total_bets': total_bets,
            'total_staked': total_staked,
            'winning_bets': winning_bets,
            'losing_bets': losing_bets,
            'win_rate': win_rate,
            'total_winnings': total_winnings,
            'net_profit': net_profit,
            'roi': roi,
            'bet_details': bet_details
        }
    
    def run_full_analysis(self, predictions_file: str) -> Dict:
        """Run the complete analysis pipeline."""
        print("Starting Premier League odds matching analysis...")
        
        # Extract and parse data
        self.extract_archive()
        self.parse_all_files()
        
        # Load predictions
        print(f"Loading predictions from {predictions_file}...")
        predictions_df = pd.read_csv(predictions_file)
        
        # Match odds and calculate PnL
        matched_predictions = self.match_odds_to_predictions(predictions_df)
        pnl_results = self.calculate_pnl_with_real_odds(matched_predictions)
        
        print(f"\n📊 PREMIER LEAGUE PnL ANALYSIS RESULTS")
        print("=" * 50)
        print(f"Total bets matched: {pnl_results['total_bets']}")
        print(f"Total staked: ${pnl_results['total_staked']:,.2f}")
        print(f"Winning bets: {pnl_results['winning_bets']}")
        print(f"Losing bets: {pnl_results['losing_bets']}")
        print(f"Win rate: {pnl_results['win_rate']:.1f}%")
        print(f"Total winnings: ${pnl_results['total_winnings']:,.2f}")
        print(f"Net profit: ${pnl_results['net_profit']:,.2f}")
        print(f"ROI: {pnl_results['roi']:.1f}%")
        
        return pnl_results

def main():
    """Main function to run the analysis."""
    matcher = PremierLeagueOddsMatcher("data/GB_BF_Data.tar")
    
    # Run analysis on the matchweek 5+ predictions
    results = matcher.run_full_analysis("matchweek5_plus_predictions.csv")
    
    # Save detailed results
    bet_details_df = pd.DataFrame(results['bet_details'])
    bet_details_df.to_csv("premier_league_real_odds_analysis.csv", index=False)
    print(f"\nDetailed results saved to: premier_league_real_odds_analysis.csv")
    
    return results

if __name__ == "__main__":
    main()
