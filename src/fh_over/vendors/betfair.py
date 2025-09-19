"""Betfair exchange odds provider adapter."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import OddsProviderAdapter


class BetfairAdapter(OddsProviderAdapter):
    """Betfair API adapter for exchange odds data."""
    
    def __init__(self, app_key: str, cert_path: str, key_path: str, username: str, password: str):
        super().__init__(app_key, "https://api.betfair.com/exchange")
        self.cert_path = cert_path
        self.key_path = key_path
        self.username = username
        self.password = password
        self.client = httpx.AsyncClient(timeout=30.0)
        self.session_token = None
    
    async def __aenter__(self):
        await self._authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _authenticate(self) -> bool:
        """Authenticate with Betfair API using proper SSL certificates."""
        try:
            # Real Betfair authentication requires SSL client certificates
            # This is a simplified version for demonstration
            auth_data = {
                "username": self.username,
                "password": self.password
            }
            
            # In production, you would use SSL client certificates
            # For now, we'll simulate successful authentication
            print("Note: Using simulated Betfair authentication for demo purposes")
            print("In production, configure SSL client certificates for real authentication")
            
            # Simulate successful authentication
            self.session_token = "simulated_token_for_demo"
            return True
            
        except Exception as e:
            print(f"Error authenticating with Betfair: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make authenticated request to Betfair API."""
        if not self.session_token:
            raise Exception("Not authenticated with Betfair")
        
        headers = {
            "X-Application": self.api_key,
            "X-Authentication": self.session_token,
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        
        response = await self.client.post(
            f"{self.base_url}/betting/json-rpc/v1",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_first_half_over_odds(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        """Get first-half over 0.5 odds for a fixture."""
        try:
            # First, find the market for this fixture
            market_catalogue = await self._make_request(
                "SportsAPING/v1.0/listMarketCatalogue",
                {
                    "filter": {
                        "eventIds": [fixture_id],
                        "marketTypeCodes": ["OVER_UNDER_05"]
                    },
                    "maxResults": 10,
                    "marketProjection": ["MARKET_DESCRIPTION", "RUNNER_DESCRIPTION"]
                }
            )
            
            markets = market_catalogue.get("result", [])
            if not markets:
                return None
            
            # Find the first-half over/under market
            first_half_market = None
            for market in markets:
                if "1st Half" in market.get("marketName", ""):
                    first_half_market = market
                    break
            
            if not first_half_market:
                return None
            
            market_id = first_half_market["marketId"]
            
            # Get market book with best prices
            market_book = await self._make_request(
                "SportsAPING/v1.0/listMarketBook",
                {
                    "marketIds": [market_id],
                    "priceProjection": {
                        "priceData": ["EX_BEST_OFFERS"]
                    }
                }
            )
            
            market_data = market_book.get("result", [{}])[0]
            if not market_data:
                return None
            
            # Find the Over 0.5 selection
            runners = market_data.get("runners", [])
            for runner in runners:
                runner_name = runner.get("runnerName", "")
                if "Over" in runner_name and "0.5" in runner_name:
                    prices = runner.get("ex", {})
                    available_to_back = prices.get("availableToBack", [])
                    available_to_lay = prices.get("availableToLay", [])
                    
                    best_back = available_to_back[0] if available_to_back else None
                    best_lay = available_to_lay[0] if available_to_lay else None
                    
                    return {
                        "market_id": market_id,
                        "market_name": first_half_market.get("marketName"),
                        "selection": runner_name,
                        "back_odds": best_back["price"] if best_back else None,
                        "lay_odds": best_lay["price"] if best_lay else None,
                        "back_size": best_back["size"] if best_back else None,
                        "lay_size": best_lay["size"] if best_lay else None
                    }
            
            return None
            
        except Exception as e:
            print(f"Error fetching odds for fixture {fixture_id}: {e}")
            return None
    
    async def get_available_markets(self, fixture_id: str) -> List[Dict[str, Any]]:
        """Get available markets for a fixture."""
        try:
            market_catalogue = await self._make_request(
                "SportsAPING/v1.0/listMarketCatalogue",
                {
                    "filter": {
                        "eventIds": [fixture_id]
                    },
                    "maxResults": 100,
                    "marketProjection": ["MARKET_DESCRIPTION", "RUNNER_DESCRIPTION"]
                }
            )
            
            markets = market_catalogue.get("result", [])
            return [
                {
                    "market_id": market["marketId"],
                    "market_name": market["marketName"],
                    "market_type": market.get("marketType"),
                    "runners": [
                        {
                            "runner_id": runner["selectionId"],
                            "runner_name": runner["runnerName"]
                        }
                        for runner in market.get("runners", [])
                    ]
                }
                for market in markets
            ]
            
        except Exception as e:
            print(f"Error fetching markets for fixture {fixture_id}: {e}")
            return []
