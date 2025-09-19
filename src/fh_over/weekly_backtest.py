"""Weekly backtesting that processes matches by matchweek starting from week 9."""

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
class WeeklyBacktestResult:
    """Result of a weekly backtest bet."""
    fixture_id: str
    match_date: datetime
    home_team: str
    away_team: str
    league: str
    matchweek: int
    
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


class WeeklyBacktester:
    """Weekly backtesting that processes matches by matchweek."""
    
    def __init__(self):
        self.config = config
        self.results = []
        self.weekly_results = {}
        self.processed_fixtures = 0
        self.total_fixtures = 0
    
    def run_weekly_backtest(
        self,
        start_week: int = 9,
        end_week: Optional[int] = None,
        league_filter: Optional[str] = None,
        min_samples_home: int = 5,
        min_samples_away: int = 5
    ) -> None:
        """Run weekly backtest starting from specified week."""
        
        print(f"🚀 Starting weekly backtest from matchweek {start_week}...")
        
        # Get all fixtures grouped by matchweek
        weekly_fixtures = self._get_fixtures_by_week(league_filter)
        
        if not weekly_fixtures:
            print("❌ No fixtures found for backtest")
            return
        
        # Process each week
        for week, fixtures in weekly_fixtures.items():
            if week < start_week:
                continue
            if end_week and week > end_week:
                break
                
            print(f"\n📅 Processing Matchweek {week} ({len(fixtures)} fixtures)...")
            week_results = self._process_week(fixtures, week, min_samples_home, min_samples_away)
            self.weekly_results[week] = week_results
            self.results.extend(week_results)
            self.processed_fixtures += len(fixtures)
            
            # Print week summary
            self._print_week_summary(week, week_results)
        
        # Print overall summary
        self._print_overall_summary()
    
    def _get_fixtures_by_week(self, league_filter: Optional[str]) -> Dict[int, List[Fixture]]:
        """Get fixtures grouped by matchweek."""
        
        with next(get_session()) as session:
            # Build query
            statement = select(Fixture).where(Fixture.status == "finished")
            
            if league_filter:
                statement = statement.where(Fixture.league_name == league_filter)
            
            # Order by date
            statement = statement.order_by(Fixture.match_date)
            
            fixtures = session.exec(statement).all()
            
            # Group by actual Premier League matchweek
            weekly_fixtures = {}
            
            for fixture in fixtures:
                # Map date to actual Premier League round
                week_num = self._get_premier_league_round(fixture.match_date)
                
                if week_num not in weekly_fixtures:
                    weekly_fixtures[week_num] = []
                
                weekly_fixtures[week_num].append(fixture)
            
            return weekly_fixtures
    
    def _get_premier_league_round(self, match_date) -> int:
        """Map a match date to the actual Premier League round number."""
        from datetime import datetime
        
        # Premier League 2024-25 round date ranges
        round_dates = {
            1: (datetime(2024, 8, 16), datetime(2024, 8, 16)),
            2: (datetime(2024, 8, 24), datetime(2024, 8, 25)),
            3: (datetime(2024, 8, 31), datetime(2024, 9, 1)),
            4: (datetime(2024, 9, 14), datetime(2024, 9, 15)),
            5: (datetime(2024, 9, 21), datetime(2024, 9, 22)),
            6: (datetime(2024, 9, 28), datetime(2024, 9, 30)),
            7: (datetime(2024, 10, 5), datetime(2024, 10, 6)),
            8: (datetime(2024, 10, 19), datetime(2024, 10, 21)),
            9: (datetime(2024, 10, 25), datetime(2024, 10, 27)),
            10: (datetime(2024, 11, 2), datetime(2024, 11, 4)),
            11: (datetime(2024, 11, 9), datetime(2024, 11, 10)),
            12: (datetime(2024, 11, 23), datetime(2024, 11, 25)),
            13: (datetime(2024, 11, 29), datetime(2024, 12, 1)),
            14: (datetime(2024, 12, 3), datetime(2024, 12, 5)),
            15: (datetime(2024, 12, 7), datetime(2024, 12, 14)),
            16: (datetime(2024, 12, 14), datetime(2024, 12, 21)),
            17: (datetime(2024, 12, 21), datetime(2024, 12, 26)),
            18: (datetime(2024, 12, 26), datetime(2024, 12, 29)),
            19: (datetime(2024, 12, 29), datetime(2025, 1, 4)),
            20: (datetime(2025, 1, 4), datetime(2025, 1, 14)),
            21: (datetime(2025, 1, 14), datetime(2025, 1, 18)),
            22: (datetime(2025, 1, 18), datetime(2025, 1, 25)),
            23: (datetime(2025, 1, 25), datetime(2025, 2, 1)),
            24: (datetime(2025, 2, 1), datetime(2025, 2, 12)),
            25: (datetime(2025, 2, 14), datetime(2025, 2, 16)),
            26: (datetime(2025, 2, 19), datetime(2025, 2, 23)),
            27: (datetime(2025, 2, 23), datetime(2025, 2, 26)),
            28: (datetime(2025, 2, 27), datetime(2025, 3, 9)),
            29: (datetime(2025, 3, 10), datetime(2025, 4, 1)),
            30: (datetime(2025, 4, 1), datetime(2025, 4, 5)),
            31: (datetime(2025, 4, 5), datetime(2025, 4, 12)),
            32: (datetime(2025, 4, 12), datetime(2025, 4, 16)),
            33: (datetime(2025, 4, 19), datetime(2025, 4, 21)),
            34: (datetime(2025, 4, 22), datetime(2025, 5, 1)),
            35: (datetime(2025, 5, 2), datetime(2025, 5, 5)),
            36: (datetime(2025, 5, 10), datetime(2025, 5, 11)),
            37: (datetime(2025, 5, 16), datetime(2025, 5, 20)),
            38: (datetime(2025, 5, 25), datetime(2025, 5, 25))
        }
        
        # Find the round that contains this date
        for round_num, (start_date, end_date) in round_dates.items():
            if start_date <= match_date <= end_date:
                return round_num
        
        # If no round found, return 0 (shouldn't happen with valid data)
        return 0
    
    def _process_week(
        self,
        fixtures: List[Fixture],
        week: int,
        min_samples_home: int,
        min_samples_away: int
    ) -> List[WeeklyBacktestResult]:
        """Process all fixtures in a given week."""
        
        week_results = []
        
        for fixture in fixtures:
            result = self._backtest_fixture_weekly(
                fixture, week, min_samples_home, min_samples_away
            )
            if result:
                week_results.append(result)
        
        return week_results
    
    def _backtest_fixture_weekly(
        self,
        fixture: Fixture,
        week: int,
        min_samples_home: int,
        min_samples_away: int
    ) -> Optional[WeeklyBacktestResult]:
        """Backtest a single fixture using simple average calculation."""
        
        try:
            # Get historical samples for both teams (only before this match)
            home_samples, away_samples = self._get_historical_samples_weekly(
                fixture, min_samples_home, min_samples_away
            )
            
            # Use whatever data is available, even if minimal
            if not home_samples:
                home_samples = TeamSamples(
                    team_id=str(fixture.home_team_id),
                    scope="home",
                    samples=[0.0],  # Default to 0 if no data
                    match_dates=[fixture.match_date],
                    season="2024-25",
                    n_samples=1
                )
            
            if not away_samples:
                away_samples = TeamSamples(
                    team_id=str(fixture.away_team_id),
                    scope="away", 
                    samples=[0.0],  # Default to 0 if no data
                    match_dates=[fixture.match_date],
                    season="2024-25",
                    n_samples=1
                )
            
            # Calculate simple averages
            home_avg = sum(home_samples.samples) / len(home_samples.samples)
            away_avg = sum(away_samples.samples) / len(away_samples.samples)
            combined_avg = (home_avg + away_avg) / 2
            
            # Simple betting rule: if combined average >= 1.5, bet $100
            should_bet = combined_avg >= 1.5
            
            # Get actual result
            actual_first_half_goals = self._get_actual_first_half_goals(fixture)
            if actual_first_half_goals is None:
                # Still create a result record even if no actual result
                return self._create_empty_result(fixture, week)
            
            actual_over_05 = actual_first_half_goals > 0.5
            
            # Calculate P&L
            if should_bet:
                flat_stake = 100.0  # $100 per bet
                # Simulate market odds (for backtesting, we'll use fair odds + noise)
                market_odds = self._simulate_market_odds(1.0 - (1.0 / (1.0 + combined_avg)))
                
                if actual_over_05:
                    profit_loss = flat_stake * (market_odds - 1)
                else:
                    profit_loss = -flat_stake
                
                roi = profit_loss / flat_stake if flat_stake > 0 else 0
            else:
                flat_stake = 0.0
                profit_loss = 0.0
                roi = 0.0
                market_odds = 0.0
            
            # Get team names from database since relationships are disabled
            with next(get_session()) as session:
                home_team_stmt = select(Team).where(Team.id == fixture.home_team_id)
                away_team_stmt = select(Team).where(Team.id == fixture.away_team_id)
                home_team = session.exec(home_team_stmt).first()
                away_team = session.exec(away_team_stmt).first()
                
                home_team_name = home_team.name if home_team else "Unknown"
                away_team_name = away_team.name if away_team else "Unknown"
            
            return WeeklyBacktestResult(
                fixture_id=str(fixture.id),
                match_date=fixture.match_date,
                home_team=home_team_name,
                away_team=away_team_name,
                league=fixture.league_name,
                matchweek=week,
                lambda_hat=combined_avg,  # Use combined average as lambda
                p_hat=1.0 - (1.0 / (1.0 + combined_avg)) if combined_avg > 0 else 0.0,  # Simple probability
                p_ci_low=0.0,  # No confidence intervals in simple model
                p_ci_high=0.0,  # No confidence intervals in simple model
                fair_odds=market_odds,
                n_home=len(home_samples.samples),
                n_away=len(away_samples.samples),
                stake_amount=flat_stake,
                stake_fraction=flat_stake / self.config.staking.bankroll if flat_stake > 0 else 0.0,
                signal=should_bet,
                actual_first_half_goals=actual_first_half_goals,
                actual_over_05=actual_over_05,
                profit_loss=profit_loss,
                roi=roi
            )
            
        except Exception as e:
            print(f"⚠️ Error backtesting fixture {fixture.id}: {e}")
            return self._create_empty_result(fixture, week)
    
    def _create_empty_result(self, fixture: Fixture, week: int) -> WeeklyBacktestResult:
        """Create an empty result record for fixtures that couldn't be processed."""
        
        # Get team names from database since relationships are disabled
        with next(get_session()) as session:
            home_team_stmt = select(Team).where(Team.id == fixture.home_team_id)
            away_team_stmt = select(Team).where(Team.id == fixture.away_team_id)
            home_team = session.exec(home_team_stmt).first()
            away_team = session.exec(away_team_stmt).first()
            
            home_team_name = home_team.name if home_team else "Unknown"
            away_team_name = away_team.name if away_team else "Unknown"
        
        return WeeklyBacktestResult(
            fixture_id=str(fixture.id),
            match_date=fixture.match_date,
            home_team=home_team_name,
            away_team=away_team_name,
            league=fixture.league_name,
            matchweek=week,
            lambda_hat=0.0,
            p_hat=0.0,
            p_ci_low=0.0,
            p_ci_high=0.0,
            fair_odds=0.0,
            n_home=0,
            n_away=0,
            stake_amount=0.0,
            stake_fraction=0.0,
            signal=False,
            actual_first_half_goals=0.0,
            actual_over_05=False,
            profit_loss=0.0,
            roi=0.0
        )
    
    def _get_historical_samples_weekly(
        self,
        fixture: Fixture,
        min_samples_home: int,
        min_samples_away: int
    ) -> Tuple[Optional[TeamSamples], Optional[TeamSamples]]:
        """Get historical samples for a fixture using only data before the match date."""
        
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
    
    def _print_week_summary(self, week: int, week_results: List[WeeklyBacktestResult]) -> None:
        """Print summary for a specific week."""
        
        if not week_results:
            print(f"  No predictions for Matchweek {week}")
            return
        
        # Filter to only bets we actually made
        bets = [r for r in week_results if r.signal and r.stake_amount > 0]
        
        if not bets:
            print(f"  Matchweek {week}: No bets made")
            return
        
        winning_bets = sum(1 for bet in bets if bet.actual_over_05)
        losing_bets = len(bets) - winning_bets
        win_rate = winning_bets / len(bets) if bets else 0.0
        
        total_staked = sum(bet.stake_amount for bet in bets)
        total_profit = sum(bet.profit_loss for bet in bets)
        total_roi = total_profit / total_staked if total_staked > 0 else 0.0
        
        print(f"  📊 Matchweek {week}: {len(bets)} bets, {win_rate:.1%} win rate, ${total_profit:.2f} profit ({total_roi:.1%} ROI)")
        
        # Show individual bets
        for bet in bets:
            result = "✅" if bet.actual_over_05 else "❌"
            print(f"    {result} {bet.home_team} vs {bet.away_team}: λ={bet.lambda_hat:.2f}, P={bet.p_hat:.3f}, Stake=${bet.stake_amount:.2f}, Profit=${bet.profit_loss:.2f}")
    
    def _print_overall_summary(self) -> None:
        """Print overall backtest summary."""
        
        if not self.results:
            print("No results to summarize")
            return
        
        # Filter to only bets we actually made
        bets = [r for r in self.results if r.signal and r.stake_amount > 0]
        
        if not bets:
            print("No bets were made")
            return
        
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
        
        print("\n" + "="*60)
        print("📊 WEEKLY BACKTEST RESULTS SUMMARY")
        print("="*60)
        print(f"Total Fixtures Processed: {self.processed_fixtures}")
        print(f"Total Bets Made: {len(bets)}")
        print(f"Winning Bets: {winning_bets}")
        print(f"Losing Bets: {losing_bets}")
        print(f"Win Rate: {win_rate:.1%}")
        print(f"Total Staked: ${total_staked:.2f}")
        print(f"Total Profit: ${total_profit:.2f}")
        print(f"Total ROI: {total_roi:.1%}")
        print(f"Average Stake: ${avg_stake:.2f}")
        print(f"Average Profit per Bet: ${avg_profit_per_bet:.2f}")
        print(f"Maximum Drawdown: ${max_drawdown:.2f}")
        print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
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
                'matchweek': result.matchweek,
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
    
    def export_weekly_summary(self, filepath: str) -> None:
        """Export weekly summary to CSV."""
        
        if not self.weekly_results:
            print("No weekly results to export")
            return
        
        # Create weekly summary
        weekly_data = []
        for week, results in self.weekly_results.items():
            bets = [r for r in results if r.signal and r.stake_amount > 0]
            
            if not bets:
                weekly_data.append({
                    'matchweek': week,
                    'fixtures_processed': len(results),
                    'bets_made': 0,
                    'winning_bets': 0,
                    'losing_bets': 0,
                    'win_rate': 0.0,
                    'total_staked': 0.0,
                    'total_profit': 0.0,
                    'roi': 0.0
                })
                continue
            
            winning_bets = sum(1 for bet in bets if bet.actual_over_05)
            losing_bets = len(bets) - winning_bets
            win_rate = winning_bets / len(bets)
            
            total_staked = sum(bet.stake_amount for bet in bets)
            total_profit = sum(bet.profit_loss for bet in bets)
            roi = total_profit / total_staked if total_staked > 0 else 0.0
            
            weekly_data.append({
                'matchweek': week,
                'fixtures_processed': len(results),
                'bets_made': len(bets),
                'winning_bets': winning_bets,
                'losing_bets': losing_bets,
                'win_rate': win_rate,
                'total_staked': total_staked,
                'total_profit': total_profit,
                'roi': roi
            })
        
        df = pd.DataFrame(weekly_data)
        df.to_csv(filepath, index=False)
        print(f"✅ Weekly summary exported to {filepath}")


def run_weekly_backtest(
    start_week: int = 9,
    end_week: Optional[int] = None,
    league: Optional[str] = None,
    export_file: Optional[str] = None,
    export_weekly: Optional[str] = None,
    min_samples: int = 5
) -> None:
    """Run weekly backtest with command line interface."""
    
    backtester = WeeklyBacktester()
    
    # Run backtest
    backtester.run_weekly_backtest(
        start_week=start_week,
        end_week=end_week,
        league_filter=league,
        min_samples_home=min_samples,
        min_samples_away=min_samples
    )
    
    # Export results if requested
    if export_file:
        backtester.export_results(export_file)
    
    if export_weekly:
        backtester.export_weekly_summary(export_weekly)


if __name__ == "__main__":
    # Example usage
    run_weekly_backtest(
        start_week=9,
        end_week=38,
        league="Premier League",
        export_file="weekly_backtest_results.csv",
        export_weekly="weekly_summary.csv",
        min_samples=5
    )
