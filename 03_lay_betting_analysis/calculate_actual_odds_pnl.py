#!/usr/bin/env python3
"""
Script to calculate ROI and PnL using actual odds from GB_24_25.tar data
"""

import json
import subprocess
import pandas as pd
from collections import defaultdict
import bz2
import os
import re
from datetime import datetime

def extract_actual_odds_data():
    """Extract actual odds data from GB_24_25.tar for overlapping leagues"""
    print("Extracting actual odds data from GB_24_25.tar...")
    
    # Get list of files in the tar
    result = subprocess.run(['tar', '-tf', 'data/GB_24_25.tar'], 
                          capture_output=True, text=True, cwd='/Users/seijimatsuda/first_half_model')
    
    files = [f for f in result.stdout.strip().split('\n') if f.endswith('.bz2')]
    print(f"Found {len(files)} bz2 files")
    
    matches_data = []
    leagues_processed = set()
    
    # Process all files to find matches from overlapping leagues
    for i, file_path in enumerate(files):
        if i % 500 == 0:
            print(f"Processing file {i+1}/{len(files)}")
            
        try:
            # Extract file
            subprocess.run(['tar', '-xf', 'data/GB_24_25.tar', file_path], 
                         cwd='/Users/seijimatsuda/first_half_model', 
                         capture_output=True)
            
            # Read and parse JSON
            with bz2.open(file_path, 'rt') as f:
                lines = f.readlines()
                
                # Get market definition from first line
                if lines:
                    first_data = json.loads(lines[0])
                    
                    if 'mc' in first_data and len(first_data['mc']) > 0:
                        market_def = first_data['mc'][0].get('marketDefinition', {})
                        event_name = market_def.get('eventName', 'Unknown')
                        
                        # Check if this is from an overlapping league
                        league = identify_league_from_match(event_name)
                        if league and league in ['Premier League', 'League Two']:
                            
                            # Extract odds from the last line (final odds)
                            if len(lines) > 1:
                                last_data = json.loads(lines[-1])
                                
                                if 'mc' in last_data and len(last_data['mc']) > 0:
                                    market_data = last_data['mc'][0]
                                    
                                    # Extract odds for Over 0.5 Goals
                                    if 'rc' in market_data:
                                        runners = market_data['rc']
                                        
                                        for runner_id, runner_data in runners.items():
                                            if runner_data.get('ltp'):  # Last traded price
                                                runner_info = market_def.get('runners', [])
                                                for runner in runner_info:
                                                    if str(runner.get('id')) == runner_id:
                                                        runner_name = runner.get('name', '')
                                                        
                                                        if 'Over 0.5 Goals' in runner_name:
                                                            odds = float(runner_data['ltp'])
                                                            
                                                            match_info = {
                                                                'event_name': event_name,
                                                                'league': league,
                                                                'country': 'England',
                                                                'market_type': 'FIRST_HALF_GOALS_05',
                                                                'over_05_odds': odds,
                                                                'file_path': file_path,
                                                                'event_id': market_def.get('eventId'),
                                                                'market_time': market_def.get('marketTime'),
                                                                'status': market_def.get('status')
                                                            }
                                                            
                                                            matches_data.append(match_info)
                                                            leagues_processed.add(league)
                                                            break
            
            # Clean up extracted file
            os.remove(file_path)
            
        except Exception as e:
            if i < 10:  # Only print first few errors
                print(f"Error processing {file_path}: {e}")
            continue
    
    print(f"Found {len(matches_data)} matches with odds data")
    print(f"Leagues processed: {leagues_processed}")
    
    return matches_data

def identify_league_from_match(event_name):
    """Identify league from match event name"""
    if not event_name or event_name == 'Unknown' or 'Test' in event_name:
        return None
    
    # Premier League teams
    premier_league_teams = [
        'Manchester', 'Arsenal', 'Chelsea', 'Liverpool', 'Tottenham', 'Newcastle',
        'Leicester', 'Southampton', 'Brighton', 'Aston Villa', 'West Ham', 'Brentford',
        'Crystal Palace', 'Everton', 'Fulham', 'Wolves', 'Nottingham Forest', 'Bournemouth',
        'Ipswich', 'Luton', 'Sheffield'
    ]
    
    # League Two teams
    league_two_teams = [
        'AFC Wimbledon', 'Colchester', 'Gillingham', 'Chesterfield', 'Swindon',
        'Grimsby', 'Bradford', 'Accrington', 'Fleetwood', 'Stockport', 'Barrow',
        'Crawley', 'Doncaster', 'Harrogate', 'Mansfield', 'Morecambe', 'Newport',
        'Salford', 'Sutton', 'Tranmere', 'Walsall', 'Wrexham', 'Wycombe'
    ]
    
    event_lower = event_name.lower()
    
    for team in premier_league_teams:
        if team.lower() in event_lower:
            return 'Premier League'
    
    for team in league_two_teams:
        if team.lower() in event_lower:
            return 'League Two'
    
    return None

def load_predicted_data():
    """Load the predicted data from comprehensive analysis"""
    print("Loading predicted data...")
    
    try:
        # Read the detailed results
        df = pd.read_csv('comprehensive_backtest_full_all_results.csv')
        
        # Filter for overlapping leagues
        overlapping_leagues = ['Premier League', 'League Two']
        overlapping_data = df[df['league_name'].isin(overlapping_leagues)].copy()
        
        print(f"Found {len(overlapping_data)} predicted bets from overlapping leagues")
        
        return overlapping_data
        
    except Exception as e:
        print(f"Error loading predicted data: {e}")
        return pd.DataFrame()

