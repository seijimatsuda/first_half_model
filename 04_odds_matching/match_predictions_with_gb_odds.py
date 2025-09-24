#!/usr/bin/env python3
"""
Match predictions with GB_24_25.tar odds data
"""

import pandas as pd
import tarfile
import bz2
import json
from fuzzywuzzy import fuzz

# Runner IDs for "Under 0.5 Goals" and "Over 0.5 Goals" in FIRST_HALF_GOALS_05 market
UNDER_05_GOALS_RUNNER_ID = 5851482
OVER_05_GOALS_RUNNER_ID = 5851483

def load_predictions():
    """Load the predictions from comprehensive results"""
    print("Loading predictions...")
    df = pd.read_csv('comprehensive_backtest_full_all_results.csv')
    
    # Filter for Great Britain leagues
    gb_leagues = ['Premier League', 'Championship', 'League One', 'League Two', 'National League']
    gb_predictions = df[df['league_name'].isin(gb_leagues)].copy()
    
    print(f"Found {len(gb_predictions)} GB predictions")
    return gb_predictions

def load_gb_matches():
    """Load the GB matches from the CSV we just created"""
    print("Loading GB matches...")
    df = pd.read_csv('gb_24_25_all_matches.csv')
    
    # Filter for matches with odds
    df_with_odds = df[(df['under_05_odds'].notna()) & (df['over_05_odds'].notna())]
    
    print(f"Found {len(df_with_odds)} GB matches with odds")
    return df_with_odds

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
        'Sheffield United': 'Sheff Utd',
        'Sheffield Wednesday': 'Sheff Wed',
        'Luton Town': 'Luton'
    }
    
    return name_mappings.get(team_name, team_name)

def find_matches(predictions_df, gb_matches_df):
    """Find matches between predictions and GB odds data"""
    print("Finding matches between predictions and GB odds...")
    
    matched_results = []
    
    for _, pred in predictions_df.iterrows():
        pred_match_id = f"{pred['home_team']} v {pred['away_team']}"
        best_match = None
        best_score = 0
        
        # Try exact match first
        if pred_match_id in gb_matches_df['event_name'].values:
            best_match = gb_matches_df[gb_matches_df['event_name'] == pred_match_id].iloc[0]
            best_score = 100
        else:
            # Try fuzzy matching with different variations
            variations = [
                pred_match_id,
                f"{normalize_team_name(pred['home_team'])} v {normalize_team_name(pred['away_team'])}",
                f"{pred['home_team']} vs {pred['away_team']}",
                f"{normalize_team_name(pred['home_team'])} vs {normalize_team_name(pred['away_team'])}"
            ]
            
            for variation in variations:
                for _, gb_match in gb_matches_df.iterrows():
                    score = fuzz.ratio(variation.lower(), gb_match['event_name'].lower())
                    if score > best_score and score > 70:  # Minimum threshold
                        best_score = score
                        best_match = gb_match
        
        if best_match is not None and best_score > 70:
            # Calculate lay betting PnL with commission
            stake = 100
            commission_rate = 0.02
            
            if pred['prediction_correct']:  # Goal scored - we win the lay bet
                actual_pnl = stake * (1 - commission_rate)  # +$98 profit after commission
            else:  # 0-0 at half-time - we lose the lay bet
                actual_pnl = -stake * (best_match['under_05_odds'] - 1)
            
            matched_results.append({
                'prediction_match_id': pred_match_id,
                'gb_match_id': best_match['event_name'],
                'match_score': best_score,
                'home_team': pred['home_team'],
                'away_team': pred['away_team'],
                'league_name': pred['league_name'],
                'match_date': pred['match_date'],
                'combined_avg': pred['combined_avg'],
                'prediction_correct': pred['prediction_correct'],
                'original_pnl': pred['pnl'],
                'actual_pnl': actual_pnl,
                'under_05_odds': best_match['under_05_odds'],
                'over_05_odds': best_match['over_05_odds'],
                'stake': stake
            })
    
    print(f"Found {len(matched_results)} matches between predictions and GB odds")
    return matched_results

def main():
    print("=== MATCHING PREDICTIONS WITH GB ODDS ===")
    
    # Load data
    predictions_df = load_predictions()
    gb_matches_df = load_gb_matches()
    
    # Find matches
    matched_results = find_matches(predictions_df, gb_matches_df)
    
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
        
        print(f"\n=== MATCHED RESULTS ===")
        print(f"Total Matches Found: {total_bets}")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"Original PnL: ${total_original_pnl:,.2f}")
        print(f"Actual PnL: ${total_actual_pnl:,.2f}")
        print(f"Original ROI: {original_roi:.1f}%")
        print(f"Actual ROI: {actual_roi:.1f}%")
        
        # Show results by league
        print(f"\n=== BY LEAGUE ===")
        league_summary = df.groupby('league_name').agg({
            'stake': 'count',
            'actual_pnl': 'sum',
            'prediction_correct': 'sum'
        }).reset_index()
        league_summary.columns = ['League', 'Bets', 'Total_PnL', 'Correct_Predictions']
        league_summary['Accuracy'] = (league_summary['Correct_Predictions'] / league_summary['Bets'] * 100).round(1)
        league_summary['ROI'] = (league_summary['Total_PnL'] / (league_summary['Bets'] * 100) * 100).round(1)
        print(league_summary.to_string(index=False))
        
        # Show sample matches
        print(f"\n=== SAMPLE MATCHES ===")
        sample_df = df.head(15)[['prediction_match_id', 'gb_match_id', 'match_score', 'prediction_correct', 'actual_pnl', 'under_05_odds']]
        print(sample_df.to_string(index=False))
        
        # Save results
        df.to_csv('matched_gb_predictions_odds.csv', index=False)
        print(f"\nResults saved to matched_gb_predictions_odds.csv")
        
    else:
        print("No matches found between predictions and GB odds data")

if __name__ == "__main__":
    main()
