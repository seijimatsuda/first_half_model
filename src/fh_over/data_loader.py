"""Data loader for Excel datasets and backtesting."""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json

from fh_over.models import Team, Fixture, SplitSample, League
from fh_over.db import get_session
from sqlmodel import Session, select


class ExcelDataLoader:
    """Data loader for Excel datasets."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.data = None
        self.teams_map = {}
        self.leagues_map = {}
    
    def load_data(self) -> pd.DataFrame:
        """Load data from Excel file."""
        try:
            # Try to read the Excel file
            self.data = pd.read_excel(self.file_path)
            print(f"✅ Loaded {len(self.data)} rows from {self.file_path}")
            print(f"Columns: {list(self.data.columns)}")
            return self.data
        except Exception as e:
            print(f"❌ Error loading Excel file: {e}")
            return None
    
    def inspect_data(self) -> None:
        """Inspect the loaded data structure."""
        if self.data is None:
            print("No data loaded. Call load_data() first.")
            return
        
        print("\n📊 Dataset Overview:")
        print(f"Shape: {self.data.shape}")
        print(f"Columns: {list(self.data.columns)}")
        print(f"\nFirst 5 rows:")
        print(self.data.head())
        print(f"\nData types:")
        print(self.data.dtypes)
        print(f"\nSample values:")
        for col in self.data.columns:
            print(f"{col}: {self.data[col].iloc[0] if len(self.data) > 0 else 'N/A'}")
    
    def detect_columns(self) -> Dict[str, str]:
        """Auto-detect column mappings for common field names."""
        if self.data is None:
            return {}
        
        column_mappings = {}
        columns_lower = [col.lower() for col in self.data.columns]
        
        # Common patterns for different fields
        patterns = {
            'home_team': ['home', 'home_team', 'home team', 'team_home', 'team home'],
            'away_team': ['away', 'away_team', 'away team', 'team_away', 'team away'],
            'match_date': ['date', 'match_date', 'match date', 'datetime', 'time'],
            'home_score': ['home_score', 'home score', 'h_score', 'hscore', 'home_goals'],
            'away_score': ['away_score', 'away score', 'a_score', 'ascore', 'away_goals'],
            'home_first_half': ['home_ht', 'home ht', 'home_first_half', 'home first half', 'h_ht', 'hht'],
            'away_first_half': ['away_ht', 'away ht', 'away_first_half', 'away first half', 'a_ht', 'aht'],
            'league': ['league', 'competition', 'comp', 'division'],
            'season': ['season', 'year', 'campaign']
        }
        
        for field, patterns_list in patterns.items():
            for pattern in patterns_list:
                for i, col in enumerate(columns_lower):
                    if pattern in col:
                        column_mappings[field] = self.data.columns[i]
                        break
                if field in column_mappings:
                    break
        
        return column_mappings
    
    def parse_match_data(self, column_mappings: Dict[str, str]) -> List[Dict[str, Any]]:
        """Parse match data using column mappings."""
        if self.data is None:
            return []
        
        matches = []
        
        for idx, row in self.data.iterrows():
            try:
                # Extract basic match info
                home_team = str(row[column_mappings.get('home_team', '')]) if column_mappings.get('home_team') else f"Home_{idx}"
                away_team = str(row[column_mappings.get('away_team', '')]) if column_mappings.get('away_team') else f"Away_{idx}"
                
                # Parse date
                date_col = column_mappings.get('match_date', '')
                if date_col and pd.notna(row[date_col]):
                    if isinstance(row[date_col], str):
                        match_date = pd.to_datetime(row[date_col])
                    else:
                        match_date = row[date_col]
                else:
                    match_date = datetime.now()
                
                # Parse scores
                home_score = self._safe_int(row[column_mappings.get('home_score', '')]) if column_mappings.get('home_score') else None
                away_score = self._safe_int(row[column_mappings.get('away_score', '')]) if column_mappings.get('away_score') else None
                home_first_half = self._safe_int(row[column_mappings.get('home_first_half', '')]) if column_mappings.get('home_first_half') else None
                away_first_half = self._safe_int(row[column_mappings.get('away_first_half', '')]) if column_mappings.get('away_first_half') else None
                
                # League info
                league = str(row[column_mappings.get('league', '')]) if column_mappings.get('league') else "Premier League"
                season = str(row[column_mappings.get('season', '')]) if column_mappings.get('season') else "2024-25"
                
                match_data = {
                    'home_team': home_team,
                    'away_team': away_team,
                    'match_date': match_date,
                    'home_score': home_score,
                    'away_score': away_score,
                    'home_first_half': home_first_half,
                    'away_first_half': away_first_half,
                    'league': league,
                    'season': season,
                    'row_index': idx
                }
                
                matches.append(match_data)
                
            except Exception as e:
                print(f"⚠️ Error parsing row {idx}: {e}")
                continue
        
        return matches
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to int."""
        if pd.isna(value) or value == '' or value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def store_in_database(self, matches: List[Dict[str, Any]], session: Session) -> None:
        """Store parsed matches in the database."""
        
        # Create league
        league_name = matches[0]['league'] if matches else "Premier League"
        league = League(
            provider_id="excel_loader",
            provider_name="excel",
            name=league_name,
            country="England",
            season=matches[0]['season'] if matches else "2024-25",
            is_active=True
        )
        session.add(league)
        session.commit()
        session.refresh(league)
        self.leagues_map[league_name] = league.id
        
        # Create teams and store fixtures
        for match in matches:
            # Create/get home team
            home_team = self._get_or_create_team(
                session, match['home_team'], league.id, "excel_loader"
            )
            
            # Create/get away team
            away_team = self._get_or_create_team(
                session, match['away_team'], league.id, "excel_loader"
            )
            
            # Create fixture
            fixture = Fixture(
                provider_id=f"excel_{match['row_index']}",
                provider_name="excel",
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                league_id=str(league.id),
                league_name=league_name,
                match_date=match['match_date'],
                season=match['season'],
                status="finished" if match['home_score'] is not None else "scheduled",
                home_score=match['home_score'],
                away_score=match['away_score'],
                home_first_half_score=match['home_first_half'],
                away_first_half_score=match['away_first_half']
            )
            session.add(fixture)
            session.commit()
            session.refresh(fixture)
            
            # Create first-half samples if we have the data
            if match['home_first_half'] is not None and match['away_first_half'] is not None:
                total_first_half = match['home_first_half'] + match['away_first_half']
                
                # Home team sample
                home_sample = SplitSample(
                    team_id=home_team.id,
                    fixture_id=fixture.id,
                    scope="home",
                    first_half_goals=total_first_half,
                    match_date=match['match_date'],
                    season=match['season']
                )
                session.add(home_sample)
                
                # Away team sample
                away_sample = SplitSample(
                    team_id=away_team.id,
                    fixture_id=fixture.id,
                    scope="away",
                    first_half_goals=total_first_half,
                    match_date=match['match_date'],
                    season=match['season']
                )
                session.add(away_sample)
        
        session.commit()
        print(f"✅ Stored {len(matches)} matches in database")
    
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


def load_excel_dataset(file_path: str) -> None:
    """Load Excel dataset into the database."""
    
    loader = ExcelDataLoader(file_path)
    
    # Load and inspect data
    data = loader.load_data()
    if data is None:
        return
    
    loader.inspect_data()
    
    # Auto-detect column mappings
    mappings = loader.detect_columns()
    print(f"\n🔍 Detected column mappings:")
    for field, column in mappings.items():
        print(f"  {field}: {column}")
    
    # Parse matches
    matches = loader.parse_match_data(mappings)
    print(f"\n📊 Parsed {len(matches)} matches")
    
    if not matches:
        print("❌ No matches parsed. Check column mappings.")
        return
    
    # Store in database
    with next(get_session()) as session:
        loader.store_in_database(matches, session)
    
    print("✅ Dataset loaded successfully!")


if __name__ == "__main__":
    # Example usage
    file_path = "/Users/seijimatsuda/first_half_model/data/ENP_2024-2025_M.xlsx"
    load_excel_dataset(file_path)