def match_predictions_with_odds(predictions_df, odds_data):
    """Match predictions with actual odds data"""
    print("Matching predictions with actual odds...")
    
    matched_data = []
    
    for _, prediction in predictions_df.iterrows():
        # Extract date from match_date
        try:
            match_date = pd.to_datetime(prediction['match_date']).date()
        except:
            continue
        
        # Find matching odds data
        for odds_match in odds_data:
            if (prediction['home_team'] in odds_match['event_name'] and 
                prediction['away_team'] in odds_match['event_name'] and
                prediction['league_name'] == odds_match['league']):
                
                # Calculate PnL with actual odds
                actual_odds = odds_match['over_05_odds']
                
                # Calculate lay odds (betting against Over 0.5)
                lay_odds = (actual_odds - 1) / actual_odds + 1
                
                # Calculate PnL based on prediction
                if prediction['prediction_correct']:
                    # Win: lay bet wins, we keep the liability
                    pnl = 100 * (lay_odds - 1) - 2  # 2% commission
                else:
                    # Loss: lay bet loses, we pay out
                    pnl = -100 * (actual_odds - 1) - 2  # 2% commission
                
                matched_info = {
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
                    'actual_odds': actual_odds,
                    'lay_odds': lay_odds,
                    'actual_pnl': pnl,
                    'stake': 100
                }
                
                matched_data.append(matched_info)
                break
    
    print(f"Matched {len(matched_data)} predictions with actual odds")
    
    return pd.DataFrame(matched_data)

def calculate_summary_stats(matched_df):
    """Calculate summary statistics for actual odds PnL"""
    if matched_df.empty:
        return {}
    
    # Overall stats
    total_bets = len(matched_df)
    correct_predictions = matched_df['prediction_correct'].sum()
    accuracy = correct_predictions / total_bets * 100
    
    total_original_pnl = matched_df['original_pnl'].sum()
    total_actual_pnl = matched_df['actual_pnl'].sum()
    
    original_roi = (total_original_pnl / (total_bets * 100)) * 100
    actual_roi = (total_actual_pnl / (total_bets * 100)) * 100
    
    # By league
    league_stats = matched_df.groupby('league_name').agg({
        'prediction_correct': ['count', 'sum'],
        'original_pnl': 'sum',
        'actual_pnl': 'sum',
        'stake': 'sum'
    }).round(2)
    
    league_stats.columns = ['total_bets', 'correct_predictions', 'original_pnl', 'actual_pnl', 'total_stake']
    league_stats['accuracy'] = (league_stats['correct_predictions'] / league_stats['total_bets'] * 100).round(1)
    league_stats['original_roi'] = (league_stats['original_pnl'] / league_stats['total_stake'] * 100).round(1)
    league_stats['actual_roi'] = (league_stats['actual_pnl'] / league_stats['total_stake'] * 100).round(1)
    
    return {
        'overall': {
            'total_bets': total_bets,
            'accuracy': round(accuracy, 1),
            'original_pnl': round(total_original_pnl, 2),
            'actual_pnl': round(total_actual_pnl, 2),
            'original_roi': round(original_roi, 1),
            'actual_roi': round(actual_roi, 1)
        },
        'by_league': league_stats
    }

def main():
    print("=== Actual Odds PnL Calculation ===")
    
    # Extract actual odds data
    odds_data = extract_actual_odds_data()
    
    if not odds_data:
        print("No odds data found")
        return
    
    # Load predicted data
    predictions_df = load_predicted_data()
    
    if predictions_df.empty:
        print("No predicted data found")
        return
    
    # Match predictions with actual odds
    matched_df = match_predictions_with_odds(predictions_df, odds_data)
    
    if matched_df.empty:
        print("No matches found between predictions and odds data")
        return
    
    # Calculate summary statistics
    stats = calculate_summary_stats(matched_df)
    
    print(f"\n=== RESULTS WITH ACTUAL ODDS ===")
    print(f"Total Bets: {stats['overall']['total_bets']}")
    print(f"Accuracy: {stats['overall']['accuracy']}%")
    print(f"Original PnL: ${stats['overall']['original_pnl']:,.2f}")
    print(f"Actual PnL: ${stats['overall']['actual_pnl']:,.2f}")
    print(f"Original ROI: {stats['overall']['original_roi']}%")
    print(f"Actual ROI: {stats['overall']['actual_roi']}%")
    
    print(f"\n=== BY LEAGUE ===")
    print(stats['by_league'].to_string())
    
    # Save results
    matched_df.to_csv('actual_odds_pnl_results.csv', index=False)
    print(f"\nDetailed results saved to actual_odds_pnl_results.csv")
    
    # Show sample of matches
    print(f"\n=== SAMPLE MATCHES ===")
    sample = matched_df[['home_team', 'away_team', 'league_name', 'prediction_correct', 
                        'original_pnl', 'actual_pnl', 'actual_odds']].head(10)
    print(sample.to_string(index=False))

if __name__ == "__main__":
    main()
