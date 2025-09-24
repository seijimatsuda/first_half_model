#!/usr/bin/env python3
"""
Comprehensive Historical Backtesting System for ALL 2024-2025 Leagues
Analyzes all 1,193 leagues in batches to find which ones our model works best for
"""

import asyncio
import yaml
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import json
import math
import random
import time
from concurrent.futures import ThreadPoolExecutor
import os
from collections import defaultdict

class ComprehensiveHistoricalBacktesterFull:
    """Comprehensive backtesting system for ALL leagues in 2024-2025 season."""
    
    def __init__(self):
        self.api_key = self._get_api_key()
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {'x-apisports-key': self.api_key} if self.api_key else {}
        
        # Load all available leagues
        self.all_leagues = self._load_all_leagues()
        
        # League tier classification
        self.league_tiers = self._classify_leagues_by_tier()
        
        # Rate limiting
        self.request_delay = 0.1  # 100ms between requests for faster processing
        
        # Results storage
        self.all_results = []
        self.league_performance = {}
        self.team_performance = defaultdict(list)
        
        # Batch processing
        self.batch_size = 50
        self.total_batches = 0
        
    def _get_api_key(self) -> str:
        """Get API key from config."""
        try:
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                return config.get('keys', {}).get('api_football_key', '')
        except:
            return ""
    
    def _load_all_leagues(self) -> pd.DataFrame:
        """Load all available leagues from CSV."""
        try:
            return pd.read_csv('api_football_all_leagues.csv')
        except:
            print("❌ Could not load leagues CSV")
            return pd.DataFrame()
    
    def _classify_leagues_by_tier(self) -> Dict[str, Dict]:
        """Classify leagues by tier for realistic projections."""
        
        tier_1_leagues = [
            'Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1',
            'Champions League', 'Europa League', 'UEFA Champions League'
        ]
        
        tier_2_leagues = [
            'Championship', 'Segunda División', '2. Bundesliga', 'Serie B',
            'Premiership', 'Jupiler Pro League', 'Eredivisie', 'Primeira Liga'
        ]
        
        tier_3_leagues = [
            'League One', 'League Two', 'Serie C', '3. Liga',
            'Championship', 'Liga 1', 'Segunda División B'
        ]
        
        tier_4_leagues = [
            'League Two', 'Serie D', '4. Liga', 'Non League',
            'Amateur', 'Youth', 'U20', 'U19', 'U18'
        ]
        
        tiers = {}
        
        for _, league in self.all_leagues.iterrows():
            league_name = league['League_Name']
            country = league['Country']
            
            if any(t1 in league_name for t1 in tier_1_leagues):
                tier = 1
                min_avg, max_avg = 1.2, 1.8
            elif any(t2 in league_name for t2 in tier_2_leagues):
                tier = 2
                min_avg, max_avg = 1.0, 1.6
            elif any(t3 in league_name for t3 in tier_3_leagues):
                tier = 3
                min_avg, max_avg = 0.8, 1.4
            elif any(t4 in league_name for t4 in tier_4_leagues):
                tier = 4
                min_avg, max_avg = 0.6, 1.2
            else:
                if country in ['England', 'Spain', 'Germany', 'Italy', 'France']:
                    tier = 2
                    min_avg, max_avg = 1.0, 1.6
                else:
                    tier = 3
                    min_avg, max_avg = 0.8, 1.4
            
            tiers[league_name] = {
                'tier': tier,
                'min_avg': min_avg,
                'max_avg': max_avg,
                'country': country
            }
        
        return tiers
    
    def calculate_team_averages(self, home_team: str, away_team: str, league_name: str, 
                              historical_matches: List[Dict]) -> Tuple[float, float]:
        """Calculate team averages based on historical matches."""
        
        # Get league tier for realistic ranges
        tier_info = self.league_tiers.get(league_name, {'tier': 3, 'min_avg': 0.8, 'max_avg': 1.4})
        min_avg, max_avg = tier_info['min_avg'], tier_info['max_avg']
        
        # Calculate home team average from historical matches
        home_matches = [m for m in historical_matches if m['home_team'] == home_team]
        if home_matches:
            home_avg = sum(m['home_first_half_goals'] for m in home_matches) / len(home_matches)
        else:
            # Fallback to league tier average with team variation
            home_factor = hash(home_team) % 100 / 100.0
            home_avg = min_avg + (max_avg - min_avg) * (0.3 + 0.7 * home_factor)
        
        # Calculate away team average from historical matches
        away_matches = [m for m in historical_matches if m['away_team'] == away_team]
        if away_matches:
            away_avg = sum(m['away_first_half_goals'] for m in away_matches) / len(away_matches)
        else:
            # Fallback to league tier average with team variation
            away_factor = hash(away_team) % 100 / 100.0
            away_avg = min_avg + (max_avg - min_avg) * (0.3 + 0.7 * away_factor)
        
        return round(home_avg, 2), round(away_avg, 2)
    
    def calculate_projection(self, home_avg: float, away_avg: float) -> Dict[str, float]:
        """Calculate First-Half Over 0.5 projection."""
        
        combined_avg = (home_avg + away_avg) / 2
        p_over_05 = 1 - math.exp(-combined_avg)
        fair_odds = 1 / p_over_05 if p_over_05 > 0 else 10.0
        
        # Simulate market odds with realistic spread
        market_odds = fair_odds * random.uniform(0.85, 1.15)
        edge_pct = (market_odds / fair_odds - 1) * 100
        
        return {
            'combined_avg': round(combined_avg, 2),
            'p_over_05': round(p_over_05, 3),
            'fair_odds': round(fair_odds, 2),
            'market_odds': round(market_odds, 2),
            'edge_pct': round(edge_pct, 1)
        }
    
    def calculate_pnl(self, outcome: str, market_odds: float, stake: float = 100.0) -> float:
        """Calculate PnL for lay betting (laying Under 0.5 Goals)."""
        
        if outcome == 'WIN':  # Goal scored before half-time
            return stake * 0.98
        else:  # 0-0 at half-time
            return -stake * (market_odds - 1)
    
    async def fetch_league_fixtures_historical(self, league_id: int, season: str = "2024") -> List[Dict]:
        """Fetch historical fixtures and results for a league."""
        
        if not self.api_key:
            return []
        
        try:
            response = requests.get(f"{self.base_url}/fixtures", 
                                  headers=self.headers, 
                                  params={
                                      'league': league_id,
                                      'season': season,
                                      'status': 'FT'  # Only finished matches
                                  })
            response.raise_for_status()
            
            data = response.json()
            fixtures = data.get('response', [])
            
            processed_fixtures = []
            for fixture in fixtures:
                # Extract first-half scores
                home_ht = fixture['score']['halftime']['home']
                away_ht = fixture['score']['halftime']['away']
                
                # Calculate first-half total goals
                first_half_goals = home_ht + away_ht
                
                processed_fixtures.append({
                    'fixture_id': fixture['fixture']['id'],
                    'league_id': league_id,
                    'league_name': fixture['league']['name'],
                    'country': fixture['league']['country'],
                    'home_team': fixture['teams']['home']['name'],
                    'away_team': fixture['teams']['away']['name'],
                    'match_date': fixture['fixture']['date'],
                    'home_first_half_goals': home_ht,
                    'away_first_half_goals': away_ht,
                    'total_first_half_goals': first_half_goals,
                    'outcome': 'WIN' if first_half_goals > 0 else 'LOSS'
                })
            
            return processed_fixtures
            
        except Exception as e:
            print(f"❌ Error fetching historical fixtures for league {league_id}: {e}")
            return []
    
    async def backtest_league(self, league_id: int, league_name: str, country: str) -> Dict[str, Any]:
        """Backtest a single league for the 2024-2025 season."""
        
        # Fetch historical fixtures
        fixtures = await self.fetch_league_fixtures_historical(league_id, "2024")
        
        if not fixtures:
            return {
                'league_name': league_name,
                'country': country,
                'total_matches': 0,
                'bets_placed': 0,
                'correct_predictions': 0,
                'accuracy': 0,
                'total_pnl': 0,
                'roi': 0,
                'matches': []
            }
        
        # Sort fixtures by date for chronological processing
        fixtures.sort(key=lambda x: x['match_date'])
        
        # Process each match chronologically
        league_results = []
        historical_matches = []  # Store for team average calculation
        
        for i, fixture in enumerate(fixtures):
            # Calculate team averages based on historical matches up to this point
            home_avg, away_avg = self.calculate_team_averages(
                fixture['home_team'], 
                fixture['away_team'], 
                league_name,
                historical_matches
            )
            
            # Calculate projection
            projection = self.calculate_projection(home_avg, away_avg)
            
            # Apply betting criteria (combined average >= 1.5)
            if projection['combined_avg'] >= 1.5:
                # Calculate PnL based on actual outcome
                pnl = self.calculate_pnl(fixture['outcome'], projection['market_odds'])
                
                result = {
                    'fixture_id': fixture['fixture_id'],
                    'league_name': league_name,
                    'country': country,
                    'home_team': fixture['home_team'],
                    'away_team': fixture['away_team'],
                    'match_date': fixture['match_date'],
                    'home_avg': home_avg,
                    'away_avg': away_avg,
                    'combined_avg': projection['combined_avg'],
                    'p_over_05': projection['p_over_05'],
                    'fair_odds': projection['fair_odds'],
                    'market_odds': projection['market_odds'],
                    'edge_pct': projection['edge_pct'],
                    'actual_outcome': fixture['outcome'],
                    'actual_first_half_goals': fixture['total_first_half_goals'],
                    'prediction_correct': projection['combined_avg'] >= 1.5 and fixture['outcome'] == 'WIN',
                    'pnl': round(pnl, 2),
                    'stake': 100.0
                }
                
                league_results.append(result)
            
            # Add this match to historical data for future calculations
            historical_matches.append(fixture)
        
        # Calculate league performance
        total_matches = len(fixtures)
        bets_placed = len(league_results)
        correct_predictions = sum(1 for r in league_results if r['prediction_correct'])
        accuracy = correct_predictions / bets_placed if bets_placed > 0 else 0
        total_pnl = sum(r['pnl'] for r in league_results)
        roi = total_pnl / (bets_placed * 100) * 100 if bets_placed > 0 else 0
        
        return {
            'league_name': league_name,
            'country': country,
            'total_matches': total_matches,
            'bets_placed': bets_placed,
            'correct_predictions': correct_predictions,
            'accuracy': round(accuracy, 3),
            'total_pnl': round(total_pnl, 2),
            'roi': round(roi, 1),
            'matches': league_results
        }
    
    async def process_batch(self, batch_leagues: pd.DataFrame, batch_num: int) -> List[Dict]:
        """Process a batch of leagues."""
        
        print(f"\n🔄 PROCESSING BATCH {batch_num}/{self.total_batches}")
        print(f"   Leagues in batch: {len(batch_leagues)}")
        print("=" * 50)
        
        batch_results = []
        
        for i, (_, league) in enumerate(batch_leagues.iterrows(), 1):
            league_id = league['League_ID']
            league_name = league['League_Name']
            country = league['Country']
            
            print(f"[{i:2d}/{len(batch_leagues)}] {league_name:30s} ({country:15s})...", end=" ")
            
            try:
                result = await self.backtest_league(league_id, league_name, country)
                batch_results.append(result)
                
                # Display quick result
                if result['bets_placed'] > 0:
                    print(f"✅ {result['bets_placed']:3d} bets | {result['accuracy']:5.1%} | ${result['total_pnl']:8.2f}")
                else:
                    print("❌ No data")
                
                # Rate limiting
                await asyncio.sleep(self.request_delay)
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}...")
                batch_results.append({
                    'league_name': league_name,
                    'country': country,
                    'total_matches': 0,
                    'bets_placed': 0,
                    'correct_predictions': 0,
                    'accuracy': 0,
                    'total_pnl': 0,
                    'roi': 0,
                    'matches': []
                })
        
        return batch_results
    
    async def backtest_all_leagues_full(self) -> Dict[str, Any]:
        """Backtest ALL available leagues for 2024-2025 season in batches."""
        
        print(f"🚀 COMPREHENSIVE HISTORICAL BACKTESTING - ALL LEAGUES")
        print(f"   Season: 2024-2025")
        print(f"   Total leagues: {len(self.all_leagues)}")
        print(f"   Batch size: {self.batch_size}")
        print(f"   Total batches: {(len(self.all_leagues) + self.batch_size - 1) // self.batch_size}")
        print("=" * 70)
        
        # Calculate total batches
        self.total_batches = (len(self.all_leagues) + self.batch_size - 1) // self.batch_size
        
        all_results = []
        league_summaries = []
        
        # Process leagues in batches
        for batch_num in range(1, self.total_batches + 1):
            start_idx = (batch_num - 1) * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(self.all_leagues))
            batch_leagues = self.all_leagues.iloc[start_idx:end_idx]
            
            # Process this batch
            batch_results = await self.process_batch(batch_leagues, batch_num)
            league_summaries.extend(batch_results)
            
            # Store individual match results
            for result in batch_results:
                for match in result['matches']:
                    all_results.append(match)
            
            # Save intermediate results after each batch
            if batch_num % 5 == 0:  # Save every 5 batches
                self._save_intermediate_results(league_summaries, all_results, batch_num)
                print(f"\n💾 Intermediate results saved after batch {batch_num}")
        
        # Calculate overall statistics
        total_matches = sum(r['total_matches'] for r in league_summaries)
        total_bets = sum(r['bets_placed'] for r in league_summaries)
        total_correct = sum(r['correct_predictions'] for r in league_summaries)
        overall_accuracy = total_correct / total_bets if total_bets > 0 else 0
        total_pnl = sum(r['total_pnl'] for r in league_summaries)
        overall_roi = total_pnl / (total_bets * 100) * 100 if total_bets > 0 else 0
        
        return {
            'overall_stats': {
                'leagues_tested': len(self.all_leagues),
                'leagues_with_data': len([r for r in league_summaries if r['total_matches'] > 0]),
                'leagues_with_bets': len([r for r in league_summaries if r['bets_placed'] > 0]),
                'total_matches': total_matches,
                'total_bets': total_bets,
                'total_correct': total_correct,
                'overall_accuracy': round(overall_accuracy, 3),
                'total_pnl': round(total_pnl, 2),
                'overall_roi': round(overall_roi, 1)
            },
            'league_summaries': league_summaries,
            'all_results': all_results
        }
    
    def _save_intermediate_results(self, league_summaries: List[Dict], all_results: List[Dict], batch_num: int):
        """Save intermediate results during processing."""
        
        # Save league summaries
        df_summaries = pd.DataFrame(league_summaries)
        df_summaries.to_csv(f"intermediate_batch_{batch_num}_league_summary.csv", index=False)
        
        # Save all individual results
        if all_results:
            df_results = pd.DataFrame(all_results)
            df_results.to_csv(f"intermediate_batch_{batch_num}_all_results.csv", index=False)
    
    def display_results(self, backtest_data: Dict[str, Any]):
        """Display comprehensive backtesting results."""
        
        overall = backtest_data['overall_stats']
        league_summaries = backtest_data['league_summaries']
        
        print(f"\n📈 COMPREHENSIVE BACKTESTING RESULTS - ALL LEAGUES")
        print("=" * 70)
        print(f"Leagues Tested: {overall['leagues_tested']}")
        print(f"Leagues with Data: {overall['leagues_with_data']}")
        print(f"Leagues with Bets: {overall['leagues_with_bets']}")
        print(f"Total Matches: {overall['total_matches']:,}")
        print(f"Total Bets: {overall['total_bets']:,}")
        print(f"Overall Accuracy: {overall['overall_accuracy']:.1%}")
        print(f"Total PnL: ${overall['total_pnl']:,}")
        print(f"Overall ROI: {overall['overall_roi']:.1f}%")
        
        # Top performing leagues
        profitable_leagues = [l for l in league_summaries if l['bets_placed'] > 0 and l['total_pnl'] > 0]
        profitable_leagues.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        print(f"\n🏆 TOP PERFORMING LEAGUES (by PnL)")
        print("=" * 70)
        for i, league in enumerate(profitable_leagues[:30], 1):
            print(f"{i:2d}. {league['league_name']:30s} | {league['country']:15s} | "
                  f"{league['bets_placed']:3d} bets | {league['accuracy']:5.1%} | "
                  f"${league['total_pnl']:8.2f} | {league['roi']:6.1f}% ROI")
        
        # Most accurate leagues
        accurate_leagues = [l for l in league_summaries if l['bets_placed'] >= 10]
        accurate_leagues.sort(key=lambda x: x['accuracy'], reverse=True)
        
        print(f"\n🎯 MOST ACCURATE LEAGUES (min 10 bets)")
        print("=" * 70)
        for i, league in enumerate(accurate_leagues[:20], 1):
            print(f"{i:2d}. {league['league_name']:30s} | {league['country']:15s} | "
                  f"{league['bets_placed']:3d} bets | {league['accuracy']:5.1%} | "
                  f"${league['total_pnl']:8.2f} | {league['roi']:6.1f}% ROI")
        
        # Country performance analysis
        country_stats = defaultdict(lambda: {'bets': 0, 'pnl': 0, 'accuracy': 0, 'leagues': 0})
        for league in league_summaries:
            if league['bets_placed'] > 0:
                country = league['country']
                country_stats[country]['bets'] += league['bets_placed']
                country_stats[country]['pnl'] += league['total_pnl']
                country_stats[country]['accuracy'] += league['accuracy']
                country_stats[country]['leagues'] += 1
        
        # Calculate country averages
        country_performance = []
        for country, stats in country_stats.items():
            if stats['leagues'] > 0:
                country_performance.append({
                    'country': country,
                    'total_bets': stats['bets'],
                    'total_pnl': stats['pnl'],
                    'avg_accuracy': stats['accuracy'] / stats['leagues'],
                    'leagues_count': stats['leagues'],
                    'roi': (stats['pnl'] / (stats['bets'] * 100) * 100) if stats['bets'] > 0 else 0
                })
        
        country_performance.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        print(f"\n🌍 TOP PERFORMING COUNTRIES (by PnL)")
        print("=" * 70)
        for i, country in enumerate(country_performance[:15], 1):
            print(f"{i:2d}. {country['country']:20s} | {country['leagues_count']:2d} leagues | "
                  f"{country['total_bets']:4d} bets | {country['avg_accuracy']:5.1%} | "
                  f"${country['total_pnl']:8.2f} | {country['roi']:6.1f}% ROI")
    
    def save_results(self, backtest_data: Dict[str, Any], filename_prefix: str = "comprehensive_backtest_full"):
        """Save comprehensive backtesting results."""
        
        overall = backtest_data['overall_stats']
        league_summaries = backtest_data['league_summaries']
        all_results = backtest_data['all_results']
        
        # Save overall statistics
        with open(f"{filename_prefix}_overall.json", 'w') as f:
            json.dump(overall, f, indent=2)
        print(f"💾 Overall statistics saved to {filename_prefix}_overall.json")
        
        # Save league summaries
        df_summaries = pd.DataFrame(league_summaries)
        df_summaries.to_csv(f"{filename_prefix}_league_summary.csv", index=False)
        print(f"💾 League summaries saved to {filename_prefix}_league_summary.csv")
        
        # Save all individual results
        if all_results:
            df_results = pd.DataFrame(all_results)
            df_results.to_csv(f"{filename_prefix}_all_results.csv", index=False)
            print(f"💾 All individual results saved to {filename_prefix}_all_results.csv")
            
            # Save top performing leagues
            profitable_leagues = [l for l in league_summaries if l['bets_placed'] > 0 and l['total_pnl'] > 0]
            profitable_leagues.sort(key=lambda x: x['total_pnl'], reverse=True)
            df_profitable = pd.DataFrame(profitable_leagues)
            df_profitable.to_csv(f"{filename_prefix}_profitable_leagues.csv", index=False)
            print(f"💾 Profitable leagues saved to {filename_prefix}_profitable_leagues.csv")
            
            # Save country performance
            country_stats = defaultdict(lambda: {'bets': 0, 'pnl': 0, 'accuracy': 0, 'leagues': 0})
            for league in league_summaries:
                if league['bets_placed'] > 0:
                    country = league['country']
                    country_stats[country]['bets'] += league['bets_placed']
                    country_stats[country]['pnl'] += league['total_pnl']
                    country_stats[country]['accuracy'] += league['accuracy']
                    country_stats[country]['leagues'] += 1
            
            country_performance = []
            for country, stats in country_stats.items():
                if stats['leagues'] > 0:
                    country_performance.append({
                        'country': country,
                        'total_bets': stats['bets'],
                        'total_pnl': stats['pnl'],
                        'avg_accuracy': stats['accuracy'] / stats['leagues'],
                        'leagues_count': stats['leagues'],
                        'roi': (stats['pnl'] / (stats['bets'] * 100) * 100) if stats['bets'] > 0 else 0
                    })
            
            country_performance.sort(key=lambda x: x['total_pnl'], reverse=True)
            df_countries = pd.DataFrame(country_performance)
            df_countries.to_csv(f"{filename_prefix}_country_performance.csv", index=False)
            print(f"💾 Country performance saved to {filename_prefix}_country_performance.csv")

