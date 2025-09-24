#!/usr/bin/env python3
"""
Comprehensive match finder using multiple data sources:
1. ENP_2024-2025_M.xlsx (Excel data)
2. GB_24_25.tar (Betfair odds data)
3. comprehensive_backtest_full_all_results.csv (Predictions)
"""

import pandas as pd
import tarfile
import bz2
import json
import re
from datetime import datetime
from fuzzywuzzy import fuzz, process

# Runner IDs for "Under 0.5 Goals" and "Over 0.5 Goals"
UNDER_05_GOALS_RUNNER_ID = 5851482
OVER_05_GOALS_RUNNER_ID = 5851483

def load_excel_data():
    """Load and process Excel data"""
    print("Loading Excel data...")
    excel_file = '/Users/seijimatsuda/first_half_model/data/ENP_2024-2025_M.xlsx'
    
    # Read the FM Data sheet
    df = pd.read_excel(excel_file, sheet_name='FM Data')
    
    # Clean and process the data
    excel_matches = []
    for _, row in df.iterrows():
        if pd.notna(row['Home Team']) and pd.notna(row['Away Team']):
            # Clean team names
            home_team = str(row['Home Team']).strip()
            away_team = str(row['Away Team']).strip()
            
            # Create match identifier
            match_id = f"{home_team} v {away_team}"
            
            excel_matches.append({
                'match_id': match_id,
                'home_team': home_team,
                'away_team': away_team,
                'date': row['Date'],
                'ht_goals': row.get('HT Goals', 0),
                'avg_t1_goals': row.get('AVG T1 Goals', 0),
                'avg_t2_goals': row.get('AVG T2 Goals', 0),
                'prediction': row.get('Prediction', ''),
                'source': 'excel'
            })
    
    print(f"Loaded {len(excel_matches)} matches from Excel")
    return excel_matches

def load_predictions_data():
    """Load prediction data from comprehensive results"""
    print("Loading predictions data...")
    df = pd.read_csv('comprehensive_backtest_full_all_results.csv')
    
    # Filter for English leagues
    english_leagues = ['Premier League', 'Championship', 'League One', 'League Two', 'National League']
    english_data = df[df['league_name'].isin(english_leagues)].copy()
    
    predictions = []
    for _, row in english_data.iterrows():
        match_id = f"{row['home_team']} v {row['away_team']}"
        predictions.append({
            'match_id': match_id,
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'league_name': row['league_name'],
            'match_date': row['match_date'],
            'combined_avg': row['combined_avg'],
            'prediction_correct': row['prediction_correct'],
            'pnl': row['pnl'],
            'stake': 100.0,
            'source': 'predictions'
        })
    
    print(f"Loaded {len(predictions)} predictions")
    return predictions

def extract_betfair_odds(tar_path, max_files=None):
    """Extract odds data from Betfair tar file"""
    print("Extracting Betfair odds data...")
    odds_data = {}
    file_count = 0
    
    with tarfile.open(tar_path, "r") as tar:
        bz2_files = [m for m in tar.getmembers() if m.name.endswith('.bz2')]
        
        for i, member in enumerate(bz2_files):
            if max_files and i >= max_files:
                break
                
            file_count += 1
            if file_count % 1000 == 0:
                print(f"Processing file {file_count}/{len(bz2_files)}")
            
            try:
                extracted_bz2 = tar.extractfile(member)
                if extracted_bz2:
                    decompressed_data = bz2.decompress(extracted_bz2.read()).decode('utf-8')
                    lines = decompressed_data.strip().split('\n')
                    
                    event_name = None
                    final_under_odds = None
                    final_over_odds = None
                    
                    # Get event name from first line
                    if lines:
                        first_line_data = json.loads(lines[0])
                        if 'mc' in first_line_data and first_line_data['mc']:
                            market_definition = first_line_data['mc'][0].get('marketDefinition')
                            if market_definition:
                                event_name = market_definition.get('eventName')
                    
                    if event_name:
                        # Find final odds from last lines
                        for line in reversed(lines):
                            data = json.loads(line)
                            if 'mc' in data and data['mc']:
                                for market_change in data['mc']:
                                    if 'rc' in market_change:
                                        for runner_change in market_change['rc']:
                                            if runner_change.get('id') == UNDER_05_GOALS_RUNNER_ID and 'ltp' in runner_change:
                                                final_under_odds = runner_change['ltp']
                                            if runner_change.get('id') == OVER_05_GOALS_RUNNER_ID and 'ltp' in runner_change:
                                                final_over_odds = runner_change['ltp']
                                        if final_under_odds and final_over_odds:
                                            break
                                if final_under_odds and final_over_odds:
                                    break
                    
                    if event_name and final_under_odds and final_over_odds:
                        odds_data[event_name] = {
                            'under_05_odds': final_under_odds,
                            'over_05_odds': final_over_odds
                        }
                        
            except Exception as e:
                pass
    
    print(f"Extracted odds for {len(odds_data)} matches from Betfair")
    return odds_data

