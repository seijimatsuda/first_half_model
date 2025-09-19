"""Data synchronization service for populating database with real data."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, and_

from fh_over.db import get_session
from fh_over.models import League, Team, Fixture, SplitSample, Result
from fh_over.vendors.api_football import ApiFootballAdapter
from fh_over.vendors.flashscore import FlashScoreAdapter
from fh_over.vendors.sportradar import SportradarAdapter
from fh_over.config import config


class DataSyncService:
    """Service for synchronizing data from external providers."""
    
    def __init__(self):
        self.config = config
    
    async def sync_leagues(self, provider_name: str = "api_football") -> List[League]:
        """Sync leagues from a data provider."""
        leagues = []
        
        try:
            if provider_name == "api_football" and config.providers.api_football_enabled:
                api_key = config.get_provider_api_key("api_football")
                if not api_key:
                    print("❌ No API key found for API-Football")
                    return []
                async with ApiFootballAdapter(api_key) as adapter:
                    league_infos = await adapter.list_leagues()
                    leagues = await self._save_leagues(league_infos)
            
            elif provider_name == "flashscore" and config.providers.flashscore_enabled:
                async with FlashScoreAdapter() as adapter:
                    league_infos = await adapter.list_leagues()
                    leagues = await self._save_leagues(league_infos)
            
            elif provider_name == "sportradar" and config.providers.sportradar_enabled:
                async with SportradarAdapter(config.providers.sportradar_api_key) as adapter:
                    league_infos = await adapter.list_leagues()
                    leagues = await self._save_leagues(league_infos)
            
            print(f"✅ Synced {len(leagues)} leagues from {provider_name}")
            return leagues
            
        except Exception as e:
            print(f"❌ Error syncing leagues from {provider_name}: {e}")
            return []
    
    async def sync_fixtures(
        self,
        league_ids: Optional[List[str]] = None,
        days_back: int = 30,
        provider_name: str = "api_football"
    ) -> List[Fixture]:
        """Sync fixtures from a data provider."""
        fixtures = []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            if provider_name == "api_football" and config.providers.api_football_enabled:
                api_key = config.get_provider_api_key("api_football")
                if not api_key:
                    print("❌ No API key found for API-Football")
                    return []
                async with ApiFootballAdapter(api_key) as adapter:
                    fixture_infos = await adapter.list_fixtures(
                        date_range=(start_date, end_date),
                        league_ids=league_ids
                    )
                    fixtures = await self._save_fixtures(fixture_infos)
            
            elif provider_name == "flashscore" and config.providers.flashscore_enabled:
                async with FlashScoreAdapter() as adapter:
                    fixture_infos = await adapter.list_fixtures(
                        date_range=(start_date, end_date),
                        league_ids=league_ids
                    )
                    fixtures = await self._save_fixtures(fixture_infos)
            
            elif provider_name == "sportradar" and config.providers.sportradar_enabled:
                async with SportradarAdapter(config.providers.sportradar_api_key) as adapter:
                    fixture_infos = await adapter.list_fixtures(
                        date_range=(start_date, end_date),
                        league_ids=league_ids
                    )
                    fixtures = await self._save_fixtures(fixture_infos)
            
            print(f"✅ Synced {len(fixtures)} fixtures from {provider_name}")
            return fixtures
            
        except Exception as e:
            print(f"❌ Error syncing fixtures from {provider_name}: {e}")
            return []
    
    async def sync_team_samples(
        self,
        team_id: str,
        scope: str = "home",
        days_back: int = 90,
        provider_name: str = "api_football"
    ) -> List[SplitSample]:
        """Sync first-half samples for a team."""
        samples = []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            if provider_name == "api_football" and config.providers.api_football_enabled:
                api_key = config.get_provider_api_key("api_football")
                if not api_key:
                    print("❌ No API key found for API-Football")
                    return []
                async with ApiFootballAdapter(api_key) as adapter:
                    sample_infos = await adapter.get_team_first_half_samples(
                        team_id=team_id,
                        scope=scope,
                        date_range=(start_date, end_date)
                    )
                    samples = await self._save_team_samples(sample_infos)
            
            elif provider_name == "sportradar" and config.providers.sportradar_enabled:
                async with SportradarAdapter(config.providers.sportradar_api_key) as adapter:
                    sample_infos = await adapter.get_team_first_half_samples(
                        team_id=team_id,
                        scope=scope,
                        date_range=(start_date, end_date)
                    )
                    samples = await self._save_team_samples(sample_infos)
            
            print(f"✅ Synced {len(samples)} samples for team {team_id} ({scope}) from {provider_name}")
            return samples
            
        except Exception as e:
            print(f"❌ Error syncing samples for team {team_id}: {e}")
            return []
    
    async def _save_leagues(self, league_infos: List) -> List[League]:
        """Save league information to database."""
        leagues = []
        
        with next(get_session()) as session:
            for league_info in league_infos:
                # Check if league already exists
                existing = session.exec(
                    select(League).where(
                        and_(
                            League.provider_id == league_info.provider_id,
                            League.provider_name == league_info.provider_name
                        )
                    )
                ).first()
                
                if existing:
                    leagues.append(existing)
                    continue
                
                # Create new league
                league = League(
                    provider_id=league_info.provider_id,
                    provider_name=league_info.provider_name,
                    name=league_info.name,
                    country=league_info.country,
                    season=league_info.season
                )
                
                session.add(league)
                leagues.append(league)
            
            session.commit()
            return leagues
    
    async def _save_fixtures(self, fixture_infos: List) -> List[Fixture]:
        """Save fixture information to database."""
        fixtures = []
        
        with next(get_session()) as session:
            for fixture_info in fixture_infos:
                # Check if fixture already exists
                existing = session.exec(
                    select(Fixture).where(
                        and_(
                            Fixture.provider_id == fixture_info.provider_id,
                            Fixture.provider_name == fixture_info.provider_name
                        )
                    )
                ).first()
                
                if existing:
                    fixtures.append(existing)
                    continue
                
                # Get or create teams
                home_team = await self._get_or_create_team(
                    session, fixture_info.home_team_id, fixture_info.provider_name
                )
                away_team = await self._get_or_create_team(
                    session, fixture_info.away_team_id, fixture_info.provider_name
                )
                
                # Get or create league
                league = await self._get_or_create_league(
                    session, fixture_info.league_id, fixture_info.provider_name, fixture_info.league_name
                )
                
                # Create fixture
                fixture = Fixture(
                    provider_id=fixture_info.provider_id,
                    provider_name=fixture_info.provider_name,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    league_id=league.id,
                    league_name=fixture_info.league_name,
                    match_date=fixture_info.match_date,
                    season=fixture_info.season,
                    status=fixture_info.status,
                    home_score=fixture_info.home_score,
                    away_score=fixture_info.away_score,
                    home_first_half_score=fixture_info.home_first_half_score,
                    away_first_half_score=fixture_info.away_first_half_score
                )
                
                session.add(fixture)
                fixtures.append(fixture)
            
            session.commit()
            return fixtures
    
    async def _save_team_samples(self, sample_infos: List) -> List[SplitSample]:
        """Save team sample information to database."""
        samples = []
        
        with next(get_session()) as session:
            for sample_info in sample_infos:
                # Check if sample already exists
                existing = session.exec(
                    select(SplitSample).where(
                        and_(
                            SplitSample.fixture_id == sample_info.fixture_id,
                            SplitSample.team_id == sample_info.team_id,
                            SplitSample.scope == sample_info.scope
                        )
                    )
                ).first()
                
                if existing:
                    samples.append(existing)
                    continue
                
                # Create sample
                sample = SplitSample(
                    team_id=sample_info.team_id,
                    fixture_id=sample_info.fixture_id,
                    scope=sample_info.scope,
                    first_half_goals=sample_info.first_half_goals,
                    match_date=sample_info.match_date,
                    season=sample_info.season
                )
                
                session.add(sample)
                samples.append(sample)
            
            session.commit()
            return samples
    
    async def _get_or_create_team(self, session: Session, team_id: str, provider_name: str) -> Team:
        """Get or create a team."""
        existing = session.exec(
            select(Team).where(
                and_(
                    Team.provider_id == team_id,
                    Team.provider_name == provider_name
                )
            )
        ).first()
        
        if existing:
            return existing
        
        # Create new team
        team = Team(
            provider_id=team_id,
            provider_name=provider_name,
            name=f"Team {team_id}",  # Default name, could be improved
            country=None
        )
        
        session.add(team)
        session.commit()
        session.refresh(team)
        return team
    
    async def _get_or_create_league(self, session: Session, league_id: str, provider_name: str, league_name: str) -> League:
        """Get or create a league."""
        existing = session.exec(
            select(League).where(
                and_(
                    League.provider_id == league_id,
                    League.provider_name == provider_name
                )
            )
        ).first()
        
        if existing:
            return existing
        
        # Create new league
        league = League(
            provider_id=league_id,
            provider_name=provider_name,
            name=league_name,
            country=None,
            season="2024-25"
        )
        
        session.add(league)
        session.commit()
        session.refresh(league)
        return league


async def sync_all_data(provider_name: str = "api_football", days_back: int = 30) -> Dict[str, Any]:
    """Sync all data from a provider."""
    sync_service = DataSyncService()
    
    print(f"🚀 Starting data sync from {provider_name}...")
    
    # Sync leagues
    leagues = await sync_service.sync_leagues(provider_name)
    
    # Sync fixtures for specific leagues (Premier League, La Liga, etc.)
    major_league_ids = ['39', '140', '135', '78', '61']  # Premier League, La Liga, Serie A, Bundesliga, Ligue 1
    fixtures = await sync_service.sync_fixtures(major_league_ids, days_back, provider_name)
    
    # Sync samples for teams in fixtures (simplified for now)
    team_samples = []
    print(f"✅ Synced {len(fixtures)} fixtures")
    print("Note: Team samples sync skipped to avoid session issues")
    
    print(f"✅ Data sync complete!")
    print(f"   - Leagues: {len(leagues)}")
    print(f"   - Fixtures: {len(fixtures)}")
    print(f"   - Team samples: {len(team_samples)}")
    
    return {
        "leagues": len(leagues),
        "fixtures": len(fixtures),
        "team_samples": len(team_samples)
    }