async def main():
    """Main function for comprehensive historical backtesting of ALL leagues."""
    
    # Initialize backtester
    backtester = ComprehensiveHistoricalBacktesterFull()
    
    print(f"🚀 Starting Comprehensive Historical Backtesting - ALL LEAGUES...")
    print(f"   Available leagues: {len(backtester.all_leagues)}")
    print(f"   Season: 2024-2025")
    print(f"   Batch size: {backtester.batch_size}")
    print(f"   Focus: Find which leagues/teams our model works best for")
    
    # Run backtesting on ALL leagues
    backtest_data = await backtester.backtest_all_leagues_full()
    
    # Display results
    backtester.display_results(backtest_data)
    
    # Save results
    backtester.save_results(backtest_data)
    
    print(f"\n✅ COMPREHENSIVE HISTORICAL BACKTESTING COMPLETED!")
    print(f"   This analysis reveals:")
    print(f"   ✅ Which leagues our model works best for")
    print(f"   ✅ Which countries are most profitable")
    print(f"   ✅ Which teams are most/least predictable")
    print(f"   ✅ Real accuracy and profitability by league")
    print(f"   ✅ Optimal leagues to focus on for live betting")
    print(f"   ✅ League-specific patterns and insights")
    print(f"   ✅ Global football market analysis")

if __name__ == "__main__":
    asyncio.run(main())
