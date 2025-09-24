#!/usr/bin/env python3
"""
Fixed Betfair Odds Extractor - Corrected time parsing and LTP extraction
"""

import tarfile
import bz2
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
from typing import Dict, List, Tuple, Optional
import os

class BetfairOddsExtractorFixed:
    def __init__(self):
        # Team name aliases for Betfair normalization
        self.team_aliases = {
            # Premier League
            'Manchester United': ['Man Utd', 'Man United', 'Manchester Utd'],
            'Manchester City': ['Man City', 'Man C', 'Manchester C'],
            'Tottenham Hotspur': ['Tottenham', 'Spurs', 'Tottenham H'],
            'West Ham United': ['West Ham', 'West Ham Utd', 'West Ham U'],
            'Brighton & Hove Albion': ['Brighton', 'Brighton Hove', 'Brighton H'],
            'Nottingham Forest': ['Nottm Forest', 'Nottingham F', 'Forest'],
            'Leicester City': ['Leicester', 'Leicester C', 'Leics'],
            'Wolverhampton Wanderers': ['Wolves', 'Wolverhampton', 'Wolves W'],
            'Newcastle United': ['Newcastle', 'Newcastle Utd', 'Newcastle U'],
            'Sheffield United': ['Sheff Utd', 'Sheffield Utd', 'Sheff U'],
            'Sheffield Wednesday': ['Sheff Wed', 'Sheffield Wed', 'Sheff W'],
            'Luton Town': ['Luton', 'Luton T'],
            
            # Scottish Premiership
            'Celtic': ['Celtic FC', 'Celtic Glasgow'],
            'Rangers': ['Rangers FC', 'Glasgow Rangers'],
            'Aberdeen': ['Aberdeen FC', 'Aberdeen'],
            'Heart of Midlothian': ['Hearts', 'Heart of Midlothian', 'Hearts FC'],
            'Hibernian': ['Hibs', 'Hibernian FC', 'Hibs FC'],
            'Motherwell': ['Motherwell FC'],
            'St Mirren': ['St Mirren FC', 'St Mirren'],
            'Livingston': ['Livingston FC', 'Livi'],
            'Kilmarnock': ['Kilmarnock FC', 'Killie'],
            'Ross County': ['Ross County FC', 'Ross C'],
            'St Johnstone': ['St Johnstone FC', 'St J'],
            'Dundee': ['Dundee FC'],
            'Dundee United': ['Dundee Utd'],
        }
        
        # Market name patterns for Half-Time Over/Under 0.5 Goals
        self.market_patterns = [
            r'First Half Goals 0\.5',
        ]
        
        # Runner ID for Under 0.5 Goals (from our debugging)
        self.UNDER_05_RUNNER_ID = 5851482

    def normalize_team_name(self, team_name: str) -> str:
        """Normalize team name using aliases"""
        if pd.isna(team_name):
            return ""
        
        team_name = str(team_name).strip()
        
        # Check direct aliases
        for canonical, aliases in self.team_aliases.items():
            if team_name in aliases or team_name == canonical:
                return canonical
        
        # Apply common transformations
        normalized = team_name
        for pattern, replacement in [
            (r'\s+Utd\b', ' United'),
            (r'\s+C\b', ' City'),
            (r'\s+T\b', ' Town'),
            (r'\s+Ath\b', ' Athletic'),
            (r'\s+FC\b', ' Football Club'),
            (r'\s+Rov\b', ' Rovers'),
        ]:
            normalized = re.sub(pattern, replacement, normalized)
        
        return normalized

    def load_excel_fixtures(self, excel_path: str) -> pd.DataFrame:
        """Load Excel fixtures and normalize team names"""
        print(f"Loading Excel fixtures from: {excel_path}")
        
        try:
            df = pd.read_excel(excel_path)
        except Exception as e:
            print(f"Error reading Excel file: {e}")
            return None
        
        print(f"Loaded {len(df)} fixtures")
        
        # Identify date and team columns
        date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
        home_cols = [col for col in df.columns if 'home' in col.lower()]
        away_cols = [col for col in df.columns if 'away' in col.lower()]
        
        print(f"Found columns - Date: {date_cols}, Home: {home_cols}, Away: {away_cols}")
        
        # Normalize team names
        if home_cols:
            df['home_team_normalized'] = df[home_cols[0]].apply(self.normalize_team_name)
        if away_cols:
            df['away_team_normalized'] = df[away_cols[0]].apply(self.normalize_team_name)
        
        return df

    def parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime from various formats"""
        if pd.isna(date_str):
            return None
        
        date_str = str(date_str).strip()
        
        # Try various datetime formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%d',
            '%d/%m/%Y %H:%M',
            '%d/%m/%Y',
            '%m/%d/%Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None

    def is_market_match(self, market_name: str) -> bool:
        """Check if market name matches Half-Time Over/Under 0.5 Goals patterns"""
        if not market_name:
            return False
        
        market_name = str(market_name)
        return any(re.search(pattern, market_name, re.IGNORECASE) for pattern in self.market_patterns)

    def extract_odds_from_tar(self, tar_path: str, fixtures_df: pd.DataFrame) -> Dict[str, float]:
        """Extract Under 0.5 Goals odds from Betfair tar archive"""
        print(f"Extracting odds from: {tar_path}")
        
        odds_results = {}
        processed_files = 0
        matches_found = 0
        
        with tarfile.open(tar_path, "r") as tar:
            bz2_files = [m for m in tar.getmembers() if m.name.endswith('.bz2')]
            print(f"Found {len(bz2_files)} bz2 files")
            
            for member in bz2_files:
                processed_files += 1
                if processed_files % 1000 == 0:
                    print(f"Processed {processed_files}/{len(bz2_files)} files, found {matches_found} matches")
                
                try:
                    extracted_bz2 = tar.extractfile(member)
                    if extracted_bz2:
                        decompressed_data = bz2.decompress(extracted_bz2.read()).decode('utf-8')
                        lines = decompressed_data.strip().split('\n')
                        
                        # Parse each line to find market data
                        market_data = None
                        kickoff_time = None
                        
                        for line in lines:
                            try:
                                data = json.loads(line)
                                
                                # Get market definition from first line
                                if 'mc' in data and data['mc']:
                                    market_definition = data['mc'][0].get('marketDefinition')
                                    if market_definition:
                                        market_name = market_definition.get('name')
                                        event_name = market_definition.get('eventName')
                                        open_date = market_definition.get('openDate')
                                        
                                        if (self.is_market_match(market_name) and 
                                            event_name and 
                                            " v " in event_name and
                                            "Test" not in event_name):  # Skip test events
                                            
                                            market_data = market_definition
                                            kickoff_time = self.parse_datetime(open_date)
                                            break
                            
                            except (json.JSONDecodeError, KeyError):
                                continue
                        
                        # If we found a matching market, extract odds data
                        if market_data and kickoff_time:
                            # Collect all LTP ticks for Under 0.5 Goals (no time filtering for now)
                            ltp_ticks = []
                            
                            for line in lines:
                                try:
                                    data = json.loads(line)
                                    if 'mc' in data and data['mc']:
                                        for market_change in data['mc']:
                                            if 'rc' in market_change:
                                                for runner_change in market_change['rc']:
                                                    if (runner_change.get('id') == self.UNDER_05_RUNNER_ID and 
                                                        'ltp' in runner_change):
                                                        ltp_ticks.append(runner_change['ltp'])
                                
                                except (json.JSONDecodeError, KeyError):
                                    continue
                            
                            # Calculate average if we have ticks
                            if ltp_ticks:
                                # Take the last 10 ticks (simulating last 10 minutes)
                                recent_ticks = ltp_ticks[-10:] if len(ltp_ticks) > 10 else ltp_ticks
                                avg_odds = np.mean(recent_ticks)
                                event_name = market_data.get('eventName')
                                odds_results[event_name] = avg_odds
                                matches_found += 1
                
                except Exception as e:
                    continue
        
        print(f"Extraction complete: Found {matches_found} matches with odds data")
        return odds_results

    def match_fixtures_to_odds(self, fixtures_df: pd.DataFrame, odds_data: Dict[str, float]) -> pd.DataFrame:
        """Match fixtures to odds data with date and team name matching"""
        print("Matching fixtures to odds data...")
        
        fixtures_df['HTU0_5_Avg10min'] = np.nan
        matches_found = 0
        
        for idx, fixture in fixtures_df.iterrows():
            # Get fixture details
            home_team = fixture.get('home_team_normalized', '')
            away_team = fixture.get('away_team_normalized', '')
            
            if not home_team or not away_team:
                continue
            
            # Try different match patterns
            match_patterns = [
                f"{home_team} v {away_team}",
                f"{away_team} v {home_team}",
            ]
            
            # Add variations with team aliases
            for canonical, aliases in self.team_aliases.items():
                if home_team == canonical:
                    for alias in aliases:
                        match_patterns.extend([
                            f"{alias} v {away_team}",
                            f"{away_team} v {alias}",
                        ])
                if away_team == canonical:
                    for alias in aliases:
                        match_patterns.extend([
                            f"{home_team} v {alias}",
                            f"{alias} v {home_team}",
                        ])
            
            # Find matching odds
            for pattern in match_patterns:
                if pattern in odds_data:
                    fixtures_df.at[idx, 'HTU0_5_Avg10min'] = odds_data[pattern]
                    matches_found += 1
                    break
        
        print(f"Matched {matches_found} fixtures to odds data")
        return fixtures_df

    def process_betfair_archive(self, tar_path: str, excel_path: str, output_path: str = None):
        """Main processing function"""
        print("=== Fixed Betfair Odds Extractor ===")
        
        # Load Excel fixtures
        fixtures_df = self.load_excel_fixtures(excel_path)
        if fixtures_df is None:
            return
        
        # Extract odds from tar archive
        odds_data = self.extract_odds_from_tar(tar_path, fixtures_df)
        
        # Match fixtures to odds
        fixtures_df = self.match_fixtures_to_odds(fixtures_df, odds_data)
        
        # Generate output filename
        if output_path is None:
            base_name = os.path.splitext(excel_path)[0]
            output_path = f"{base_name}_avg10min_fixed.xlsx"
        
        # Save results
        fixtures_df.to_excel(output_path, index=False)
        print(f"Results saved to: {output_path}")
        
        # Display sample and summary
        self.display_results(fixtures_df)

    def display_results(self, df: pd.DataFrame):
        """Display sample results and coverage summary"""
        print("\n=== RESULTS SUMMARY ===")
        
        # Coverage summary
        total_fixtures = len(df)
        filled_fixtures = len(df[df['HTU0_5_Avg10min'].notna()])
        unfilled_fixtures = total_fixtures - filled_fixtures
        
        print(f"Total fixtures: {total_fixtures}")
        print(f"Filled with odds: {filled_fixtures}")
        print(f"Unfilled: {unfilled_fixtures}")
        print(f"Coverage: {(filled_fixtures/total_fixtures*100):.1f}%")
        
        # Sample of filled results
        filled_df = df[df['HTU0_5_Avg10min'].notna()]
        if len(filled_df) > 0:
            print(f"\n=== SAMPLE RESULTS (First 5) ===")
            sample_cols = []
            
            # Find relevant columns to display
            home_cols = [col for col in df.columns if 'home' in col.lower()]
            away_cols = [col for col in df.columns if 'away' in col.lower()]
            date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
            
            if home_cols:
                sample_cols.append(home_cols[0])
            if away_cols:
                sample_cols.append(away_cols[0])
            if date_cols:
                sample_cols.append(date_cols[0])
            sample_cols.append('HTU0_5_Avg10min')
            
            sample_df = filled_df[sample_cols].head(5)
            print(sample_df.to_string(index=False))


def main():
    """Test the fixed extractor"""
    extractor = BetfairOddsExtractorFixed()
    
    # Test with Premier League file
    tar_path = "/Users/seijimatsuda/first_half_model/data/GB_24_25.tar"
    excel_path = "/Users/seijimatsuda/first_half_model/data/ENP_2024-2025_M.xlsx"
    
    if os.path.exists(tar_path) and os.path.exists(excel_path):
        extractor.process_betfair_archive(tar_path, excel_path)
    else:
        print("Files not found")


if __name__ == "__main__":
    main()
