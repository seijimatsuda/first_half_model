"""Multi-league data synchronization service."""

import asyncio
import yaml
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
from fh_over.db import get_session
from fh_over.models import League, Team, Fixture

class MultiLeagueSyncService:
    """Service to sync data for multiple leagues."""
    
    def __init__(self):
        self.api_key = self._get_api_key()
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {'x-apisports-key': self.api_key} if self.api_key else {}
    
    def _get_api_key(self) -> str:
        """Get API key from config."""
        try:
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                return config.get('keys', {}).get('api_football_key', '')
        except:
            return ""
    
    async def sync_all_available_leagues(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Sync all available leagues with fixtures."""
        
        if not self.api_key:
            print("❌ API key not found")
            return {}
        
        print("🌍 Starting multi-league sync...")
        
        # Get all available leagues
        leagues_data = await self._get_all_leagues()
        if not leagues_data:
            print("❌ Could not fetch leagues")
            return {}
        
        # Filter for leagues with 2024 data
        available_leagues = [league for league in leagues_data if 2024 in league.get('seasons', [])]
        print(f"✅ Found {len(available_leagues)} leagues with 2024 data")
        
        # Sync leagues to database
        synced_leagues = await self._sync_leagues_to_db(available_leagues)
        print(f"✅ Synced {len(synced_leagues)} leagues to database")
        
        # Sync fixtures for each league
        total_fixtures = 0
        for league in synced_leagues:
            fixtures = await self._sync_league_fixtures(league['id'], days_ahead)
            total_fixtures += len(fixtures)
            print(f"   {league['name']}: {len(fixtures)} fixtures")
        
        return {
            'leagues_synced': len(synced_leagues),
            'total_fixtures': total_fixtures,
            'leagues': synced_leagues
        }
    
    async def _get_all_leagues(self) -> List[Dict]:
        """Get all available leagues from API-Football."""
        
        try:
            response = requests.get(f"{self.base_url}/leagues", headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get('response', [])
            
        except Exception as e:
            print(f"❌ Error fetching leagues: {e}")
            return []
    
    async def _sync_leagues_to_db(self, leagues_data: List[Dict]) -> List[Dict]:
        """Sync leagues to database."""
        
        session = next(get_session())
        synced_leagues = []
        
        try:
            for league_data in leagues_data:
                league_info = league_data['league']
                country_info = league_data['country']
                
                # Check if league already exists
                existing_league = session.exec(
                    session.query(League).where(League.api_id == league_info['id'])
                ).first()
                
                if not existing_league:
                    # Create new league
                    league = League(
                        api_id=league_info['id'],
                        name=league_info['name'],
                        type=league_info['type'],
                        country=country_info['name'],
                        country_code=country_info['code'],
                        logo=league_info.get('logo', ''),
                        current_season=league_data['seasons'][-1]['year'] if league_data['seasons'] else None
                    )
                    session.add(league)
                    session.commit()
                    session.refresh(league)
                else:
                    league = existing_league
                
                synced_leagues.append({
                    'id': league.id,
                    'api_id': league.api_id,
                    'name': league.name,
                    'country': league.country
                })
                
        except Exception as e:
            print(f"❌ Error syncing leagues: {e}")
            session.rollback()
        finally:
            session.close()
        
        return synced_leagues
    
    async def _sync_league_fixtures(self, league_id: int, days_ahead: int) -> List[Dict]:
        """Sync fixtures for a specific league."""
        
        try:
            # Get fixtures for the next N days
            response = requests.get(f"{self.base_url}/fixtures", 
                                  headers=self.headers,
                                  params={
                                      'league': league_id,
                                      'season': 2024,
                                      'next': days_ahead
                                  })
            response.raise_for_status()
            
            data = response.json()
            fixtures_data = data.get('response', [])
            
            if not fixtures_data:
                return []
            
            # Sync fixtures to database
            session = next(get_session())
            synced_fixtures = []
            
            try:
                for fixture_data in fixtures_data:
                    fixture_info = fixture_data['fixture']
                    teams_info = fixture_data['teams']
                    league_info = fixture_data['league']
                    
                    # Parse match date
                    match_date = datetime.fromisoformat(fixture_info['date'].replace('Z', '+00:00'))
                    
                    # Check if fixture already exists
                    existing_fixture = session.exec(
                        session.query(Fixture).where(Fixture.api_id == fixture_info['id'])
                    ).first()
                    
                    if not existing_fixture:
                        # Create new fixture
                        fixture = Fixture(
                            api_id=fixture_info['id'],
                            league_id=league_id,
                            league_name=league_info['name'],
                            league_type=league_info['type'],
                            country=league_info['country'],
                            home_team_name=teams_info['home']['name'],
                            away_team_name=teams_info['away']['name'],
                            match_date=match_date,
                            status=fixture_info['status']['short'],
                            home_score=fixture_info['score']['fulltime']['home'],
                            away_score=fixture_info['score']['fulltime']['away'],
                            home_first_half_score=fixture_info['score']['halftime']['home'],
                            away_first_half_score=fixture_info['score']['halftime']['away']
                        )
                        session.add(fixture)
                        session.commit()
                        session.refresh(fixture)
                    else:
                        fixture = existing_fixture
                    
                    synced_fixtures.append({
                        'id': fixture.id,
                        'api_id': fixture.api_id,
                        'home_team': fixture.home_team_name,
                        'away_team': fixture.away_team_name,
                        'match_date': fixture.match_date
                    })
                    
            except Exception as e:
                print(f"❌ Error syncing fixtures for league {league_id}: {e}")
                session.rollback()
            finally:
                session.close()
            
            return synced_fixtures
            
        except Exception as e:
            print(f"❌ Error fetching fixtures for league {league_id}: {e}")
            return []
    
    async def sync_top_leagues(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Sync only top-tier leagues."""
        
        # Define top leagues by ID
        top_league_ids = [
            39,   # Premier League
            40,   # Championship
            41,   # League One
            42,   # League Two
            140,  # La Liga
            141,  # Segunda División
            78,   # Bundesliga
            79,   # 2. Bundesliga
            135,  # Serie A
            136,  # Serie B
            179,  # Scottish Premiership
            180,  # Scottish Championship
            144,  # Jupiler Pro League (Belgium)
            71,   # Serie A (Brazil)
            72,   # Serie B (Brazil)
        ]
        
        print(f"🏆 Syncing top {len(top_league_ids)} leagues...")
        
        total_fixtures = 0
        synced_leagues = []
        
        for league_id in top_league_ids:
            try:
                # Get league info
                response = requests.get(f"{self.base_url}/leagues", 
                                      headers=self.headers,
                                      params={'id': league_id})
                response.raise_for_status()
                
                data = response.json()
                if data.get('response'):
                    league_data = data['response'][0]
                    league_name = league_data['league']['name']
                    country = league_data['country']['name']
                    
                    print(f"   Syncing {league_name} ({country})...", end=" ")
                    
                    # Sync fixtures
                    fixtures = await self._sync_league_fixtures(league_id, days_ahead)
                    total_fixtures += len(fixtures)
                    
                    synced_leagues.append({
                        'id': league_id,
                        'name': league_name,
                        'country': country,
                        'fixtures': len(fixtures)
                    })
                    
                    print(f"✅ {len(fixtures)} fixtures")
                    
            except Exception as e:
                print(f"❌ Error syncing league {league_id}: {e}")
        
        return {
            'leagues_synced': len(synced_leagues),
            'total_fixtures': total_fixtures,
            'leagues': synced_leagues
        }

async def sync_all_leagues(days_ahead: int = 7, top_only: bool = False) -> Dict[str, Any]:
    """Main function to sync all leagues."""
    
    service = MultiLeagueSyncService()
    
    if top_only:
        return await service.sync_top_leagues(days_ahead)
    else:
        return await service.sync_all_available_leagues(days_ahead)