def normalize_team_name(team_name):
    """Normalize team names for better matching"""
    if pd.isna(team_name):
        return ""
    
    team_name = str(team_name).strip()
    
    # Common name mappings
    name_mappings = {
        'Manchester United': 'Man Utd',
        'Manchester City': 'Man City',
        'Tottenham Hotspur': 'Tottenham',
        'West Ham United': 'West Ham',
        'Brighton & Hove Albion': 'Brighton',
        'Nottingham Forest': 'Nottm Forest',
        'Leicester City': 'Leicester',
        'Aston Villa': 'Aston Villa',
        'Crystal Palace': 'Crystal Palace',
        'Wolverhampton Wanderers': 'Wolves',
        'Newcastle United': 'Newcastle',
        'Sheffield United': 'Sheffield Utd',
        'Luton Town': 'Luton'
    }
    
    return name_mappings.get(team_name, team_name)

def find_matches_with_fuzzy_matching(predictions, odds_data, excel_matches):
    """Find matches using fuzzy string matching across all data sources"""
    print("Finding matches using fuzzy matching...")
    
    matched_results = []
    
    # Create a comprehensive list of all possible matches
    all_matches = []
    
    # Add predictions
    for pred in predictions:
        all_matches.append({
            'match_id': pred['match_id'],
            'home_team': pred['home_team'],
            'away_team': pred['away_team'],
            'league_name': pred.get('league_name', 'Unknown'),
            'match_date': pred.get('match_date', ''),
            'combined_avg': pred.get('combined_avg', 0),
            'prediction_correct': pred.get('prediction_correct', False),
            'pnl': pred.get('pnl', 0),
            'stake': pred.get('stake', 100),
            'source': 'prediction'
        })
    
    # Add Excel matches
    for excel_match in excel_matches:
        all_matches.append({
            'match_id': excel_match['match_id'],
            'home_team': excel_match['home_team'],
            'away_team': excel_match['away_team'],
            'league_name': 'Premier League',  # Excel data appears to be Premier League
            'match_date': excel_match.get('date', ''),
            'combined_avg': (excel_match.get('avg_t1_goals', 0) + excel_match.get('avg_t2_goals', 0)),
            'prediction_correct': excel_match.get('ht_goals', 0) > 0,  # Goal scored in first half
            'pnl': 0,  # Will calculate based on odds
            'stake': 100,
            'source': 'excel'
        })
    
    # Now try to match with odds data
    for match in all_matches:
        best_match = None
        best_score = 0
        
        # Try exact match first
        if match['match_id'] in odds_data:
            best_match = match['match_id']
            best_score = 100
        else:
            # Try fuzzy matching
            for odds_match_id in odds_data.keys():
                # Try different variations of the match ID
                variations = [
                    match['match_id'],
                    f"{normalize_team_name(match['home_team'])} v {normalize_team_name(match['away_team'])}",
                    f"{match['home_team']} vs {match['away_team']}",
                    f"{normalize_team_name(match['home_team'])} vs {normalize_team_name(match['away_team'])}"
                ]
                
                for variation in variations:
                    score = fuzz.ratio(variation.lower(), odds_match_id.lower())
                    if score > best_score and score > 70:  # Minimum threshold
                        best_score = score
                        best_match = odds_match_id
        
        if best_match and best_match in odds_data:
            odds = odds_data[best_match]
            
            # Calculate lay betting PnL
            stake = 100
            commission_rate = 0.02
            
            if match['prediction_correct']:  # Goal scored (we lose the lay bet)
                actual_pnl = -stake * (odds['under_05_odds'] - 1)
            else:  # 0-0 (we win the lay bet)
                actual_pnl = stake * (1 - commission_rate)
            
            matched_results.append({
                'match_id': match['match_id'],
                'odds_match_id': best_match,
                'match_score': best_score,
                'home_team': match['home_team'],
                'away_team': match['away_team'],
                'league_name': match['league_name'],
                'match_date': match['match_date'],
                'combined_avg': match['combined_avg'],
                'prediction_correct': match['prediction_correct'],
                'original_pnl': match['pnl'],
                'actual_pnl': actual_pnl,
                'under_05_odds': odds['under_05_odds'],
                'over_05_odds': odds['over_05_odds'],
                'stake': stake,
                'source': match['source']
            })
    
    print(f"Found {len(matched_results)} matches with odds data")
    return matched_results

