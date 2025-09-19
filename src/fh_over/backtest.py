"""Backtesting system for the First-Half Over scanner."""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json

from fh_over.db import get_session
from fh_over.models import Fixture, Team, SplitSample, Result
from fh_over.stats.samples import get_home_away_samples, validate_samples, TeamSamples
from fh_over.stats.project import project_first_half_over_05, validate_projection
from fh_over.stats.value import detect_value, validate_value_conditions
from fh_over.staking.bankroll import calculate_stake
from fh_over.config import config
from sqlmodel import Session, select, and_


@dataclass
class BacktestResult:
    """Result of a single backtest bet."""
    fixture_id: str
    match_date: datetime
    home_team: str
    away_team: str
    league: str
    
    # Predictions
    lambda_hat: float
    p_hat: float
    p_ci_low: float
    p_ci_high: float
    fair_odds: float
    
    # Sample info
    n_home: int
    n_away: int
    
    # Betting
    stake_amount: float
    stake_fraction: float
    signal: bool
    
    # Actual result
    actual_first_half_goals: int
    actual_over_05: bool
    profit_loss: float
    roi: float


@dataclass
class BacktestSummary:
    """Summary of backtest results."""
    total_bets: int
    winning_bets: int
    losing_bets: int
    win_rate: float
    total_staked: float
    total_profit: float
    total_roi: float
    avg_stake: float
    avg_profit_per_bet: float
    max_drawdown: float
    sharpe_ratio: float
    results: List[BacktestResult]


