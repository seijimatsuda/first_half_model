"""TheOddsAPI odds provider adapter."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import OddsProviderAdapter


class TheOddsApiAdapter(OddsProviderAdapter):
    """TheOddsAPI adapter for odds data."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.the-odds-api.com/v4")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make authenticated request to TheOddsAPI."""
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_first_half_over_odds(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        """Get first-half over 0.5 odds for a fixture."""
        try:
            # TheOddsAPI doesn't have direct fixture ID lookup, so we need to search by date
            # This is a limitation - we'd need to map fixture IDs to dates/teams
            # For now, return None as this would require additional mapping logic
            print(f"TheOddsAPI: get_first_half_over_odds not implemented for fixture {fixture_id} (requires date/team mapping)")
            return None
            
        except Exception as e:
            print(f"Error fetching odds for fixture {fixture_id}: {e}")
            return None
    
    async def get_available_markets(self, fixture_id: str) -> List[Dict[str, Any]]:
        """Get available markets for a fixture."""
        try:
            # Similar limitation as above - would need date/team mapping
            print(f"TheOddsAPI: get_available_markets not implemented for fixture {fixture_id} (requires date/team mapping)")
            return []
            
        except Exception as e:
            print(f"Error fetching markets for fixture {fixture_id}: {e}")
            return []
    
    async def get_odds_by_sport(self, sport: str = "soccer", regions: str = "us,uk,eu") -> List[Dict[str, Any]]:
        """Get odds for a specific sport (helper method for bulk fetching)."""
        try:
            params = {
                "sport": sport,
                "regions": regions,
                "markets": "h2h,spreads,totals",
                "oddsFormat": "decimal",
                "dateFormat": "iso"
            }
            
            data = await self._make_request("sports/soccer/odds", params)
            return data
            
        except Exception as e:
            print(f"Error fetching odds for sport {sport}: {e}")
            return []
    
    def _find_first_half_over_market(self, odds_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find first-half over 0.5 market in odds data."""
        for bookmaker in odds_data:
            markets = bookmaker.get("bookmakers", [])
            for market in markets:
                if market.get("key") == "totals":
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        if (outcome.get("description") == "Over" and 
                            outcome.get("point") == 0.5 and
                            "1st Half" in market.get("title", "")):
                            return {
                                "bookmaker": bookmaker.get("title"),
                                "back_odds": outcome.get("price"),
                                "market": market.get("title"),
                                "selection": outcome.get("description"),
                                "point": outcome.get("point")
                            }
        return None
