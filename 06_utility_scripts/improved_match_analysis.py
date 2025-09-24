#!/usr/bin/env python3
"""
Improved analysis to find more overlapping matches between predictions and GB odds data
"""

import json
import subprocess
import pandas as pd
import bz2
import os
from datetime import datetime
import re
from collections import defaultdict

def extract_all_odds_data():
    """Extract all odds data from GB_24_25.tar"""
    print("Extracting ALL odds data from GB_24_25.tar...")
    
    # Get list of files
    result = subprocess.run(['tar', '-tf', 'data/GB_24_25.tar'], 
                          capture_output=True, text=True, cwd='/Users/seijimatsuda/first_half_model')
    
    files = [f for f in result.stdout.strip().split('\n') if f.endswith('.bz2')]
    print(f"Found {len(files)} bz2 files")
    
    all_matches = []
    league_counts = defaultdict(int)
    
    # Process all files
    for i, file_path in enumerate(files):
        if i % 1000 == 0:
            print(f"Processing file {i+1}/{len(files)}")
            
        try:
            # Extract file
            subprocess.run(['tar', '-xf', 'data/GB_24_25.tar', file_path], 
                         cwd='/Users/seijimatsuda/first_half_model', 
                         capture_output=True)
            
            # Read file
            with bz2.open(file_path, 'rt') as f:
                lines = f.readlines()
                
                if not lines:
                    continue
                
                # Get market definition from first line
                first_data = json.loads(lines[0])
                
                if 'mc' in first_data and len(first_data['mc']) > 0:
                    market_def = first_data['mc'][0].get('marketDefinition', {})
                    event_name = market_def.get('eventName', 'Unknown')
                    
                    # Skip test matches
                    if 'Test' in event_name:
                        os.remove(file_path)
                        continue
                    
                    # Extract date from file path
                    path_parts = file_path.split('/')
                    if len(path_parts) >= 4:
                        year = path_parts[1]
                        month = path_parts[2]
                        day = path_parts[3]
                        event_id = path_parts[4] if len(path_parts) > 4 else 'unknown'
                        
                        # Identify league
                        league = identify_league_from_match(event_name)
                        
                        # Find final odds
                        final_over_odds = None
                        final_under_odds = None
                        
                        # Go through lines in reverse to find the last odds
                        for line in reversed(lines[1:]):
                            try:
                                data = json.loads(line)
                                
                                if 'mc' in data and len(data['mc']) > 0:
                                    mc_data = data['mc'][0]
                                    
                                    if 'rc' in mc_data:
                                        rc_data = mc_data['rc']
                                        
                                        if isinstance(rc_data, list):
                                            for runner in rc_data:
                                                runner_id = runner.get('id')
                                                odds = runner.get('ltp')
                                                
                                                if runner_id == 5851483 and odds:  # Over 0.5 Goals
                                                    final_over_odds = odds
                                                elif runner_id == 5851482 and odds:  # Under 0.5 Goals
                                                    final_under_odds = odds
                                        elif isinstance(rc_data, dict):
                                            for runner_id, runner_data in rc_data.items():
                                                odds = runner_data.get('ltp')
                                                
                                                if runner_id == '5851483' and odds:  # Over 0.5 Goals
                                                    final_over_odds = odds
                                                elif runner_id == '5851482' and odds:  # Under 0.5 Goals
                                                    final_under_odds = odds
                                        
                                        # If we found both odds, we're done
                                        if final_over_odds and final_under_odds:
                                            break
                            
                            except json.JSONDecodeError:
                                continue
                        
                        # Store match data if we have odds
                        if final_under_odds:
                            match_info = {
                                'event_name': event_name,
                                'league': league,
                                'country': 'England',
                                'over_05_odds': final_over_odds,
                                'under_05_odds': final_under_odds,
                                'file_path': file_path,
                                'event_id': event_id,
                                'market_time': market_def.get('marketTime'),
                                'status': market_def.get('status'),
                                'year': year,
                                'month': month,
                                'day': day,
                                'date_str': f"{year}-{month}-{day}"
                            }
                            
                            all_matches.append(match_info)
                            league_counts[league] += 1
            
            # Clean up
            os.remove(file_path)
            
        except Exception as e:
            if i < 10:  # Only print first few errors
                print(f"Error processing {file_path}: {e}")
            continue
    
    print(f"\nFound {len(all_matches)} matches with odds data")
    print("League distribution:")
    for league, count in sorted(league_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {league}: {count} matches")
    
    return all_matches

def identify_league_from_match(event_name):
    """Enhanced league identification"""
    if not event_name or event_name == 'Unknown':
        return None
    
    # Premier League teams (expanded list)
    premier_league_teams = [
        'Manchester', 'Arsenal', 'Chelsea', 'Liverpool', 'Tottenham', 'Newcastle',
        'Leicester', 'Southampton', 'Brighton', 'Aston Villa', 'West Ham', 'Brentford',
        'Crystal Palace', 'Everton', 'Fulham', 'Wolves', 'Nottingham Forest', 'Bournemouth',
        'Ipswich', 'Luton', 'Sheffield', 'Man Utd', 'Man City', 'Nottm Forest',
        'Man United', 'Manchester United', 'Manchester City', 'Nottingham', 'Forest'
    ]
    
    # Championship teams
    championship_teams = [
        'Middlesbrough', 'Swansea', 'Millwall', 'Watford', 'Hull', 'Bristol City',
        'Norwich', 'Leeds', 'Sheffield Wednesday', 'Birmingham', 'Blackburn', 'Burnley',
        'Cardiff', 'Coventry', 'Huddersfield', 'Ipswich', 'Leicester', 'Preston',
        'QPR', 'Reading', 'Stoke', 'Sunderland', 'West Brom', 'Wigan'
    ]
    
    # League One teams
    league_one_teams = [
        'Wrexham', 'Reading', 'Crawley', 'Barnsley', 'Bolton', 'Bristol Rovers',
        'Charlton', 'Derby', 'Exeter', 'Fleetwood', 'Leyton Orient', 'Lincoln',
        'Northampton', 'Oxford', 'Peterborough', 'Portsmouth', 'Port Vale',
        'Shrewsbury', 'Stevenage', 'Wycombe'
    ]
    
    # League Two teams (expanded)
    league_two_teams = [
        'AFC Wimbledon', 'Colchester', 'Gillingham', 'Chesterfield', 'Swindon',
        'Grimsby', 'Bradford', 'Accrington', 'Fleetwood', 'Stockport', 'Barrow',
        'Crawley', 'Doncaster', 'Harrogate', 'Mansfield', 'Morecambe', 'Newport',
        'Salford', 'Sutton', 'Tranmere', 'Walsall', 'Wrexham', 'Wycombe', 'MK Dons'
    ]
    
    # National League teams
    national_league_teams = [
        'Oldham', 'AFC Fylde', 'Barnet', 'Forest Green', 'Eastleigh', 'Solihull Moors',
        'Gateshead', 'Yeovil Town', 'Sutton Utd', 'York', 'Altrincham'
    ]
    
    event_lower = event_name.lower()
    
    # Check leagues in order of preference
    for team in premier_league_teams:
        if team.lower() in event_lower:
            return 'Premier League'
    
    for team in championship_teams:
        if team.lower() in event_lower:
            return 'Championship'
    
    for team in league_one_teams:
        if team.lower() in event_lower:
            return 'League One'
    
    for team in league_two_teams:
        if team.lower() in event_lower:
            return 'League Two'
    
    for team in national_league_teams:
        if team.lower() in event_lower:
            return 'National League'
    
    return 'Other'

def load_predicted_data():
    """Load all predicted data"""
    print("Loading predicted data...")
    
    try:
        df = pd.read_csv('comprehensive_backtest_full_all_results.csv')
        
        # Filter for English leagues
        english_leagues = ['Premier League', 'Championship', 'League One', 'League Two', 'National League']
        english_data = df[df['league_name'].isin(english_leagues)].copy()
        
        print(f"Found {len(df)} total predicted bets")
        print(f"Found {len(english_data)} English league bets")
        
        # Show breakdown by league
        league_breakdown = english_data['league_name'].value_counts()
        print("English league breakdown:")
        for league, count in league_breakdown.items():
            print(f"  {league}: {count} bets")
        
        return english_data
        
    except Exception as e:
        print(f"Error loading predicted data: {e}")
        return pd.DataFrame()

def improved_matching(predictions_df, odds_data):
    """Improved matching algorithm with multiple strategies"""
    print("Matching predictions with odds using improved algorithm...")
    
    matched_data = []
    
    for _, prediction in predictions_df.iterrows():
        home_team = prediction['home_team']
        away_team = prediction['away_team']
        league = prediction['league_name']
        match_date = prediction['match_date']
        
        # Extract date from match_date
        try:
            pred_date = pd.to_datetime(match_date).date()
        except:
            continue
        
        # Try multiple matching strategies
        matched = False
        
        # Strategy 1: Exact team name match
        for odds_match in odds_data:
            if (league == odds_match['league'] and
                home_team.lower() in odds_match['event_name'].lower() and 
                away_team.lower() in odds_match['event_name'].lower()):
                
                matched_data.append(create_match_record(prediction, odds_match))
                matched = True
                break
        
        if matched:
            continue
            
        # Strategy 2: Partial team name match (handle abbreviations)
        for odds_match in odds_data:
            if league == odds_match['league']:
                event_lower = odds_match['event_name'].lower()
                
                # Handle common abbreviations and variations
                home_variations = get_team_variations(home_team)
                away_variations = get_team_variations(away_team)
                
                home_match = any(var.lower() in event_lower for var in home_variations)
                away_match = any(var.lower() in event_lower for var in away_variations)
                
                if home_match and away_match:
                    matched_data.append(create_match_record(prediction, odds_match))
                    matched = True
                    break
        
        if matched:
            continue
            
        # Strategy 3: Date-based matching (if we can extract dates from odds data)
        # This would require more sophisticated date parsing from the odds data
    
    print(f"Matched {len(matched_data)} predictions with odds")
    return pd.DataFrame(matched_data)

def get_team_variations(team_name):
    """Get common variations of team names"""
    variations = [team_name]
    
    # Common abbreviations
    if 'Manchester' in team_name:
        variations.extend(['Man Utd', 'Man United', 'Man City', 'Manchester United', 'Manchester City'])
    if 'Nottingham' in team_name:
        variations.extend(['Nottm Forest', 'Nottingham Forest'])
    if 'Crystal Palace' in team_name:
        variations.extend(['Palace'])
    if 'Aston Villa' in team_name:
        variations.extend(['Villa'])
    if 'West Ham' in team_name:
        variations.extend(['Hammers'])
    
    return variations

def create_match_record(prediction, odds_match):
    """Create a matched record"""
    under_odds = odds_match['under_05_odds']
    
    # Calculate PnL using correct lay betting formula
    if prediction['prediction_correct']:
        # Goal scored - we win the lay bet
        correct_pnl = 98.0  # $100 minus 2% commission
    else:
        # 0-0 at half-time - we lose the lay bet
        correct_pnl = -100 * (under_odds - 1)
    
    return {
        'fixture_id': prediction['fixture_id'],
        'league_name': prediction['league_name'],
        'country': prediction['country'],
        'home_team': prediction['home_team'],
        'away_team': prediction['away_team'],
        'match_date': prediction['match_date'],
        'predicted_combined_avg': prediction['combined_avg'],
        'prediction_correct': prediction['prediction_correct'],
        'actual_first_half_goals': prediction['actual_first_half_goals'],
        'original_pnl': prediction['pnl'],
        'under_odds': under_odds,
        'over_odds': odds_match['over_05_odds'],
        'correct_pnl': correct_pnl,
        'stake': 100,
        'odds_event_name': odds_match['event_name']
    }

def main():
    print("=== IMPROVED MATCH ANALYSIS ===")
    
    # Extract all odds data
    all_odds = extract_all_odds_data()
    
    # Load predicted data
    predictions_df = load_predicted_data()
    
    if predictions_df.empty:
        print("No predicted data found")
        return
    
    # Improved matching
    matched_df = improved_matching(predictions_df, all_odds)
    
    if matched_df.empty:
        print("No matches found")
        return
    
    # Calculate summary statistics
    total_bets = len(matched_df)
    correct_predictions = matched_df['prediction_correct'].sum()
    accuracy = correct_predictions / total_bets * 100
    
    total_original_pnl = matched_df['original_pnl'].sum()
    total_correct_pnl = matched_df['correct_pnl'].sum()
    
    original_roi = (total_original_pnl / (total_bets * 100)) * 100
    correct_roi = (total_correct_pnl / (total_bets * 100)) * 100
    
    print(f"\n=== IMPROVED RESULTS ===")
    print(f"Total Matched Bets: {total_bets}")
    print(f"Accuracy: {accuracy:.1f}%")
    print(f"Original PnL: ${total_original_pnl:,.2f}")
    print(f"Correct PnL: ${total_correct_pnl:,.2f}")
    print(f"Original ROI: {original_roi:.1f}%")
    print(f"Correct ROI: {correct_roi:.1f}%")
    
    # By league breakdown
    print(f"\n=== BY LEAGUE ===")
    league_stats = matched_df.groupby('league_name').agg({
        'prediction_correct': ['count', 'sum'],
        'original_pnl': 'sum',
        'correct_pnl': 'sum',
        'stake': 'sum'
    }).round(2)
    
    league_stats.columns = ['total_bets', 'correct_predictions', 'original_pnl', 'correct_pnl', 'total_stake']
    league_stats['accuracy'] = (league_stats['correct_predictions'] / league_stats['total_bets'] * 100).round(1)
    league_stats['original_roi'] = (league_stats['original_pnl'] / league_stats['total_stake'] * 100).round(1)
    league_stats['correct_roi'] = (league_stats['correct_pnl'] / league_stats['total_stake'] * 100).round(1)
    
    print(league_stats.to_string())
    
    # Save results
    matched_df.to_csv('improved_matched_results.csv', index=False)
    print(f"\nDetailed results saved to improved_matched_results.csv")
    
    # Show sample matches
    print(f"\n=== SAMPLE MATCHES ===")
    sample = matched_df[['home_team', 'away_team', 'league_name', 'prediction_correct', 
                        'correct_pnl', 'under_odds', 'odds_event_name']].head(15)
    print(sample.to_string(index=False))

if __name__ == "__main__":
    main()
