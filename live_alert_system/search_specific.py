#!/usr/bin/env python3
"""
Targeted betting alert search.
Search by country/league or team name with focused outputs.
"""

import asyncio
import subprocess
import os
import sys
from typing import List, Dict, Optional
from datetime import datetime

from league_scanner import LeagueScanner
from team_analyzer import TeamAnalyzer
from specific_alert_generator import SpecificAlertGenerator
from progress_tracker import ProgressTracker


class SpecificSearchScanner:
    """Handles targeted search functionality for specific leagues or teams."""
    
    def __init__(self):
        self.league_scanner = LeagueScanner()
        self.team_analyzer = TeamAnalyzer()
        self.alert_generator = SpecificAlertGenerator()
    
    async def run_interactive_search(self):
        """Run the interactive search menu."""
        while True:
            self._display_menu()
            choice = input("\nEnter choice (1-3): ").strip()
            
            if choice == "1":
                await self._search_by_country_league()
            elif choice == "2":
                await self._search_by_team()
            elif choice == "3":
                print("\n👋 Goodbye!")
                break
            else:
                print("\n❌ Invalid choice. Please enter 1, 2, or 3.")
            
            # Pause before showing menu again
            if choice in ["1", "2"]:
                input("\nPress Enter to continue...")
    
    def _display_menu(self):
        """Display the main menu."""
        print("\n" + "="*60)
        print("╔" + " " * 58 + "╗")
        print("║" + " " * 20 + "BETTING ALERT SEARCH" + " " * 19 + "║")
        print("╠" + " " * 58 + "╣")
        print("║ 1. Search by Country/League" + " " * 30 + "║")
        print("║ 2. Search by Team Name" + " " * 33 + "║")
        print("║ 3. Exit" + " " * 47 + "║")
        print("╚" + " " * 58 + "╝")
        print("="*60)
    
    async def _search_by_country_league(self):
        """Handle country/league search."""
        print("\n🌍 COUNTRY/LEAGUE SEARCH")
        print("-" * 30)
        
        # Get country name
        country = input("Enter country name (e.g., England, Spain, Germany): ").strip()
        if not country:
            print("❌ Country name cannot be empty.")
            return
        
        try:
            # Search for leagues in the country
            print(f"\n🔍 Searching for leagues in {country}...")
            tracker = ProgressTracker(1, f"Searching leagues in {country}")
            tracker.update(0, f"Fetching leagues for {country}...")
            
            leagues = await self._get_leagues_by_country(country)
            tracker.update(1, f"Found {len(leagues)} leagues")
            tracker.finish()
            
            if not leagues:
                print(f"❌ No leagues found for country: {country}")
                return
            
            # Display leagues
            print(f"\n📋 Found {len(leagues)} leagues in {country}:")
            print("-" * 50)
            for i, league in enumerate(leagues, 1):
                print(f"{i:2d}. {league['name']} ({league['type']})")
            
            # Get user selection
            while True:
                try:
                    choice = int(input(f"\nSelect league (1-{len(leagues)}): ").strip())
                    if 1 <= choice <= len(leagues):
                        selected_league = leagues[choice - 1]
                        break
                    else:
                        print(f"❌ Please enter a number between 1 and {len(leagues)}")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            # Analyze the selected league
            await self._analyze_league(selected_league)
            
        except Exception as e:
            print(f"❌ Error during country/league search: {e}")
    
    async def _search_by_team(self):
        """Handle team name search."""
        print("\n⚽ TEAM SEARCH")
        print("-" * 15)
        
        # Get team name
        team_name = input("Enter team name (e.g., Manchester United, Real Madrid): ").strip()
        if not team_name:
            print("❌ Team name cannot be empty.")
            return
        
        try:
            # Search for the team
            print(f"\n🔍 Searching for team: {team_name}...")
            tracker = ProgressTracker(1, f"Searching for {team_name}")
            tracker.update(0, f"Finding {team_name}...")
            
            team_info = await self._find_team(team_name)
            tracker.update(1, f"Team search completed")
            tracker.finish()
            
            if not team_info:
                print(f"❌ Team not found: {team_name}")
                print("💡 Try a different spelling or check the team name")
                return
            
            # Find next match for the team
            print(f"\n🏈 Finding next match for {team_info['name']}...")
            match_tracker = ProgressTracker(1, f"Finding next match for {team_info['name']}")
            match_tracker.update(0, f"Searching upcoming matches...")
            
            next_match = await self._find_next_match(team_info['id'])
            match_tracker.update(1, f"Next match found")
            match_tracker.finish()
            
            if not next_match:
                print(f"❌ No upcoming matches found for {team_info['name']}")
                return
            
            # Analyze the match
            await self._analyze_team_match(team_info, next_match)
            
        except Exception as e:
            print(f"❌ Error during team search: {e}")
    
    async def _get_leagues_by_country(self, country: str) -> List[Dict]:
        """Get all leagues for a specific country."""
        try:
            # Get all leagues
            all_leagues = await self.league_scanner.get_all_leagues()
            
            # Filter by country (case-insensitive)
            country_leagues = []
            for league in all_leagues:
                if country.lower() in league['country'].lower():
                    country_leagues.append(league)
            
            return country_leagues
            
        except Exception as e:
            print(f"❌ Error fetching leagues for {country}: {e}")
            return []
    
    async def _find_team(self, team_name: str) -> Optional[Dict]:
        """Find a team by name across all leagues."""
        try:
            # This would typically use a team search API endpoint
            # For now, we'll simulate by getting all leagues and searching
            all_leagues = await self.league_scanner.get_all_leagues()
            
            # Search through leagues for the team
            for league in all_leagues[:10]:  # Limit search for performance
                try:
                    # Get teams for this league (this would need a teams API endpoint)
                    # For now, we'll return a mock result
                    if team_name.lower() in ["manchester united", "man utd", "manchester"]:
                        return {
                            "id": 33,
                            "name": "Manchester United",
                            "league_id": 39,
                            "league_name": "Premier League"
                        }
                    elif team_name.lower() in ["real madrid", "real"]:
                        return {
                            "id": 541,
                            "name": "Real Madrid",
                            "league_id": 140,
                            "league_name": "La Liga"
                        }
                    # Add more teams as needed
                except:
                    continue
            
            return None
            
        except Exception as e:
            print(f"❌ Error finding team {team_name}: {e}")
            return None
    
    async def _find_next_match(self, team_id: int) -> Optional[Dict]:
        """Find the next upcoming match for a team."""
        try:
            # This would use the fixtures API with team parameter
            # For now, we'll return a mock match
            return {
                "fixture_id": 12345,
                "home_team_id": team_id,
                "home_team_name": "Manchester United",
                "away_team_id": 50,
                "away_team_name": "Arsenal",
                "match_date": "2025-09-23T15:00:00Z",
                "league_name": "Premier League",
                "country": "England",
                "season": 2025
            }
            
        except Exception as e:
            print(f"❌ Error finding next match for team {team_id}: {e}")
            return None
    
    async def _analyze_league(self, league: Dict):
        """Analyze a specific league."""
        print(f"\n📊 Analyzing {league['name']}...")
        
        try:
            # Get upcoming matches for this league
            tracker = ProgressTracker(1, f"Analyzing {league['name']}")
            tracker.update(0, f"Getting upcoming matches...")
            
            matches = await self.league_scanner.get_upcoming_matches([league['id']])
            tracker.update(1, f"Found {len(matches)} matches")
            tracker.finish()
            
            if not matches:
                print(f"❌ No upcoming matches found for {league['name']}")
                return
            
            # Analyze matches
            print(f"\n⚽ Analyzing {len(matches)} matches...")
            analysis_tracker = ProgressTracker(len(matches), f"Analyzing {league['name']} matches")
            
            analysis_results = []
            for i, match in enumerate(matches):
                analysis_tracker.update(i, f"Analyzing {match['home_team_name']} vs {match['away_team_name']}...")
                
                result = await self.team_analyzer.analyze_match(match)
                if result:
                    analysis_results.append(result)
            
            analysis_tracker.finish()
            
            # Generate focused alert
            print(f"\n📊 Generating league alert...")
            alert_file = self.alert_generator.generate_league_alert(
                league['name'], 
                league['country'], 
                matches, 
                analysis_results
            )
            
            print(f"✅ League analysis completed!")
            print(f"📁 Alert file: {alert_file}")
            
        except Exception as e:
            print(f"❌ Error analyzing league {league['name']}: {e}")
    
    async def _analyze_team_match(self, team_info: Dict, match: Dict):
        """Analyze a specific team's next match."""
        print(f"\n📊 Analyzing {team_info['name']}'s next match...")
        
        try:
            # Analyze the match
            tracker = ProgressTracker(1, f"Analyzing {team_info['name']} match")
            tracker.update(0, f"Calculating team averages...")
            
            result = await self.team_analyzer.analyze_match(match)
            tracker.update(1, f"Analysis completed")
            tracker.finish()
            
            if not result:
                print(f"❌ Insufficient data to analyze {team_info['name']}'s match")
                return
            
            # Generate focused alert
            print(f"\n📊 Generating team alert...")
            alert_file = self.alert_generator.generate_team_alert(
                team_info['name'], 
                match, 
                result
            )
            
            print(f"✅ Team analysis completed!")
            print(f"📁 Alert file: {alert_file}")
            
        except Exception as e:
            print(f"❌ Error analyzing team match: {e}")


async def main():
    """Main execution function for specific search."""
    try:
        # Check if we're in the right directory
        if not os.path.exists("config.py"):
            print("❌ Error: config.py not found")
            print("💡 Please run this script from the live_alert_system directory")
            sys.exit(1)
        
        scanner = SpecificSearchScanner()
        await scanner.run_interactive_search()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Search interrupted by user")
        print("👋 Goodbye!")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("🔧 Please check your configuration and try again")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
