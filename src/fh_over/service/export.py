"""Export functionality for scan results."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from .scan import ScanResult


def export_to_csv(results: List[ScanResult], filepath: str) -> None:
    """Export scan results to CSV file."""
    
    if not results:
        return
    
    # Create directory if it doesn't exist
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'fixture_id', 'league_name', 'home_team', 'away_team', 'match_date',
            'lambda_hat', 'p_hat', 'p_ci_low', 'p_ci_high', 'prob_ci_width',
            'n_home', 'n_away', 'fair_odds', 'market_odds', 'edge_pct', 'odds_provider',
            'stake_mode', 'stake_amount', 'stake_fraction',
            'lambda_threshold_met', 'min_samples_met', 'edge_threshold_met', 'ci_width_threshold_met',
            'signal', 'reasons'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            row = {
                'fixture_id': result.fixture_id,
                'league_name': result.league_name,
                'home_team': result.home_team,
                'away_team': result.away_team,
                'match_date': result.match_date.isoformat(),
                'lambda_hat': result.lambda_hat,
                'p_hat': result.p_hat,
                'p_ci_low': result.p_ci_low,
                'p_ci_high': result.p_ci_high,
                'prob_ci_width': result.prob_ci_width,
                'n_home': result.n_home,
                'n_away': result.n_away,
                'fair_odds': result.fair_odds,
                'market_odds': result.market_odds,
                'edge_pct': result.edge_pct,
                'odds_provider': result.odds_provider,
                'stake_mode': result.stake_mode,
                'stake_amount': result.stake_amount,
                'stake_fraction': result.stake_fraction,
                'lambda_threshold_met': result.lambda_threshold_met,
                'min_samples_met': result.min_samples_met,
                'edge_threshold_met': result.edge_threshold_met,
                'ci_width_threshold_met': result.ci_width_threshold_met,
                'signal': result.signal,
                'reasons': '; '.join(result.reasons)
            }
            writer.writerow(row)


def export_to_json(results: List[ScanResult], filepath: str) -> None:
    """Export scan results to JSON file."""
    
    if not results:
        return
    
    # Create directory if it doesn't exist
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    # Convert results to dictionaries
    data = []
    for result in results:
        data.append({
            'fixture_id': result.fixture_id,
            'league_name': result.league_name,
            'home_team': result.home_team,
            'away_team': result.away_team,
            'match_date': result.match_date.isoformat(),
            'lambda_hat': result.lambda_hat,
            'p_hat': result.p_hat,
            'p_ci_low': result.p_ci_low,
            'p_ci_high': result.p_ci_high,
            'prob_ci_width': result.prob_ci_width,
            'n_home': result.n_home,
            'n_away': result.n_away,
            'fair_odds': result.fair_odds,
            'market_odds': result.market_odds,
            'edge_pct': result.edge_pct,
            'odds_provider': result.odds_provider,
            'stake_mode': result.stake_mode,
            'stake_amount': result.stake_amount,
            'stake_fraction': result.stake_fraction,
            'lambda_threshold_met': result.lambda_threshold_met,
            'min_samples_met': result.min_samples_met,
            'edge_threshold_met': result.edge_threshold_met,
            'ci_width_threshold_met': result.ci_width_threshold_met,
            'signal': result.signal,
            'reasons': result.reasons
        })
    
    with open(filepath, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=2, ensure_ascii=False)


def export_to_summary(results: List[ScanResult], filepath: str) -> None:
    """Export summary statistics to text file."""
    
    if not results:
        return
    
    # Create directory if it doesn't exist
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    # Calculate summary statistics
    total_fixtures = len(results)
    value_signals = sum(1 for r in results if r.signal)
    avg_lambda = sum(r.lambda_hat for r in results) / total_fixtures if total_fixtures > 0 else 0
    avg_edge = sum(r.edge_pct for r in results if r.edge_pct) / sum(1 for r in results if r.edge_pct) if any(r.edge_pct for r in results) else 0
    total_stake = sum(r.stake_amount for r in results if r.signal)
    
    summary = f"""
First-Half Over 0.5 Scanner - Summary Report
Generated: {datetime.utcnow().isoformat()}

Total Fixtures Scanned: {total_fixtures}
Value Signals Found: {value_signals}
Signal Rate: {value_signals/total_fixtures*100:.1f}%

Average Lambda: {avg_lambda:.3f}
Average Edge: {avg_edge:.2f}%
Total Recommended Stake: ${total_stake:.2f}

Value Signals by League:
"""
    
    # Group by league
    league_signals = {}
    for result in results:
        if result.signal:
            league = result.league_name
            if league not in league_signals:
                league_signals[league] = 0
            league_signals[league] += 1
    
    for league, count in sorted(league_signals.items()):
        summary += f"  {league}: {count} signals\n"
    
    summary += f"\nDetailed Results:\n"
    summary += f"{'='*80}\n"
    
    for result in results:
        if result.signal:
            summary += f"""
{result.home_team} vs {result.away_team} ({result.league_name})
Match Date: {result.match_date.strftime('%Y-%m-%d %H:%M')}
Lambda: {result.lambda_hat:.3f}, P(Over 0.5): {result.p_hat:.3f} [{result.p_ci_low:.3f}, {result.p_ci_high:.3f}]
Fair Odds: {result.fair_odds:.2f}, Market Odds: {result.market_odds:.2f}, Edge: {result.edge_pct:.2f}%
Stake: ${result.stake_amount:.2f} ({result.stake_fraction:.3f})
Samples: {result.n_home}H/{result.n_away}A
Reasons: {'; '.join(result.reasons)}
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(summary)
