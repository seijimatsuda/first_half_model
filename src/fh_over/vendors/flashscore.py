"""FlashScore web scraper adapter for soccer data."""

import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import DataProviderAdapter, LeagueInfo, TeamInfo, FixtureInfo, FirstHalfSample


class FlashScoreAdapter(DataProviderAdapter):
    """FlashScore web scraper adapter for soccer data."""
    
    def __init__(self, api_key: str = ""):
        super().__init__(api_key, "https://www.flashscore.com")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def _make_request(self, url: str) -> BeautifulSoup:
        """Make request to FlashScore and return parsed HTML."""
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    
    async def list_leagues(self) -> List[LeagueInfo]:
        """List all available leagues from FlashScore."""
        try:
            # FlashScore soccer leagues page
            url = "https://www.flashscore.com/football/"
            soup = await self._make_request(url)
            
            leagues = []
            
            # Find league links
            league_links = soup.find_all('a', href=re.compile(r'/football/[^/]+/$'))
            
            for link in league_links:
                href = link.get('href', '')
                name = link.get_text(strip=True)
                
                if name and href and not name.startswith('More'):
                    # Extract league ID from href
                    league_id = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                    
                    leagues.append(LeagueInfo(
                        provider_id=league_id,
                        provider_name=self.provider_name,
                        name=name,
                        country=None,  # FlashScore doesn't always show country in main list
                        season="2024-25"  # Current season
                    ))
            
            return leagues[:20]  # Limit to top 20 leagues to avoid overwhelming
            
        except Exception as e:
            print(f"Error fetching leagues from FlashScore: {e}")
            return []
    
    async def list_fixtures(
        self,
        date_range: Optional[tuple[datetime, datetime]] = None,
        season: Optional[str] = None,
        league_ids: Optional[List[str]] = None
    ) -> List[FixtureInfo]:
        """List fixtures from FlashScore."""
        fixtures = []
        
        try:
            # If no specific leagues provided, get top leagues
            if not league_ids:
                leagues = await self.list_leagues()
                league_ids = [league.provider_id for league in leagues[:5]]  # Limit to top 5 leagues
            
            # Get fixtures for each league
            for league_id in league_ids:
                try:
                    # Construct league URL
                    league_url = f"https://www.flashscore.com/football/{league_id}/"
                    soup = await self._make_request(league_url)
                    
                    # Find match elements
                    matches = soup.find_all('div', class_=re.compile(r'event__match'))
                    
                    for match in matches:
                        try:
                            fixture = await self._parse_match_element(match, league_id)
                            if fixture:
                                # Check date range filter
                                if date_range:
                                    start_date, end_date = date_range
                                    if not (start_date <= fixture.match_date <= end_date):
                                        continue
                                
                                fixtures.append(fixture)
                        except Exception as e:
                            print(f"Error parsing match: {e}")
                            continue
                
                except Exception as e:
                    print(f"Error fetching fixtures for league {league_id}: {e}")
                    continue
            
            return fixtures
            
        except Exception as e:
            print(f"Error listing fixtures from FlashScore: {e}")
            return []
    
    async def _parse_match_element(self, match_element, league_id: str) -> Optional[FixtureInfo]:
        """Parse a single match element from FlashScore."""
        try:
            # Extract match ID
            match_id = match_element.get('id', '').replace('g_1_', '')
            if not match_id:
                return None
            
            # Extract team names
            home_team_elem = match_element.find('div', class_=re.compile(r'event__participant--home'))
            away_team_elem = match_element.find('div', class_=re.compile(r'event__participant--away'))
            
            if not home_team_elem or not away_team_elem:
                return None
            
            home_team_name = home_team_elem.get_text(strip=True)
            away_team_name = away_team_elem.get_text(strip=True)
            
            # Extract match date/time
            time_elem = match_element.find('div', class_=re.compile(r'event__time'))
            if not time_elem:
                return None
            
            time_text = time_elem.get_text(strip=True)
            match_date = await self._parse_match_time(time_text)
            
            # Extract scores
            home_score = None
            away_score = None
            home_first_half_score = None
            away_first_half_score = None
            
            score_elem = match_element.find('div', class_=re.compile(r'event__score'))
            if score_elem:
                score_text = score_elem.get_text(strip=True)
                if ':' in score_text:
                    try:
                        home_score, away_score = map(int, score_text.split(':'))
                    except ValueError:
                        pass
            
            # Extract first-half scores (if available)
            first_half_elem = match_element.find('div', class_=re.compile(r'event__part--1'))
            if first_half_elem:
                first_half_text = first_half_elem.get_text(strip=True)
                if ':' in first_half_text:
                    try:
                        home_first_half_score, away_first_half_score = map(int, first_half_text.split(':'))
                    except ValueError:
                        pass
            
            # Determine match status
            status = "scheduled"
            if score_elem and score_elem.get_text(strip=True):
                status = "finished"
            
            return FixtureInfo(
                provider_id=match_id,
                provider_name=self.provider_name,
                home_team_id=f"home_{home_team_name.lower().replace(' ', '_')}",
                away_team_id=f"away_{away_team_name.lower().replace(' ', '_')}",
                league_id=league_id,
                league_name=league_id.replace('_', ' ').title(),
                match_date=match_date,
                season="2024-25",
                status=status,
                home_score=home_score,
                away_score=away_score,
                home_first_half_score=home_first_half_score,
                away_first_half_score=away_first_half_score
            )
            
        except Exception as e:
            print(f"Error parsing match element: {e}")
            return None
    
    async def _parse_match_time(self, time_text: str) -> datetime:
        """Parse match time from FlashScore format."""
        try:
            # Handle different time formats
            now = datetime.now()
            
            if ':' in time_text:
                # Time format like "15:30"
                time_parts = time_text.split(':')
                if len(time_parts) == 2:
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    
                    # Assume today's date
                    match_date = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # If time has passed, assume tomorrow
                    if match_date < now:
                        match_date += timedelta(days=1)
                    
                    return match_date
            
            elif time_text.lower() in ['ft', 'finished', 'ended']:
                # Finished match
                return now
            
            elif time_text.lower() in ['live', 'ht', '1h']:
                # Live match
                return now
            
            else:
                # Default to current time
                return now
                
        except Exception as e:
            print(f"Error parsing match time '{time_text}': {e}")
            return datetime.now()
    
    async def get_team_first_half_samples(
        self,
        team_id: str,
        scope: str = "home",
        season: Optional[str] = None,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> List[FirstHalfSample]:
        """Get first-half goal samples for a team from FlashScore."""
        samples = []
        
        try:
            # Extract team name from team_id
            team_name = team_id.replace('home_', '').replace('away_', '').replace('_', ' ')
            
            # Search for team's recent matches
            # This is a simplified approach - in practice, you'd need to find the team's page
            # and scrape their match history
            
            # For now, return empty list as this requires more complex scraping
            print(f"Note: Team-specific sample collection not fully implemented for FlashScore")
            return samples
            
        except Exception as e:
            print(f"Error fetching first-half samples for team {team_id}: {e}")
            return []
    
    async def get_fixture_details(self, fixture_id: str) -> Optional[FixtureInfo]:
        """Get detailed fixture information from FlashScore."""
        try:
            # Construct match URL
            match_url = f"https://www.flashscore.com/match/{fixture_id}/"
            soup = await self._make_request(match_url)
            
            # Parse detailed match information
            # This would require more specific parsing of the match detail page
            
            print(f"Note: Detailed fixture parsing not fully implemented for FlashScore")
            return None
            
        except Exception as e:
            print(f"Error fetching fixture details for {fixture_id}: {e}")
            return None
