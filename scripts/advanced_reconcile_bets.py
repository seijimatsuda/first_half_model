#!/usr/bin/env python3
"""
Advanced Bet Reconciliation System

Provides detailed analysis of discrepancies between model predictions and actual bets.
"""

import pandas as pd
import re
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import unicodedata

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

class AdvancedBetReconciler:
    def __init__(self):
        self.alias_map = self._build_alias_map()
        self.reason_codes = {
            'PERFECT_MATCH': 'Perfect match',
            'TEAM_ALIAS': 'Team name alias mismatch',
            'DATE_OFFSET_1D': 'Date off by exactly 1 day',
            'PARSE_FORMAT': 'Failed to parse line format',
            'DUPLICATE': 'Duplicate entry',
            'THRESHOLD_RULE': 'Different selection rule/threshold',
            'WEEK_NUMBERING': 'Week numbering vs calendar date mismatch',
            'DATE_RANGE_MISMATCH': 'Outside expected date range',
            'UNKNOWN': 'Unknown discrepancy'
        }
    
    def _build_alias_map(self) -> Dict[str, str]:
        """Build comprehensive team name alias map."""
        return {
            # Manchester teams
            "man city": "manchester city",
            "manchester city": "manchester city",
            "man utd": "manchester united",
            "manchester united": "manchester united",
            "man u": "manchester united",
            
            # London teams
            "spurs": "tottenham",
            "tottenham": "tottenham",
            "tottenham hotspur": "tottenham",
            "west ham": "west ham",
            "west ham united": "west ham",
            "arsenal": "arsenal",
            "chelsea": "chelsea",
            "crystal palace": "crystal palace",
            "fulham": "fulham",
            "brentford": "brentford",
            
            # Midlands teams
            "nott'm forest": "nottingham forest",
            "nottingham forest": "nottingham forest",
            "notts forest": "nottingham forest",
            "leicester": "leicester",
            "leicester city": "leicester",
            "wolves": "wolverhampton",
            "wolverhampton": "wolverhampton",
            "wolverhampton wanderers": "wolverhampton",
            "aston villa": "aston villa",
            "villa": "aston villa",
            
            # Northern teams
            "liverpool": "liverpool",
            "everton": "everton",
            "newcastle": "newcastle",
            "newcastle united": "newcastle",
            
            # Southern teams
            "brighton": "brighton",
            "brighton & hove albion": "brighton",
            "brighton and hove albion": "brighton",
            "southampton": "southampton",
            "bournemouth": "bournemouth",
            "afc bournemouth": "bournemouth",
            "ipswich": "ipswich",
            "ipswich town": "ipswich",
        }
    
    def normalize_team(self, name: str) -> str:
        """Normalize team name for matching."""
        if pd.isna(name) or name == '':
            return ''
        
        # Convert to string and strip
        name = str(name).strip()
        
        # Normalize unicode (apostrophes, diacritics)
        name = unicodedata.normalize('NFKD', name)
        
        # Convert to lowercase
        name = name.lower()
        
        # Replace curly apostrophes with straight ones
        name = name.replace(''', "'").replace(''', "'")
        
        # Remove punctuation except spaces and apostrophes
        name = re.sub(r'[^\w\s\']', '', name)
        
        # Collapse multiple spaces
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Apply alias map
        return self.alias_map.get(name, name)
    
    def parse_predictions_week_by_week(self, filepath: str) -> pd.DataFrame:
        """Parse week_by_week_bets_list.txt format."""
        data = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern for: ✅ 2024-08-17 - West Ham vs Aston Villa
        pattern = r'✅\s+(\d{4}-\d{2}-\d{2})\s*-\s*([A-Za-z\' .]+)\s+vs\s+([A-Za-z\' .]+)'
        
        for match in re.finditer(pattern, content):
            date_str = match.group(1)
            home_team = match.group(2).strip()
            away_team = match.group(3).strip()
            
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                data.append({
                    'Date': date,
                    'Home Team': home_team,
                    'Away Team': away_team,
                    'ModelResult': 'WIN'
                })
            except ValueError:
                continue
        
        return pd.DataFrame(data)
    
    def parse_predictions_matchweek5_format(self, filepath: str) -> pd.DataFrame:
        """Parse matchweek5_plus_predictions.txt format."""
        data = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern for: ✅ WIN Aston Villa vs Wolves (2024-09-21)
        pattern = r'✅\s+(WIN|LOSS)\s+([A-Za-z\' .]+)\s+vs\s+([A-Za-z\' .]+)\s+\((\d{4}-\d{2}-\d{2})\)'
        
        for match in re.finditer(pattern, content):
            result = match.group(1)
            home_team = match.group(2).strip()
            away_team = match.group(3).strip()
            date_str = match.group(4)
            
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                data.append({
                    'Date': date,
                    'Home Team': home_team,
                    'Away Team': away_team,
                    'ModelResult': result
                })
            except ValueError:
                continue
        
        return pd.DataFrame(data)
    
    def load_actual_bets(self, filepath: str) -> pd.DataFrame:
        """Load actual bets from Excel spreadsheet."""
        df = pd.read_excel(filepath)
        
        # Filter to rows where FM Result is not null
        actual_bets = df[df['FM Result'].notna()].copy()
        
        # Ensure Date is datetime
        actual_bets['Date'] = pd.to_datetime(actual_bets['Date']).dt.date
        
        # Add normalized team names
        actual_bets['Home_clean'] = actual_bets['Home Team'].apply(self.normalize_team)
        actual_bets['Away_clean'] = actual_bets['Away Team'].apply(self.normalize_team)
        
        # Assert count is 121
        if len(actual_bets) != 121:
            raise ValueError(f"Expected 121 actual bets, got {len(actual_bets)}")
        
        return actual_bets
    
    def analyze_date_ranges(self, pred_df: pd.DataFrame, actual_df: pd.DataFrame) -> Dict:
        """Analyze date range differences between predictions and actual bets."""
        pred_dates = pred_df['Date'].unique()
        actual_dates = actual_df['Date'].unique()
        
        pred_min = min(pred_dates)
        pred_max = max(pred_dates)
        actual_min = min(actual_dates)
        actual_max = max(actual_dates)
        
        return {
            'pred_range': (pred_min, pred_max),
            'actual_range': (actual_min, actual_max),
            'pred_count': len(pred_dates),
            'actual_count': len(actual_dates),
            'overlap_dates': len(set(pred_dates) & set(actual_dates)),
            'pred_only_dates': len(set(pred_dates) - set(actual_dates)),
            'actual_only_dates': len(set(actual_dates) - set(pred_dates))
        }
    
    def reconcile_with_date_filtering(self, pred_df: pd.DataFrame, actual_df: pd.DataFrame, 
                                    filter_to_actual_range: bool = True) -> Dict:
        """Reconcile with optional date range filtering."""
        if filter_to_actual_range:
            # Filter predictions to actual bet date range
            actual_min = min(actual_df['Date'])
            actual_max = max(actual_df['Date'])
            pred_df = pred_df[(pred_df['Date'] >= actual_min) & (pred_df['Date'] <= actual_max)].copy()
        
        # Add normalized team names to predictions
        pred_df['Home_clean'] = pred_df['Home Team'].apply(self.normalize_team)
        pred_df['Away_clean'] = pred_df['Away Team'].apply(self.normalize_team)
        
        # Create join keys
        pred_df['join_key'] = pred_df['Date'].astype(str) + '|' + pred_df['Home_clean'] + '|' + pred_df['Away_clean']
        actual_df['join_key'] = actual_df['Date'].astype(str) + '|' + actual_df['Home_clean'] + '|' + actual_df['Away_clean']
        
        # Perfect matches
        perfect_matches = pred_df.merge(actual_df, on='join_key', how='inner')
        
        # Model-only (in predictions but not in actual)
        model_only = pred_df[~pred_df['join_key'].isin(actual_df['join_key'])].copy()
        
        # Actual-only (in actual but not in predictions)
        actual_only = actual_df[~actual_df['join_key'].isin(pred_df['join_key'])].copy()
        
        # Classify discrepancies
        model_only = self._classify_discrepancies(model_only, actual_df, 'model')
        actual_only = self._classify_discrepancies(actual_only, pred_df, 'actual')
        
        return {
            'perfect_matches': perfect_matches,
            'model_only': model_only,
            'actual_only': actual_only,
            'overlap_count': len(perfect_matches),
            'model_count': len(pred_df),
            'actual_count': len(actual_df),
            'date_filtered': filter_to_actual_range
        }
    
    def _classify_discrepancies(self, df: pd.DataFrame, other_df: pd.DataFrame, source: str) -> pd.DataFrame:
        """Classify discrepancy reasons."""
        df = df.copy()
        df['reason_code'] = 'UNKNOWN'
        
        for idx, row in df.iterrows():
            # Try to find matches with different criteria
            date = row['Date']
            home_clean = row['Home_clean'] if source == 'model' else row['Home_clean']
            away_clean = row['Away_clean'] if source == 'model' else row['Away_clean']
            
            # Check for date offset by 1 day
            date_plus_1 = date + timedelta(days=1)
            date_minus_1 = date - timedelta(days=1)
            
            for check_date in [date_plus_1, date_minus_1]:
                if source == 'model':
                    matches = other_df[
                        (other_df['Date'] == check_date) & 
                        (other_df['Home_clean'] == home_clean) & 
                        (other_df['Away_clean'] == away_clean)
                    ]
                else:
                    matches = other_df[
                        (other_df['Date'] == check_date) & 
                        (other_df['Home_clean'] == home_clean) & 
                        (other_df['Away_clean'] == away_clean)
                    ]
                
                if len(matches) > 0:
                    df.loc[idx, 'reason_code'] = 'DATE_OFFSET_1D'
                    break
            
            # Check for team alias issues (same date, different teams)
            if df.loc[idx, 'reason_code'] == 'UNKNOWN':
                same_date = other_df[other_df['Date'] == date]
                if len(same_date) > 0:
                    # Check if teams are close but not exact
                    for _, other_row in same_date.iterrows():
                        if source == 'model':
                            other_home = other_row['Home_clean']
                            other_away = other_row['Away_clean']
                        else:
                            other_home = other_row['Home_clean']
                            other_away = other_row['Away_clean']
                        
                        # Check if teams are similar (fuzzy matching)
                        if (self._teams_similar(home_clean, other_home) and 
                            self._teams_similar(away_clean, other_away)):
                            df.loc[idx, 'reason_code'] = 'TEAM_ALIAS'
                            break
        
        return df
    
    def _teams_similar(self, team1: str, team2: str) -> bool:
        """Check if two team names are similar (fuzzy matching)."""
        if team1 == team2:
            return True
        
        # Check if one contains the other
        if team1 in team2 or team2 in team1:
            return True
        
        # Check for common abbreviations
        abbreviations = {
            'manchester': 'man',
            'united': 'utd',
            'wolverhampton': 'wolves',
            'tottenham': 'spurs',
            'nottingham': 'nott',
            'brighton': 'bha'
        }
        
        for full, abbrev in abbreviations.items():
            if (full in team1 and abbrev in team2) or (abbrev in team1 and full in team2):
                return True
        
        return False
    
    def generate_detailed_summary(self, results: Dict) -> str:
        """Generate detailed markdown summary of reconciliation results."""
        summary = "# Advanced Bet Reconciliation Analysis\n\n"
        
        for model_file, result in results.items():
            recon = result['reconciliation']
            date_analysis = result['date_analysis']
            
            summary += f"## {Path(model_file).name}\n\n"
            
            # Date range analysis
            summary += f"### Date Range Analysis\n"
            summary += f"- **Prediction range**: {date_analysis['pred_range'][0]} to {date_analysis['pred_range'][1]}\n"
            summary += f"- **Actual range**: {date_analysis['actual_range'][0]} to {date_analysis['actual_range'][1]}\n"
            summary += f"- **Date overlap**: {date_analysis['overlap_dates']} dates\n"
            summary += f"- **Prediction-only dates**: {date_analysis['pred_only_dates']}\n"
            summary += f"- **Actual-only dates**: {date_analysis['actual_only_dates']}\n\n"
            
            # Reconciliation results
            summary += f"### Reconciliation Results\n"
            summary += f"- **Overlap**: {recon['overlap_count']}/{recon['actual_count']} ({recon['overlap_count']/recon['actual_count']*100:.1f}%)\n"
            summary += f"- **Model predictions**: {recon['model_count']}\n"
            summary += f"- **Actual bets**: {recon['actual_count']}\n"
            summary += f"- **Model-only**: {len(recon['model_only'])}\n"
            summary += f"- **Actual-only**: {len(recon['actual_only'])}\n"
            summary += f"- **Date filtered**: {recon['date_filtered']}\n\n"
            
            # Reason code breakdown
            if len(recon['model_only']) > 0:
                reason_counts = recon['model_only']['reason_code'].value_counts()
                summary += f"**Model-only reasons**:\n"
                for reason, count in reason_counts.head(5).items():
                    summary += f"- {self.reason_codes.get(reason, reason)}: {count}\n"
                
                # Show sample model-only entries
                summary += f"\n**Sample model-only entries**:\n"
                for _, row in recon['model_only'].head(3).iterrows():
                    summary += f"- {row['Date']} - {row['Home Team']} vs {row['Away Team']} ({row['reason_code']})\n"
                summary += "\n"
            
            if len(recon['actual_only']) > 0:
                reason_counts = recon['actual_only']['reason_code'].value_counts()
                summary += f"**Actual-only reasons**:\n"
                for reason, count in reason_counts.head(5).items():
                    summary += f"- {self.reason_codes.get(reason, reason)}: {count}\n"
                
                # Show sample actual-only entries
                summary += f"\n**Sample actual-only entries**:\n"
                for _, row in recon['actual_only'].head(3).iterrows():
                    summary += f"- {row['Date']} - {row['Home Team']} vs {row['Away Team']} ({row['reason_code']})\n"
                summary += "\n"
            
            summary += "---\n\n"
        
        return summary
    
    def run_advanced_reconciliation(self, model_files: List[str], actual_file: str) -> Dict:
        """Run advanced reconciliation with date analysis."""
        results = {}
        
        # Load actual bets
        print("Loading actual bets...")
        actual_bets = self.load_actual_bets(actual_file)
        print(f"Loaded {len(actual_bets)} actual bets")
        
        # Process each model file
        for model_file in model_files:
            print(f"\nProcessing {model_file}...")
            
            # Determine parser based on filename
            if 'week_by_week' in model_file:
                pred_df = self.parse_predictions_week_by_week(model_file)
            elif 'matchweek5_plus' in model_file:
                pred_df = self.parse_predictions_matchweek5_format(model_file)
            else:
                pred_df = self.parse_predictions_week_by_week(model_file)
            
            print(f"Parsed {len(pred_df)} predictions")
            
            # Analyze date ranges
            date_analysis = self.analyze_date_ranges(pred_df, actual_bets)
            
            # Reconcile without date filtering
            reconciliation_no_filter = self.reconcile_with_date_filtering(pred_df, actual_bets, filter_to_actual_range=False)
            
            # Reconcile with date filtering
            reconciliation_with_filter = self.reconcile_with_date_filtering(pred_df, actual_bets, filter_to_actual_range=True)
            
            # Save results
            base_name = Path(model_file).stem
            
            # Save both versions
            for suffix, recon in [('_no_filter', reconciliation_no_filter), ('_with_filter', reconciliation_with_filter)]:
                # Save overlap
                overlap_file = f"/tmp/{base_name}_overlap{suffix}.csv"
                recon['perfect_matches'].to_csv(overlap_file, index=False)
                
                # Save model-only
                model_only_file = f"/tmp/{base_name}_model_only{suffix}.csv"
                recon['model_only'].to_csv(model_only_file, index=False)
                
                # Save actual-only
                actual_only_file = f"/tmp/{base_name}_actual_only{suffix}.csv"
                recon['actual_only'].to_csv(actual_only_file, index=False)
            
            results[model_file] = {
                'reconciliation': reconciliation_with_filter,  # Use filtered version for summary
                'date_analysis': date_analysis,
                'files': {
                    'overlap_no_filter': f"/tmp/{base_name}_overlap_no_filter.csv",
                    'model_only_no_filter': f"/tmp/{base_name}_model_only_no_filter.csv",
                    'actual_only_no_filter': f"/tmp/{base_name}_actual_only_no_filter.csv",
                    'overlap_with_filter': f"/tmp/{base_name}_overlap_with_filter.csv",
                    'model_only_with_filter': f"/tmp/{base_name}_model_only_with_filter.csv",
                    'actual_only_with_filter': f"/tmp/{base_name}_actual_only_with_filter.csv"
                }
            }
        
        return results


def main():
    """Main execution function."""
    # Define file paths
    model_files = [
        'matchweek5_plus_predictions.txt',
        'week_by_week_bets_list.txt'
    ]
    
    actual_file = 'data/ENP_2024-2025_M.xlsx'
    
    # Check if files exist
    missing_files = []
    for file in model_files + [actual_file]:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"Missing files: {missing_files}")
        return
    
    # Run advanced reconciliation
    reconciler = AdvancedBetReconciler()
    results = reconciler.run_advanced_reconciliation(model_files, actual_file)
    
    # Generate detailed summary
    summary = reconciler.generate_detailed_summary(results)
    print(summary)
    
    # Save summary
    with open('/tmp/advanced_reconciliation_summary.md', 'w') as f:
        f.write(summary)
    
    print("Advanced reconciliation complete! Check /tmp/ for detailed CSV files.")


if __name__ == "__main__":
    main()
