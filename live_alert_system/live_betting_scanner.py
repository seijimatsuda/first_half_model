"""Main execution script for the live betting alert system."""

import asyncio
from datetime import datetime
from typing import List, Dict

from league_scanner import LeagueScanner
from team_analyzer import TeamAnalyzer
from alert_generator import AlertGenerator
from config import COMBINED_THRESHOLD, MIN_MATCHES_REQUIRED


class LiveBettingScanner:
    """Main class that orchestrates the entire betting alert system."""
    
    def __init__(self):
        self.league_scanner = LeagueScanner()
        self.team_analyzer = TeamAnalyzer()
        self.alert_generator = AlertGenerator()
    
    async def run_scan(self) -> None:
        """Execute the complete betting alert scan."""
        
        print("🚀 Starting Live Betting Alert System")
        print(f"📊 Threshold: {COMBINED_THRESHOLD} first-half goals")
        print(f"📈 Minimum matches required: {MIN_MATCHES_REQUIRED}")
        print("-" * 50)
        
        start_time = datetime.now()
        
        try:
            # Step 1: Get all leagues
            print("Step 1: Discovering leagues...")
            leagues = await self.league_scanner.get_all_leagues()
            
            if not leagues:
                print("❌ No leagues found. Exiting.")
                return
            
            # Step 2: Get upcoming matches
            print("Step 2: Scanning for upcoming matches...")
            league_ids = [league["id"] for league in leagues]
            matches = await self.league_scanner.get_upcoming_matches(league_ids)
            
            if not matches:
                print("❌ No upcoming matches found. Exiting.")
                return
            
            # Step 3: Analyze matches
            print("Step 3: Analyzing team performance...")
            analysis_results = await self._analyze_matches(matches)
            
            # Step 4: Generate alerts
            print("Step 4: Generating alerts...")
            alert_file = self.alert_generator.generate_alert_file(analysis_results, len(matches))
            
            # Step 5: Print summary
            self.alert_generator.print_summary(analysis_results, len(matches))
            
            # Final summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n✅ Scan completed successfully!")
            print(f"📁 Alert file: {alert_file}")
            print(f"⏱️ Duration: {duration:.1f} seconds")
            
        except Exception as e:
            print(f"❌ Error during scan: {e}")
            raise
    
    async def _analyze_matches(self, matches: List[Dict]) -> List[Dict]:
        """Analyze all matches and return results."""
        
        analysis_results = []
        total_matches = len(matches)
        
        for i, match in enumerate(matches, 1):
            if i % 10 == 0 or i == total_matches:
                print(f"  Analyzing match {i}/{total_matches}...")
            
            try:
                result = await self.team_analyzer.analyze_match(match)
                if result:
                    analysis_results.append(result)
            except Exception as e:
                print(f"⚠️ Error analyzing match {match.get('fixture_id', 'unknown')}: {e}")
                continue
        
        return analysis_results
    
    def should_alert(self, home_avg: float, away_avg: float) -> bool:
        """Determine if a match should trigger an alert."""
        combined = (home_avg + away_avg) / 2
        return combined >= COMBINED_THRESHOLD


async def main():
    """Main execution function."""
    
    scanner = LiveBettingScanner()
    await scanner.run_scan()


if __name__ == "__main__":
    asyncio.run(main())
