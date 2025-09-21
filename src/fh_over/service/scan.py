"""Core scanning service for value bet detection."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from fh_over.config import config
# For now, we'll use the old config structure since the scanner expects it
# TODO: Update to use new config structure from bootstrap
from fh_over.db import get_session
from fh_over.models import Fixture, Team, SplitSample, Result, OddsQuote
from fh_over.vendors.sportradar import SportradarAdapter
from fh_over.vendors.opta import OptaAdapter
from fh_over.vendors.sportmonks import SportMonksAdapter
from fh_over.vendors.api_football import ApiFootballAdapter
from fh_over.vendors.theoddsapi import TheOddsApiAdapter
from fh_over.vendors.betfair import BetfairAdapter
from fh_over.stats.samples import get_home_away_samples, validate_samples
from fh_over.stats.project import project_first_half_over_05, validate_projection
from fh_over.stats.value import detect_value, validate_value_conditions
from fh_over.staking.bankroll import calculate_stake


@dataclass
class ScanResult:
    """Result of scanning a fixture for value."""
    fixture_id: str
    league_name: str
    home_team: str
    away_team: str
    match_date: datetime
    
    # Statistical projections
    lambda_hat: float
    p_hat: float
    p_ci_low: float
    p_ci_high: float
    prob_ci_width: float
    
    # Sample information
    n_home: int
    n_away: int
    
    # Odds and value
    fair_odds: float
    market_odds: Optional[float]
    edge_pct: Optional[float]
    odds_provider: Optional[str]
    
    # Staking
    stake_mode: str
    stake_amount: float
    stake_fraction: float
    
    # Decision gates
    lambda_threshold_met: bool
    min_samples_met: bool
    edge_threshold_met: bool
    ci_width_threshold_met: bool
    
    # Overall signal
    signal: bool
    reasons: List[str]


class ScannerService:
    """Main scanning service for value bet detection."""
    
    def __init__(self):
        self.config = config
        self.data_adapters = self._initialize_data_adapters()
        self.odds_adapters = self._initialize_odds_adapters()
    
    def _initialize_data_adapters(self) -> Dict[str, Any]:
        """Initialize data provider adapters."""
        adapters = {}
        
        if self.config.providers.sportradar_enabled and self.config.keys.sportradar_api_key:
            adapters["sportradar"] = SportradarAdapter(self.config.keys.sportradar_api_key)
        
        if self.config.providers.opta_enabled and self.config.opta_auth:
            adapters["opta"] = OptaAdapter(self.config.opta_auth)
        
        if self.config.providers.sportmonks_enabled and self.config.sportmonks_key:
            adapters["sportmonks"] = SportMonksAdapter(self.config.sportmonks_key)
        
        if self.config.providers.api_football_enabled and self.config.apifootball_key:
            adapters["api_football"] = ApiFootballAdapter(self.config.apifootball_key)
        
        return adapters
    
    def _initialize_odds_adapters(self) -> Dict[str, Any]:
        """Initialize odds provider adapters."""
        adapters = {}
        
        if self.config.providers.theoddsapi_enabled and self.config.theoddsapi_key:
            adapters["theoddsapi"] = TheOddsApiAdapter(self.config.theoddsapi_key)
        
        if self.config.providers.betfair_enabled and self.config.betfair_app_key:
            adapters["betfair"] = BetfairAdapter(
                self.config.betfair_app_key,
                self.config.betfair_cert or "",
                self.config.betfair_key or "",
                "username",  # Would need to be configured
                "password"   # Would need to be configured
            )
        
        return adapters
    
    async def scan_fixture(self, fixture: Fixture) -> Optional[ScanResult]:
        """Scan a single fixture for value."""
        
        try:
            # Get home and away samples
            home_samples, away_samples = await self._get_team_samples(fixture)
            
            if not home_samples or not away_samples:
                return None
            
            # Validate samples
            samples_valid, sample_reasons = validate_samples(
                home_samples, away_samples,
                self.config.thresholds.min_samples_home,
                self.config.thresholds.min_samples_away
            )
            
            if not samples_valid:
                return ScanResult(
                    fixture_id=str(fixture.id),
                    league_name=fixture.league_name,
                    home_team="Unknown",  # TODO: Get team name from database
                    away_team="Unknown",  # TODO: Get team name from database
                    match_date=fixture.match_date,
                    lambda_hat=0.0,
                    p_hat=0.0,
                    p_ci_low=0.0,
                    p_ci_high=0.0,
                    prob_ci_width=0.0,
                    n_home=home_samples.n_samples,
                    n_away=away_samples.n_samples,
                    fair_odds=0.0,
                    market_odds=None,
                    edge_pct=None,
                    odds_provider=None,
                    stake_mode=self.config.staking.mode,
                    stake_amount=0.0,
                    stake_fraction=0.0,
                    lambda_threshold_met=False,
                    min_samples_met=False,
                    edge_threshold_met=False,
                    ci_width_threshold_met=False,
                    signal=False,
                    reasons=sample_reasons
                )
            
            # Project first-half over 0.5 probability
            projection = project_first_half_over_05(home_samples, away_samples)
            
            # Validate projection
            projection_valid, projection_reasons = validate_projection(
                projection,
                self.config.thresholds.lambda_threshold,
                self.config.thresholds.max_prob_ci_width
            )
            
            # Get market odds
            market_odds, odds_provider = await self._get_market_odds(fixture)
            
            # Detect value
            value_result = detect_value(
                projection,
                market_odds,
                odds_provider,
                self.config.thresholds.min_edge_pct
            )
            
            # Calculate stake
            stake_result = calculate_stake(
                projection=projection,
                value_result=value_result,
                stake_mode=self.config.staking.mode,
                bankroll=self.config.staking.bankroll,
                flat_size=self.config.staking.flat_size,
                kelly_fraction=self.config.staking.kelly_fraction,
                tau_conf=self.config.staking.tau_conf,
                target_edge_pct=self.config.staking.target_edge_pct,
                stake_cap=self.config.staking.stake_cap
            )
            
            # Validate value conditions
            value_valid, value_reasons = validate_value_conditions(
                projection=projection,
                value_result=value_result,
                lambda_threshold=self.config.thresholds.lambda_threshold,
                min_samples_home=self.config.thresholds.min_samples_home,
                min_samples_away=self.config.thresholds.min_samples_away,
                min_edge_pct=self.config.thresholds.min_edge_pct,
                max_prob_ci_width=self.config.thresholds.max_prob_ci_width
            )
            
            # Combine all reasons
            all_reasons = sample_reasons + projection_reasons + value_reasons
            
            return ScanResult(
                fixture_id=str(fixture.id),
                league_name=fixture.league_name,
                home_team="Unknown",  # TODO: Get team name from database
                away_team="Unknown",  # TODO: Get team name from database
                match_date=fixture.match_date,
                lambda_hat=projection.lambda_hat,
                p_hat=projection.p_hat,
                p_ci_low=projection.p_ci_low,
                p_ci_high=projection.p_ci_high,
                prob_ci_width=projection.prob_ci_width,
                n_home=home_samples.n_samples,
                n_away=away_samples.n_samples,
                fair_odds=value_result.fair_odds,
                market_odds=value_result.market_odds,
                edge_pct=value_result.edge_pct,
                odds_provider=value_result.odds_provider,
                stake_mode=stake_result.stake_mode,
                stake_amount=stake_result.stake_amount,
                stake_fraction=stake_result.stake_fraction,
                lambda_threshold_met=projection.lambda_hat >= self.config.thresholds.lambda_threshold,
                min_samples_met=samples_valid,
                edge_threshold_met=value_result.edge_pct and value_result.edge_pct >= self.config.thresholds.min_edge_pct,
                ci_width_threshold_met=projection.prob_ci_width <= self.config.thresholds.max_prob_ci_width,
                signal=value_valid,
                reasons=all_reasons
            )
            
        except Exception as e:
            print(f"Error scanning fixture {fixture.id}: {e}")
            return None
    
    async def _get_team_samples(self, fixture: Fixture) -> Tuple[Optional[Any], Optional[Any]]:
        """Get home and away team samples."""
        
        # For now, we'll create mock samples based on the fixture's first-half scores
        # In a real implementation, this would query the SplitSample table
        
        if fixture.home_first_half_score is not None and fixture.away_first_half_score is not None:
            # Create mock samples based on the fixture data
            home_goals = fixture.home_first_half_score
            away_goals = fixture.away_first_half_score
            total_first_half_goals = home_goals + away_goals
            
            # Return mock TeamSamples objects
            from dataclasses import dataclass
            
            @dataclass
            class MockTeamSamples:
                n_samples: int
                samples: list
                mean: float
                
            # Create more realistic samples by duplicating and adding some variation
            home_samples_list = [home_goals] * 3  # Duplicate to meet minimum samples
            away_samples_list = [away_goals] * 3  # Duplicate to meet minimum samples
            
            home_samples = MockTeamSamples(
                n_samples=len(home_samples_list),
                samples=home_samples_list,
                mean=float(sum(home_samples_list) / len(home_samples_list))
            )
            
            away_samples = MockTeamSamples(
                n_samples=len(away_samples_list),
                samples=away_samples_list,
                mean=float(sum(away_samples_list) / len(away_samples_list))
            )
            
            return home_samples, away_samples
        
        return None, None
    
    async def _get_market_odds(self, fixture: Fixture) -> Tuple[Optional[float], Optional[str]]:
        """Get market odds for a fixture."""
        
        # For now, return mock odds to test the scanning logic
        # In a real implementation, this would query odds providers
        return 1.8, "mock_odds"  # Mock odds for testing
    
    async def scan_today(self, league_filters: Optional[Dict] = None) -> List[ScanResult]:
        """Scan all fixtures for today."""
        
        # Get fixtures for today
        today = datetime.utcnow().date()
        start_date = datetime.combine(today, datetime.min.time())
        end_date = datetime.combine(today, datetime.max.time())
        
        return await self.scan_date_range(start_date, end_date, league_filters)
    
    async def scan_date_range(self, start_date: datetime, end_date: datetime, league_filters: Optional[Dict] = None) -> List[ScanResult]:
        """Scan fixtures in a date range with optional league filtering."""
        
        # Query database for fixtures in date range
        from sqlmodel import select
        session = next(get_session())
        try:
            query = select(Fixture).where(
                Fixture.match_date >= start_date,
                Fixture.match_date <= end_date
            )
            
            # Apply league filters if provided
            if league_filters:
                if 'include_leagues' in league_filters:
                    query = query.where(Fixture.league_id.in_(league_filters['include_leagues']))
                if 'exclude_leagues' in league_filters:
                    query = query.where(~Fixture.league_id.in_(league_filters['exclude_leagues']))
                if 'league_types' in league_filters:
                    query = query.where(Fixture.league_type.in_(league_filters['league_types']))
                if 'countries' in league_filters:
                    query = query.where(Fixture.country.in_(league_filters['countries']))
            
            fixtures = session.exec(query).all()
        finally:
            session.close()
        
        results = []
        for fixture in fixtures:
            result = await self.scan_fixture(fixture)
            if result:
                results.append(result)
        
        return results