def main():
    print("=== Comprehensive Match Finder ===")
    
    # Load all data sources
    excel_matches = load_excel_data()
    predictions = load_predictions_data()
    
    # Extract odds data (limit to first 5000 files for speed)
    tar_path = '/Users/seijimatsuda/first_half_model/data/GB_24_25.tar'
    odds_data = extract_betfair_odds(tar_path, max_files=5000)
    
    # Find matches
    matched_results = find_matches_with_fuzzy_matching(predictions, odds_data, excel_matches)
    
    if matched_results:
        # Create DataFrame and analyze results
        df = pd.DataFrame(matched_results)
        
        # Calculate summary statistics
        total_bets = len(df)
        total_stake = df['stake'].sum()
        total_original_pnl = df['original_pnl'].sum()
        total_actual_pnl = df['actual_pnl'].sum()
        
        accuracy = (df['prediction_correct'].sum() / total_bets) * 100 if total_bets > 0 else 0
        original_roi = (total_original_pnl / total_stake) * 100 if total_stake > 0 else 0
        actual_roi = (total_actual_pnl / total_stake) * 100 if total_stake > 0 else 0
        
        print(f"\n=== COMPREHENSIVE RESULTS ===")
        print(f"Total Matches Found: {total_bets}")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"Original PnL: ${total_original_pnl:,.2f}")
        print(f"Actual PnL: ${total_actual_pnl:,.2f}")
        print(f"Original ROI: {original_roi:.1f}%")
        print(f"Actual ROI: {actual_roi:.1f}%")
        
        # Show results by source
        print(f"\n=== BY DATA SOURCE ===")
        source_summary = df.groupby('source').agg({
            'stake': 'count',
            'actual_pnl': 'sum',
            'prediction_correct': 'sum'
        }).reset_index()
        source_summary.columns = ['Source', 'Bets', 'Total_PnL', 'Correct_Predictions']
        source_summary['Accuracy'] = (source_summary['Correct_Predictions'] / source_summary['Bets'] * 100).round(1)
        source_summary['ROI'] = (source_summary['Total_PnL'] / (source_summary['Bets'] * 100) * 100).round(1)
        print(source_summary.to_string(index=False))
        
        # Show sample matches
        print(f"\n=== SAMPLE MATCHES ===")
        sample_df = df.head(10)[['match_id', 'odds_match_id', 'match_score', 'prediction_correct', 'actual_pnl', 'under_05_odds']]
        print(sample_df.to_string(index=False))
        
        # Save results
        df.to_csv('comprehensive_matched_results.csv', index=False)
        print(f"\nResults saved to comprehensive_matched_results.csv")
        
    else:
        print("No matches found between predictions and odds data")

if __name__ == "__main__":
    main()
