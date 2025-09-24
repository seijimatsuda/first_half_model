#!/usr/bin/env python3
"""
List all English matches that had predictions
"""

import pandas as pd

def main():
    # Load the comprehensive results
    df = pd.read_csv('comprehensive_backtest_full_all_results.csv')
    
    # Filter for English leagues
    english_leagues = ['Premier League', 'Championship', 'League One', 'League Two', 'National League']
    english_data = df[df['league_name'].isin(english_leagues)].copy()
    
    print(f'Total English league predictions: {len(english_data)}')
    print()
    
    # Group by league and show matches
    for league in english_leagues:
        league_matches = english_data[english_data['league_name'] == league]
        if len(league_matches) > 0:
            print(f'=== {league} ({len(league_matches)} matches) ===')
            for _, match in league_matches.iterrows():
                date_str = match['match_date'][:10] if pd.notna(match['match_date']) else 'Unknown'
                print(f'{match["home_team"]} vs {match["away_team"]} - {date_str} - Combined Avg: {match["combined_avg"]:.2f} - PnL: ${match["pnl"]:.0f}')
            print()
    
    # Summary statistics
    print("=== SUMMARY STATISTICS ===")
    summary = english_data.groupby('league_name').agg({
        'pnl': ['count', 'sum', 'mean'],
        'prediction_correct': 'sum'
    }).round(2)
    
    summary.columns = ['Total_Bets', 'Total_PnL', 'Avg_PnL', 'Correct_Predictions']
    summary['Accuracy'] = (summary['Correct_Predictions'] / summary['Total_Bets'] * 100).round(1)
    summary['ROI'] = (summary['Total_PnL'] / (summary['Total_Bets'] * 100) * 100).round(1)
    
    print(summary.to_string())
    
    # Save to CSV for reference
    english_data.to_csv('english_league_predictions.csv', index=False)
    print(f"\nDetailed results saved to english_league_predictions.csv")

if __name__ == "__main__":
    main()
