#!/usr/bin/env python3
"""
Full worldwide betting alert scanner.
Scans all leagues and generates comprehensive alerts with progress tracking.
"""

import asyncio
import subprocess
import os
import sys
from datetime import datetime
from typing import List, Dict
from live_betting_scanner import LiveBettingScanner
from progress_tracker import ProgressTracker, NestedProgressTracker


class EnhancedLiveBettingScanner(LiveBettingScanner):
    """Enhanced version of LiveBettingScanner with progress tracking."""
    
    def __init__(self):
        super().__init__()
        self.progress_tracker = None
    
    async def run_scan_with_progress(self) -> None:
        """Execute the complete betting alert scan with progress tracking."""
        
        print("🚀 Starting Enhanced Live Betting Alert System")
        print("=" * 60)
        print(f"📊 Threshold: 1.5 first-half goals")
        print(f"📈 Minimum matches required: 4")
        print(f"⏰ Scan period: Next 24 hours")
        print("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Initialize nested progress tracker
            self.progress_tracker = NestedProgressTracker(4, "Full Betting Alert Scan")
            
            # Step 1: Get all leagues
            print("\n🔍 Step 1: Discovering leagues...")
            league_tracker = self.progress_tracker.start_operation("League Discovery", 1)
            league_tracker.update(0, "Fetching all available leagues...")
            
            leagues = await self.league_scanner.get_all_leagues()
            league_tracker.update(1, "Leagues discovered successfully")
            self.progress_tracker.finish_operation("League Discovery")
            
            if not leagues:
                print("❌ No leagues found. Exiting.")
                return
            
            # Step 2: Get upcoming matches
            print(f"\n🏈 Step 2: Scanning {len(leagues)} leagues for upcoming matches...")
            match_tracker = self.progress_tracker.start_operation("Match Scanning", len(leagues))
            
            league_ids = [league["id"] for league in leagues]
            matches = await self._scan_matches_with_progress(league_ids, match_tracker)
            self.progress_tracker.finish_operation("Match Scanning")
            
            if not matches:
                print("❌ No upcoming matches found. Exiting.")
                return
            
            # Step 3: Analyze matches
            print(f"\n⚽ Step 3: Analyzing {len(matches)} matches...")
            analysis_tracker = self.progress_tracker.start_operation("Team Analysis", len(matches))
            
            analysis_results = await self._analyze_matches_with_progress(matches, analysis_tracker)
            self.progress_tracker.finish_operation("Team Analysis")
            
            # Step 4: Generate alerts
            print("\n📊 Step 4: Generating alerts...")
            alert_tracker = self.progress_tracker.start_operation("Alert Generation", 1)
            alert_tracker.update(0, "Generating comprehensive alert file...")
            
            alert_file = self.alert_generator.generate_alert_file(analysis_results, len(matches))
            alert_tracker.update(1, "Alert file generated successfully")
            self.progress_tracker.finish_operation("Alert Generation")
            
            # Step 5: Auto-open file and show summary
            print("\n📁 Step 5: Opening results...")
            self._open_alert_file(alert_file)
            
            # Final summary
            self.progress_tracker.finish_all()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n✅ Full scan completed successfully!")
            print(f"📁 Alert file: {alert_file}")
            print(f"⏱️  Total duration: {self._format_duration(duration)}")
            print(f"📊 Matches analyzed: {len(matches)}")
            print(f"🎯 Teams with data: {len(analysis_results)}")
            
            # Show alert summary
            alert_matches = [r for r in analysis_results if r["should_alert"]]
            if alert_matches:
                print(f"🚨 Alert matches: {len(alert_matches)}")
                print(f"📈 Alert rate: {len(alert_matches)/len(analysis_results)*100:.1f}%")
            else:
                print("❌ No matches meet the alert criteria today")
            
        except Exception as e:
            print(f"\n❌ Error during scan: {e}")
            print(f"📁 Check the error details above for troubleshooting")
            raise
    
    async def _scan_matches_with_progress(self, league_ids: List[int], tracker: ProgressTracker) -> List[Dict]:
        """Scan matches with progress tracking."""
        matches = []
        
        for i, league_id in enumerate(league_ids):
            try:
                tracker.update(i, f"Scanning league {league_id}...")
                
                # Get current season for this league
                league_season = await self.league_scanner._get_current_season(league_id, None)
                if not league_season:
                    continue
                
                # Get matches for this league
                league_matches = await self.league_scanner.get_upcoming_matches([league_id])
                matches.extend(league_matches)
                
            except Exception as e:
                print(f"⚠️ Error scanning league {league_id}: {e}")
                continue
        
        tracker.update(len(league_ids), "Match scanning completed")
        return matches
    
    async def _analyze_matches_with_progress(self, matches: List[Dict], tracker: ProgressTracker) -> List[Dict]:
        """Analyze matches with progress tracking."""
        analysis_results = []
        
        for i, match in enumerate(matches):
            try:
                # Update progress with current match info
                home_team = match.get('home_team_name', 'Unknown')
                away_team = match.get('away_team_name', 'Unknown')
                tracker.update(i, f"Analyzing {home_team} vs {away_team}...")
                
                result = await self.team_analyzer.analyze_match(match)
                if result:
                    analysis_results.append(result)
                    
            except Exception as e:
                print(f"⚠️ Error analyzing match {match.get('fixture_id', 'unknown')}: {e}")
                continue
        
        tracker.update(len(matches), "Match analysis completed")
        return analysis_results
    
    def _open_alert_file(self, filepath: str):
        """Open the alert file with the default application."""
        try:
            if os.path.exists(filepath):
                if sys.platform.startswith('win'):
                    os.startfile(filepath)
                elif sys.platform.startswith('darwin'):  # macOS
                    subprocess.run(['open', filepath], check=True)
                else:  # Linux and others
                    subprocess.run(['xdg-open', filepath], check=True)
                print(f"📁 File opened: {filepath}")
            else:
                print(f"❌ File not found: {filepath}")
        except Exception as e:
            print(f"⚠️ Could not auto-open file: {e}")
            print(f"📁 Please open manually: {filepath}")
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in a readable format."""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            remaining_seconds = int(seconds % 60)
            return f"{hours}h {minutes}m {remaining_seconds}s"


async def main():
    """Main execution function for full scan."""
    try:
        scanner = EnhancedLiveBettingScanner()
        await scanner.run_scan_with_progress()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Scan interrupted by user")
        print("👋 Goodbye!")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("🔧 Please check your configuration and try again")
        sys.exit(1)


if __name__ == "__main__":
    # Check if we're in the right directory
    if not os.path.exists("config.py"):
        print("❌ Error: config.py not found")
        print("💡 Please run this script from the live_alert_system directory")
        sys.exit(1)
    
    # Run the enhanced scanner
    asyncio.run(main())