class Backtester:
    """Backtesting system for the First-Half Over scanner."""
    
    def __init__(self):
        self.config = config
        self.results = []
    
    def run_backtest(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        league_filter: Optional[str] = None,
        min_samples_home: int = 8,
        min_samples_away: int = 8
    ) -> BacktestSummary:
        """Run backtest on historical data."""
        
        print("🚀 Starting backtest...")
        
        # Get fixtures to backtest
        fixtures = self._get_fixtures_for_backtest(start_date, end_date, league_filter)
        print(f"📊 Found {len(fixtures)} fixtures to backtest")
        
        if not fixtures:
            print("❌ No fixtures found for backtest")
            return BacktestSummary(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, [])
        
        # Process each fixture
        for i, fixture in enumerate(fixtures):
            if i % 10 == 0:
                print(f"Processing fixture {i+1}/{len(fixtures)}...")
            
            result = self._backtest_fixture(fixture, min_samples_home, min_samples_away)
            if result:
                self.results.append(result)
        
        # Calculate summary
        summary = self._calculate_summary()
        self._print_summary(summary)
        
        return summary
    
    def _get_fixtures_for_backtest(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        league_filter: Optional[str]
    ) -> List[Fixture]:
        """Get fixtures for backtesting."""
        
        with next(get_session()) as session:
            # Build query
            statement = select(Fixture).where(Fixture.status == "finished")
            
            if start_date:
                statement = statement.where(Fixture.match_date >= start_date)
            if end_date:
                statement = statement.where(Fixture.match_date <= end_date)
            if league_filter:
                statement = statement.where(Fixture.league_name == league_filter)
            
            # Order by date
            statement = statement.order_by(Fixture.match_date)
            
            fixtures = session.exec(statement).all()
            return list(fixtures)
    
    def _backtest_fixture(
        self,
        fixture: Fixture,
        min_samples_home: int,
        min_samples_away: int
    ) -> Optional[BacktestResult]:
        """Backtest a single fixture."""
        
        try:
            # Get historical samples for both teams
            home_samples, away_samples = self._get_historical_samples(
                fixture, min_samples_home, min_samples_away
            )
            
            if not home_samples or not away_samples:
                return None
            
            # Validate samples
            samples_valid, _ = validate_samples(
                home_samples, away_samples, min_samples_home, min_samples_away
            )
            
            if not samples_valid:
                return None
            
            # Project first-half over 0.5 probability
            projection = project_first_half_over_05(home_samples, away_samples)
            
            # Validate projection
            projection_valid, _ = validate_projection(
                projection,
                self.config.thresholds.lambda_threshold,
                self.config.thresholds.max_prob_ci_width
            )
            
            if not projection_valid:
                return None
            
            # Simulate market odds (for backtesting, we'll use fair odds + noise)
            market_odds = self._simulate_market_odds(projection.p_hat)
            
            # Detect value
            value_result = detect_value(
                projection,
                market_odds,
                "backtest",
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
            
            # Check if we have a signal
            value_valid, _ = validate_value_conditions(
                projection=projection,
                value_result=value_result,
                lambda_threshold=self.config.thresholds.lambda_threshold,
                min_samples_home=min_samples_home,
                min_samples_away=min_samples_away,
                min_edge_pct=self.config.thresholds.min_edge_pct,
                max_prob_ci_width=self.config.thresholds.max_prob_ci_width
            )
            
            # Get actual result
            actual_first_half_goals = self._get_actual_first_half_goals(fixture)
            if actual_first_half_goals is None:
                return None
            
            actual_over_05 = actual_first_half_goals > 0.5
            
            # Calculate P&L
            if value_valid and stake_result.stake_amount > 0:
                if actual_over_05:
                    profit_loss = stake_result.stake_amount * (market_odds - 1)
                else:
                    profit_loss = -stake_result.stake_amount
                
                roi = profit_loss / stake_result.stake_amount if stake_result.stake_amount > 0 else 0
            else:
                profit_loss = 0
                roi = 0
            
            # Get team names from database since relationships are disabled
            with next(get_session()) as session:
                home_team_stmt = select(Team).where(Team.id == fixture.home_team_id)
                away_team_stmt = select(Team).where(Team.id == fixture.away_team_id)
                home_team = session.exec(home_team_stmt).first()
                away_team = session.exec(away_team_stmt).first()
                
                home_team_name = home_team.name if home_team else "Unknown"
                away_team_name = away_team.name if away_team else "Unknown"
            
            return BacktestResult(
                fixture_id=str(fixture.id),
                match_date=fixture.match_date,
                home_team=home_team_name,
                away_team=away_team_name,
                league=fixture.league_name,
                lambda_hat=projection.lambda_hat,
                p_hat=projection.p_hat,
                p_ci_low=projection.p_ci_low,
                p_ci_high=projection.p_ci_high,
                fair_odds=1.0 / projection.p_hat if projection.p_hat > 0 else 1.0,
                n_home=home_samples.n_samples,
                n_away=away_samples.n_samples,
                stake_amount=stake_result.stake_amount,
                stake_fraction=stake_result.stake_fraction,
                signal=value_valid,
                actual_first_half_goals=actual_first_half_goals,
                actual_over_05=actual_over_05,
                profit_loss=profit_loss,
                roi=roi
            )
            
        except Exception as e:
            print(f"⚠️ Error backtesting fixture {fixture.id}: {e}")
            return None
    
    def _get_historical_samples(
        self,
        fixture: Fixture,
        min_samples_home: int,
        min_samples_away: int
    ) -> Tuple[Optional[TeamSamples], Optional[TeamSamples]]:
        """Get historical samples for a fixture."""
        
        with next(get_session()) as session:
            # Get home team samples (matches before this fixture)
            home_samples_query = select(SplitSample).where(
                and_(
                    SplitSample.team_id == fixture.home_team_id,
                    SplitSample.scope == "home",
                    SplitSample.match_date < fixture.match_date
                )
            ).order_by(SplitSample.match_date.desc()).limit(20)
            
            home_samples_data = session.exec(home_samples_query).all()
            
            if len(home_samples_data) < min_samples_home:
                return None, None
            
            home_samples = TeamSamples(
                team_id=str(fixture.home_team_id),
                scope="home",
                samples=[float(s.first_half_goals) for s in home_samples_data],
                match_dates=[s.match_date for s in home_samples_data],
                season=home_samples_data[0].season if home_samples_data else "2024-25",
                n_samples=len(home_samples_data)
            )
            
            # Get away team samples
            away_samples_query = select(SplitSample).where(
                and_(
                    SplitSample.team_id == fixture.away_team_id,
                    SplitSample.scope == "away",
                    SplitSample.match_date < fixture.match_date
                )
            ).order_by(SplitSample.match_date.desc()).limit(20)
            
            away_samples_data = session.exec(away_samples_query).all()
            
            if len(away_samples_data) < min_samples_away:
                return None, None
            
            away_samples = TeamSamples(
                team_id=str(fixture.away_team_id),
                scope="away",
                samples=[float(s.first_half_goals) for s in away_samples_data],
                match_dates=[s.match_date for s in away_samples_data],
                season=away_samples_data[0].season if away_samples_data else "2024-25",
                n_samples=len(away_samples_data)
            )
            
            return home_samples, away_samples
    
    def _simulate_market_odds(self, p_hat: float) -> float:
        """Simulate market odds for backtesting."""
        # Add some noise to make it realistic
        import random
        noise = random.uniform(-0.1, 0.1)  # ±10% noise
        fair_odds = 1.0 / p_hat if p_hat > 0 else 1.0
        return fair_odds * (1 + noise)
    
    def _get_actual_first_half_goals(self, fixture: Fixture) -> Optional[float]:
        """Get actual first-half goals for a fixture."""
        if (fixture.home_first_half_score is not None and 
            fixture.away_first_half_score is not None):
            return float(fixture.home_first_half_score + fixture.away_first_half_score)
        return None
    
    def _calculate_summary(self) -> BacktestSummary:
        """Calculate backtest summary statistics."""
        
        if not self.results:
            return BacktestSummary(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, [])
        
        # Filter to only bets we actually made
        bets = [r for r in self.results if r.signal and r.stake_amount > 0]
        
        if not bets:
            return BacktestSummary(
                total_bets=0,
                winning_bets=0,
                losing_bets=0,
                win_rate=0.0,
                total_staked=0.0,
                total_profit=0.0,
                total_roi=0.0,
                avg_stake=0.0,
                avg_profit_per_bet=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                results=self.results
            )
        
        winning_bets = sum(1 for bet in bets if bet.actual_over_05)
        losing_bets = len(bets) - winning_bets
        win_rate = winning_bets / len(bets) if bets else 0.0
        
        total_staked = sum(bet.stake_amount for bet in bets)
        total_profit = sum(bet.profit_loss for bet in bets)
        total_roi = total_profit / total_staked if total_staked > 0 else 0.0
        
        avg_stake = total_staked / len(bets) if bets else 0.0
        avg_profit_per_bet = total_profit / len(bets) if bets else 0.0
        
        # Calculate max drawdown
        cumulative_profit = 0
        max_profit = 0
        max_drawdown = 0
        
        for bet in bets:
            cumulative_profit += bet.profit_loss
            max_profit = max(max_profit, cumulative_profit)
            drawdown = max_profit - cumulative_profit
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate Sharpe ratio (simplified)
        if bets:
            returns = [bet.roi for bet in bets]
            avg_return = sum(returns) / len(returns)
            return_std = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe_ratio = avg_return / return_std if return_std > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        return BacktestSummary(
            total_bets=len(bets),
            winning_bets=winning_bets,
            losing_bets=losing_bets,
            win_rate=win_rate,
            total_staked=total_staked,
            total_profit=total_profit,
            total_roi=total_roi,
            avg_stake=avg_stake,
            avg_profit_per_bet=avg_profit_per_bet,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            results=self.results
        )
    
    def _print_summary(self, summary: BacktestSummary) -> None:
        """Print backtest summary."""
        
        print("\n" + "="*60)
        print("📊 BACKTEST RESULTS SUMMARY")
        print("="*60)
        print(f"Total Bets Made: {summary.total_bets}")
        print(f"Winning Bets: {summary.winning_bets}")
        print(f"Losing Bets: {summary.losing_bets}")
        print(f"Win Rate: {summary.win_rate:.1%}")
        print(f"Total Staked: ${summary.total_staked:.2f}")
        print(f"Total Profit: ${summary.total_profit:.2f}")
        print(f"Total ROI: {summary.total_roi:.1%}")
        print(f"Average Stake: ${summary.avg_stake:.2f}")
        print(f"Average Profit per Bet: ${summary.avg_profit_per_bet:.2f}")
        print(f"Maximum Drawdown: ${summary.max_drawdown:.2f}")
        print(f"Sharpe Ratio: {summary.sharpe_ratio:.2f}")
        print("="*60)
    
    def export_results(self, filepath: str) -> None:
        """Export backtest results to CSV."""
        
        if not self.results:
            print("No results to export")
            return
        
        # Convert to DataFrame
        data = []
        for result in self.results:
            data.append({
                'fixture_id': result.fixture_id,
                'match_date': result.match_date.isoformat(),
                'home_team': result.home_team,
                'away_team': result.away_team,
                'league': result.league,
                'lambda_hat': result.lambda_hat,
                'p_hat': result.p_hat,
                'p_ci_low': result.p_ci_low,
                'p_ci_high': result.p_ci_high,
                'fair_odds': result.fair_odds,
                'n_home': result.n_home,
                'n_away': result.n_away,
                'stake_amount': result.stake_amount,
                'stake_fraction': result.stake_fraction,
                'signal': result.signal,
                'actual_first_half_goals': result.actual_first_half_goals,
                'actual_over_05': result.actual_over_05,
                'profit_loss': result.profit_loss,
                'roi': result.roi
            })
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        print(f"✅ Results exported to {filepath}")


def run_backtest(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    league: Optional[str] = None,
    export_file: Optional[str] = None
) -> None:
    """Run backtest with command line interface."""
    
    backtester = Backtester()
    
    # Parse dates
    start_dt = None
    end_dt = None
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Run backtest
    summary = backtester.run_backtest(
        start_date=start_dt,
        end_date=end_dt,
        league_filter=league
    )
    
    # Export results if requested
    if export_file:
        backtester.export_results(export_file)


if __name__ == "__main__":
    # Example usage
    run_backtest(
        start_date="2024-08-01",
        end_date="2024-12-31",
        league="Premier League",
        export_file="backtest_results.csv"
    )
