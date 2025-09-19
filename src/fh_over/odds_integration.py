#!/usr/bin/env python3
"""
Comprehensive Odds Integration System

This module provides a unified interface for fetching odds from multiple sources
(Betfair, TheOddsAPI, mock data) and calculating accurate PnL.
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from .vendors.betfair import BetfairAdapter
from .vendors.theoddsapi import TheOddsApiAdapter

class OddsIntegrationService:
    """Unified service for odds integration and PnL calculation."""
    
    def __init__(self, config):
        self.config = config
        self.betfair_adapter = None
        self.theoddsapi_adapter = None
        
    async def initialize_adapters(self):
        """Initialize all available odds adapters."""
        # Initialize Betfair adapter if configured
        if (self.config.get_provider_api_key("betfair_app_key") and 
            self.config.get_provider_api_key("betfair_cert_path")):
            self.betfair_adapter = BetfairAdapter(
                app_key=self.config.get_provider_api_key("betfair_app_key"),
                cert_path=self.config.get_provider_api_key("betfair_cert_path"),
                key_path=self.config.get_provider_api_key("betfair_key_path"),
                username=self.config.get_provider_api_key("betfair_username"),
                password=self.config.get_provider_api_key("betfair_password")
            )
        
        # Initialize TheOddsAPI adapter if configured
        if self.config.get_provider_api_key("theoddsapi_key"):
            self.theoddsapi_adapter = TheOddsApiAdapter(
                api_key=self.config.get_provider_api_key("theoddsapi_key")
            )
    
    async def get_odds_for_fixture(self, fixture_id: str, home_team: str, away_team: str, 
                                 match_date: date) -> Optional[Dict[str, float]]:
        """Get odds for a specific fixture from available sources."""
        odds_sources = []
        
        # Try Betfair first (if available)
        if self.betfair_adapter:
            try:
                async with self.betfair_adapter as bf:
                    betfair_odds = await bf.get_first_half_over_odds(fixture_id)
                    if betfair_odds and betfair_odds.get('back_odds'):
                        odds_sources.append({
                            'source': 'betfair',
                            'over_odds': betfair_odds['back_odds'],
                            'under_odds': 1.0 / (1.0 - 1.0/betfair_odds['back_odds']) if betfair_odds['back_odds'] > 1 else None
                        })
            except Exception as e:
                print(f"Error fetching Betfair odds for {fixture_id}: {e}")
        
        # Try TheOddsAPI (if available)
        if self.theoddsapi_adapter:
            try:
                theoddsapi_odds = await self.theoddsapi_adapter.get_first_half_over_odds(fixture_id)
                if theoddsapi_odds:
                    odds_sources.append({
                        'source': 'theoddsapi',
                        'over_odds': theoddsapi_odds.get('over_odds'),
                        'under_odds': theoddsapi_odds.get('under_odds')
                    })
            except Exception as e:
                print(f"Error fetching TheOddsAPI odds for {fixture_id}: {e}")
        
        # If no real odds available, return None
        if not odds_sources:
            return None
        
        # Return the best available odds
        best_odds = odds_sources[0]  # Take first available
        return {
            'over_odds': best_odds['over_odds'],
            'under_odds': best_odds['under_odds'],
            'source': best_odds['source']
        }
    
    async def calculate_pnl_with_real_odds(self, predictions_df: pd.DataFrame, 
                                         stake: float = 100.0) -> Dict:
        """Calculate PnL using real odds from available sources."""
        print(f"Calculating PnL with real odds and ${stake} flat stakes...")
        
        # Initialize adapters
        await self.initialize_adapters()
        
        total_bets = len(predictions_df)
        total_staked = total_bets * stake
        total_winnings = 0.0
        winning_bets = 0
        losing_bets = 0
        
        bet_details = []
        odds_sources_used = {}
        
        for i, (_, pred) in enumerate(predictions_df.iterrows()):
            if i % 10 == 0:
                print(f"Processing bet {i+1}/{total_bets}")
            
            home_team = pred['Home Team']
            away_team = pred['Away Team']
            match_date = pred['Date']
            fixture_id = f"fixture_{i}"  # Generate a fixture ID
            
            # Get odds for this fixture
            odds = await self.get_odds_for_fixture(fixture_id, home_team, away_team, match_date)
            
            if not odds:
                print(f"No real odds available for {home_team} vs {away_team} - skipping bet")
                continue
            
            over_odds = odds['over_odds']
            source = odds['source']
            
            # Track odds sources used
            odds_sources_used[source] = odds_sources_used.get(source, 0) + 1
            
            model_result = pred['ModelResult']
            
            if model_result == 'WIN':
                winnings = stake * (over_odds - 1)  # Profit = stake * (odds - 1)
                total_winnings += winnings
                winning_bets += 1
                bet_result = 'WIN'
            else:  # LOSS
                winnings = -stake  # Lose the stake
                total_winnings += winnings
                losing_bets += 1
                bet_result = 'LOSS'
            
            bet_details.append({
                'Date': match_date,
                'Home Team': home_team,
                'Away Team': away_team,
                'Over Odds': over_odds,
                'Under Odds': odds.get('under_odds'),
                'Odds Source': source,
                'Stake': stake,
                'Model Result': model_result,
                'Bet Result': bet_result,
                'Profit/Loss': winnings
            })
        
        net_profit = total_winnings
        roi = (net_profit / total_staked) * 100 if total_staked > 0 else 0
        win_rate = (winning_bets / total_bets) * 100 if total_bets > 0 else 0
        
        return {
            'total_bets': total_bets,
            'total_staked': total_staked,
            'winning_bets': winning_bets,
            'losing_bets': losing_bets,
            'win_rate': win_rate,
            'total_winnings': total_winnings,
            'net_profit': net_profit,
            'roi': roi,
            'odds_sources_used': odds_sources_used,
            'bet_details': bet_details
        }
    
    def calculate_pnl_with_real_odds_only(self, predictions_df: pd.DataFrame, 
                                        stake: float = 100.0) -> Dict:
        """Calculate PnL using only real odds from available sources."""
        print("Note: This system now only works with real odds from Betfair and TheOddsAPI")
        print("Configure your API keys to enable real odds fetching")
        return {
            'total_bets': 0,
            'total_staked': 0.0,
            'winning_bets': 0,
            'losing_bets': 0,
            'win_rate': 0.0,
            'total_winnings': 0.0,
            'net_profit': 0.0,
            'roi': 0.0,
            'odds_sources_used': {},
            'bet_details': []
        }
    
    async def scan_live_odds(self, fixtures: List[Dict]) -> List[Dict]:
        """Scan live odds for upcoming fixtures."""
        print("Scanning live odds for upcoming fixtures...")
        
        await self.initialize_adapters()
        
        results = []
        for fixture in fixtures:
            fixture_id = fixture.get('id', f"fixture_{len(results)}")
            home_team = fixture.get('home_team', 'Unknown')
            away_team = fixture.get('away_team', 'Unknown')
            match_date = fixture.get('date', date.today())
            
            odds = await self.get_odds_for_fixture(fixture_id, home_team, away_team, match_date)
            
            if odds:
                results.append({
                    'fixture_id': fixture_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'match_date': match_date,
                    'over_odds': odds['over_odds'],
                    'under_odds': odds['under_odds'],
                    'odds_source': odds['source']
                })
        
        return results

async def main():
    """Main function to demonstrate the odds integration system."""
    # Load predictions
    predictions_df = pd.read_csv('matchweek5_plus_predictions.csv')
    
    # Create a mock config for testing
    class MockConfig:
        def get_provider_api_key(self, key_name):
            return None  # No real API keys for demo
    
    config = MockConfig()
    service = OddsIntegrationService(config)
    
    # Calculate PnL with real odds only
    print("Running PnL analysis with real odds only...")
    print("Note: No API keys configured - no real odds available")
    results = service.calculate_pnl_with_real_odds_only(predictions_df)
    
    print(f"\n📊 ODDS INTEGRATION PnL RESULTS")
    print("=" * 50)
    print(f"Total bets: {results['total_bets']}")
    print(f"Total staked: ${results['total_staked']:,.2f}")
    print(f"Winning bets: {results['winning_bets']}")
    print(f"Losing bets: {results['losing_bets']}")
    print(f"Win rate: {results['win_rate']:.1f}%")
    print(f"Total winnings: ${results['total_winnings']:,.2f}")
    print(f"Net profit: ${results['net_profit']:,.2f}")
    print(f"ROI: {results['roi']:.1f}%")
    
    if results['total_bets'] == 0:
        print("\n⚠️  No bets processed - configure API keys for Betfair or TheOddsAPI to enable real odds")

if __name__ == "__main__":
    asyncio.run(main())
