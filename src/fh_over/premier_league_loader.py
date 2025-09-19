"""Specialized loader for Premier League Excel datasets."""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json

from fh_over.models import Team, Fixture, SplitSample, League
from fh_over.db import get_session
from sqlmodel import Session, select


class PremierLeagueLoader:
    """Specialized loader for Premier League Excel datasets."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.data = None
        self.teams_map = {}
        self.leagues_map = {}
    
    def load_data(self) -> pd.DataFrame:
        """Load Premier League data from Excel file."""
        try:
            # Load the Excel file
            self.data = pd.read_excel(self.file_path)
            print(f"✅ Loaded {len(self.data)} rows from {self.file_path}")
            
            # Clean up the data
            self._clean_data()
            
            return self.data
        except Exception as e:
            print(f"❌ Error loading Excel file: {e}")
            return None
    
    def _clean_data(self) -> None:
        """Clean and prepare the data."""
        if self.data is None:
            return
        
        # Remove rows where HT Goals is NaN (these seem to be header rows)
        self.data = self.data.dropna(subset=['HT Goals'])
        
        # Convert date column
        self.data['Date'] = pd.to_datetime(self.data['Date'])
        
        # Fill NaN values in numeric columns
        numeric_columns = ['T1', 'T2', 'HT Goals', 'AVG T1 Goals', 'AVG T2 Goals']
        for col in numeric_columns:
            if col in self.data.columns:
                self.data[col] = self.data[col].fillna(0)
        
        print(f"📊 Cleaned data: {len(self.data)} valid matches")
        print(f"Date range: {self.data['Date'].min()} to {self.data['Date'].max()}")
    
    def inspect_data(self) -> None:
        """Inspect the cleaned data."""
        if self.data is None:
            print("No data loaded.")
            return
        
        print("\n📊 Premier League Dataset Overview:")
        print(f"Shape: {self.data.shape}")
        print(f"Date range: {self.data['Date'].min()} to {self.data['Date'].max()}")
        print(f"Unique teams: {len(set(self.data['Home Team'].unique()) | set(self.data['Away Team'].unique()))}")
        
        print(f"\nFirst 5 matches:")
        print(self.data[['Date', 'Home Team', 'Away Team', 'T1', 'T2', 'HT Goals']].head())
        
        print(f"\nHT Goals distribution:")
        print(self.data['HT Goals'].value_counts().sort_index())
        
        print(f"\nSample match data:")
        sample = self.data.iloc[0]
        print(f"  {sample['Home Team']} vs {sample['Away Team']}")
        print(f"  Date: {sample['Date']}")
        print(f"  HT Goals: {sample['HT Goals']}")
        print(f"  T1: {sample['T1']}, T2: {sample['T2']}")
    
    def parse_matches(self) -> List[Dict[str, Any]]:
        """Parse matches from the cleaned data."""
        if self.data is None:
            return []
        
        matches = []
        
        for idx, row in self.data.iterrows():
            try:
                # Extract match information
                home_team = str(row['Home Team']).strip()
                away_team = str(row['Away Team']).strip()
                match_date = row['Date']
                
                # HT Goals appears to be the total first-half goals
                ht_goals = float(row['HT Goals']) if pd.notna(row['HT Goals']) else 0.0
                
                # T1 and T2 might be individual team first-half goals
                t1_goals = float(row['T1']) if pd.notna(row['T1']) else 0.0
                t2_goals = float(row['T2']) if pd.notna(row['T2']) else 0.0
                
                # If T1 and T2 don't add up to HT Goals, we'll use HT Goals and split it
                if abs((t1_goals + t2_goals) - ht_goals) > 0.1:
                    # Split HT Goals evenly or use some other logic
                    # For now, let's assume T1 and T2 are correct if they're non-zero
                    if t1_goals > 0 or t2_goals > 0:
                        home_first_half = t1_goals
                        away_first_half = t2_goals
                    else:
                        # If no individual data, split HT Goals
                        home_first_half = ht_goals / 2
                        away_first_half = ht_goals / 2
                else:
                    home_first_half = t1_goals
                    away_first_half = t2_goals
                
                match_data = {
                    'home_team': home_team,
                    'away_team': away_team,
                    'match_date': match_date,
                    'home_first_half': home_first_half,
                    'away_first_half': away_first_half,
                    'total_first_half': ht_goals,
                    'league': 'Premier League',
                    'season': '2024-25',
                    'round': int(row['Round']) if pd.notna(row['Round']) else 1,
                    'row_index': idx
                }
                
                matches.append(match_data)
                
            except Exception as e:
                print(f"⚠️ Error parsing row {idx}: {e}")
                continue
        
        return matches
    
    def store_in_database(self, matches: List[Dict[str, Any]], session: Session) -> None:
        """Store parsed matches in the database."""
        
        # Create Premier League
        league = League(
            provider_id="premier_league_2024_25",
            provider_name="excel",
            name="Premier League",
            country="England",
            season="2024-25",
            is_active=True
        )
        session.add(league)
        session.commit()
        session.refresh(league)
        self.leagues_map["Premier League"] = league.id
        
        print(f"✅ Created league: {league.name} (ID: {league.id})")
        
        # Create teams and store fixtures
        fixtures_created = 0
        samples_created = 0
        
        for match in matches:
            try:
                # Create/get home team
                home_team = self._get_or_create_team(
                    session, match['home_team'], league.id, "excel"
                )
                
                # Create/get away team
                away_team = self._get_or_create_team(
                    session, match['away_team'], league.id, "excel"
                )
                
                # Create fixture
                fixture = Fixture(
                    provider_id=f"pl_{match['row_index']}",
                    provider_name="excel",
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    league_id=str(league.id),
                    league_name="Premier League",
                    match_date=match['match_date'],
                    season="2024-25",
                    status="finished",
                    home_first_half_score=int(match['home_first_half']),
                    away_first_half_score=int(match['away_first_half'])
                )
                session.add(fixture)
                session.commit()
                session.refresh(fixture)
                fixtures_created += 1
                
                # Create first-half samples
                total_first_half = match['total_first_half']
                
                # Home team sample
                home_sample = SplitSample(
                    team_id=home_team.id,
                    fixture_id=fixture.id,
                    scope="home",
                    first_half_goals=int(total_first_half),
                    match_date=match['match_date'],
                    season="2024-25"
                )
                session.add(home_sample)
                
                # Away team sample
                away_sample = SplitSample(
                    team_id=away_team.id,
                    fixture_id=fixture.id,
                    scope="away",
                    first_half_goals=int(total_first_half),
                    match_date=match['match_date'],
                    season="2024-25"
                )
                session.add(away_sample)
                samples_created += 2
                
            except Exception as e:
                print(f"⚠️ Error storing match {match['home_team']} vs {match['away_team']}: {e}")
                continue
        
        session.commit()
        print(f"✅ Stored {fixtures_created} fixtures and {samples_created} samples")
    
    def _get_or_create_team(self, session: Session, team_name: str, league_id: int, provider: str) -> Team:
        """Get existing team or create new one."""
        
        # Check if team already exists
        statement = select(Team).where(
            Team.name == team_name,
            Team.league_id == str(league_id),
            Team.provider_name == provider
        )
        team = session.exec(statement).first()
        
        if team:
            return team
        
        # Create new team
        team = Team(
            provider_id=f"{provider}_{team_name.replace(' ', '_').lower()}",
            provider_name=provider,
            name=team_name,
            country="England",
            league_id=str(league_id)
        )
        session.add(team)
        session.commit()
        session.refresh(team)
        
        return team
    
    def get_team_statistics(self) -> pd.DataFrame:
        """Get team statistics from the data."""
        if self.data is None:
            return pd.DataFrame()
        
        # Group by team and calculate statistics
        home_stats = self.data.groupby('Home Team').agg({
            'HT Goals': ['count', 'mean', 'sum'],
            'T1': ['mean', 'sum']
        }).round(2)
        
        away_stats = self.data.groupby('Away Team').agg({
            'HT Goals': ['count', 'mean', 'sum'],
            'T2': ['mean', 'sum']
        }).round(2)
        
        # Flatten column names
        home_stats.columns = [f"home_{col[0]}_{col[1]}" for col in home_stats.columns]
        away_stats.columns = [f"away_{col[0]}_{col[1]}" for col in away_stats.columns]
        
        # Combine home and away stats
        all_teams = set(self.data['Home Team'].unique()) | set(self.data['Away Team'].unique())
        team_stats = pd.DataFrame(index=sorted(all_teams))
        
        for team in all_teams:
            if team in home_stats.index:
                team_stats.loc[team, home_stats.columns] = home_stats.loc[team]
            if team in away_stats.index:
                team_stats.loc[team, away_stats.columns] = away_stats.loc[team]
        
        return team_stats.fillna(0)


def load_premier_league_dataset(file_path: str) -> None:
    """Load Premier League dataset into the database."""
    
    loader = PremierLeagueLoader(file_path)
    
    # Load and inspect data
    data = loader.load_data()
    if data is None:
        return
    
    loader.inspect_data()
    
    # Parse matches
    matches = loader.parse_matches()
    print(f"\n📊 Parsed {len(matches)} matches")
    
    if not matches:
        print("❌ No matches parsed.")
        return
    
    # Show team statistics
    team_stats = loader.get_team_statistics()
    print(f"\n📈 Team Statistics (Top 10 by total HT goals):")
    top_teams = team_stats.sort_values('home_HT Goals_sum', ascending=False).head(10)
    print(top_teams[['home_HT Goals_count', 'home_HT Goals_mean', 'away_HT Goals_count', 'away_HT Goals_mean']])
    
    # Store in database
    with next(get_session()) as session:
        loader.store_in_database(matches, session)
    
    print("✅ Premier League dataset loaded successfully!")


if __name__ == "__main__":
    # Example usage
    file_path = "/Users/seijimatsuda/first_half_model/data/ENP_2024-2025_M.xlsx"
    load_premier_league_dataset(file_path)
