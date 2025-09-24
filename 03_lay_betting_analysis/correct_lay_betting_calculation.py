#!/usr/bin/env python3
"""
Correct lay betting calculation using the proper formula:
- Profit: +$100 if goal scored before half-time (minus 2% commission = $98)
- Loss: -$100 × (Under Odds - 1) if 0-0 at half-time
"""

import pandas as pd

def load_and_calculate_correct_pnl():
    """Load the matched data and calculate correct PnL using proper lay betting formula"""
    
    # Load the previous results that had the odds data
    try:
        df = pd.read_csv('corrected_lay_odds_pnl_results.csv')
        print(f"Loaded {len(df)} matched predictions with odds data")
    except:
        print("Could not load previous results. Please run the odds extraction first.")
        return
    
    # Calculate correct PnL using the proper formula
    def calculate_correct_pnl(row):
        under_odds = row['under_odds']
        
        if row['prediction_correct']:
            # Goal scored before half-time - we WIN the lay bet
            # Profit: +$100 minus 2% commission = $98
            return 98.0
        else:
            # 0-0 at half-time - we LOSE the lay bet
            # Loss: -$100 × (Under Odds - 1)
            loss = -100 * (under_odds - 1)
            return loss
    
    # Apply the correct calculation
    df['correct_pnl'] = df.apply(calculate_correct_pnl, axis=1)
    
    # Calculate summary statistics
    total_bets = len(df)
    correct_predictions = df['prediction_correct'].sum()
    accuracy = correct_predictions / total_bets * 100
    
    total_original_pnl = df['original_pnl'].sum()
    total_correct_pnl = df['correct_pnl'].sum()
    
    original_roi = (total_original_pnl / (total_bets * 100)) * 100
    correct_roi = (total_correct_pnl / (total_bets * 100)) * 100
    
    print(f"\n=== CORRECT LAY BETTING CALCULATION ===")
    print(f"Formula: Profit = +$98 if goal scored, Loss = -$100 × (Under Odds - 1) if 0-0")
    print(f"Commission: 2% on winning bets")
    print()
    print(f"Total Bets: {total_bets}")
    print(f"Accuracy: {accuracy:.1f}%")
    print(f"Original PnL: ${total_original_pnl:,.2f}")
    print(f"Correct PnL: ${total_correct_pnl:,.2f}")
    print(f"Original ROI: {original_roi:.1f}%")
    print(f"Correct ROI: {correct_roi:.1f}%")
    
    # By league breakdown
    print(f"\n=== BY LEAGUE ===")
    league_stats = df.groupby('league_name').agg({
        'prediction_correct': ['count', 'sum'],
        'original_pnl': 'sum',
        'correct_pnl': 'sum',
        'stake': 'sum'
    }).round(2)
    
    league_stats.columns = ['total_bets', 'correct_predictions', 'original_pnl', 'correct_pnl', 'total_stake']
    league_stats['accuracy'] = (league_stats['correct_predictions'] / league_stats['total_bets'] * 100).round(1)
    league_stats['original_roi'] = (league_stats['original_pnl'] / league_stats['total_stake'] * 100).round(1)
    league_stats['correct_roi'] = (league_stats['correct_pnl'] / league_stats['total_stake'] * 100).round(1)
    
    print(league_stats[['total_bets', 'accuracy', 'original_pnl', 'correct_pnl', 'original_roi', 'correct_roi']].to_string())
    
    # Show detailed results
    print(f"\n=== DETAILED RESULTS ===")
    detailed = df[['home_team', 'away_team', 'league_name', 'prediction_correct', 
                   'under_odds', 'original_pnl', 'correct_pnl']].copy()
    
    # Add potential loss calculation for reference
    detailed['potential_loss'] = -100 * (detailed['under_odds'] - 1)
    
    print(detailed.to_string(index=False))
    
    # Save corrected results
    df.to_csv('final_correct_lay_betting_results.csv', index=False)
    print(f"\nDetailed results saved to final_correct_lay_betting_results.csv")
    
    # Analysis of wins vs losses
    wins = df[df['prediction_correct'] == True]
    losses = df[df['prediction_correct'] == False]
    
    print(f"\n=== WIN/LOSS BREAKDOWN ===")
    print(f"Winning bets: {len(wins)} (Profit: ${wins['correct_pnl'].sum():,.2f})")
    print(f"Losing bets: {len(losses)} (Loss: ${losses['correct_pnl'].sum():,.2f})")
    
    if len(losses) > 0:
        avg_loss = losses['correct_pnl'].mean()
        print(f"Average loss per losing bet: ${avg_loss:.2f}")
        print(f"Maximum single loss: ${losses['correct_pnl'].min():.2f}")
        print(f"Minimum single loss: ${losses['correct_pnl'].max():.2f}")

if __name__ == "__main__":
    load_and_calculate_correct_pnl()
