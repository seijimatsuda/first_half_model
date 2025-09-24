#!/usr/bin/env python3
"""
Chat interface for the enhanced live betting alert system.
Allows running the system through chat commands.
"""

import asyncio
import os
import sys
from typing import List, Dict, Optional
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from start_betting_alerts import EnhancedLiveBettingScanner
from search_specific import SpecificSearchScanner
from progress_tracker import ProgressTracker


class ChatInterface:
    """Chat interface for running the betting alert system."""
    
    def __init__(self):
        self.full_scanner = EnhancedLiveBettingScanner()
        self.specific_scanner = SpecificSearchScanner()
    
    async def run_full_scan(self) -> str:
        """Run the full worldwide scan and return results summary."""
        print("🚀 Starting full worldwide scan...")
        
        try:
            # Run the full scan
            await self.full_scanner.run_scan_with_progress()
            
            # Get the latest alert file
            alert_files = self._get_latest_alert_files("betting_alerts_")
            if alert_files:
                latest_file = alert_files[0]
                return f"✅ Full scan completed! Results saved to: {latest_file}"
            else:
                return "✅ Full scan completed! Check the betting_alerts directory for results."
                
        except Exception as e:
            return f"❌ Error during full scan: {e}"
    
    async def search_league(self, country: str, league_name: str = None) -> str:
        """Search for a specific league and return results."""
        print(f"🔍 Searching for league in {country}...")
        
        try:
            # Get leagues for the country
            leagues = await self.specific_scanner._get_leagues_by_country(country)
            
            if not leagues:
                return f"❌ No leagues found for country: {country}"
            
            # If league_name is specified, find it
            if league_name:
                selected_league = None
                for league in leagues:
                    if league_name.lower() in league['name'].lower():
                        selected_league = league
                        break
                
                if not selected_league:
                    return f"❌ League '{league_name}' not found in {country}. Available leagues: {[l['name'] for l in leagues[:5]]}"
            else:
                # Return list of available leagues
                league_list = "\n".join([f"{i+1}. {league['name']} ({league['type']})" for i, league in enumerate(leagues[:10])])
                return f"📋 Found {len(leagues)} leagues in {country}:\n{league_list}\n\n💡 Specify a league name to analyze it."
            
            # Analyze the selected league
            await self.specific_scanner._analyze_league(selected_league)
            
            # Get the latest league alert file
            alert_files = self._get_latest_alert_files(f"league_{selected_league['name'].replace(' ', '_')}")
            if alert_files:
                latest_file = alert_files[0]
                return f"✅ League analysis completed! Results saved to: {latest_file}"
            else:
                return f"✅ League analysis completed! Check the betting_alerts directory for results."
                
        except Exception as e:
            return f"❌ Error during league search: {e}"
    
    async def search_team(self, team_name: str) -> str:
        """Search for a specific team's next match and return results."""
        print(f"⚽ Searching for team: {team_name}...")
        
        try:
            # Find the team
            team_info = await self.specific_scanner._find_team(team_name)
            
            if not team_info:
                return f"❌ Team not found: {team_name}. Try a different spelling or check the team name."
            
            # Find next match
            next_match = await self.specific_scanner._find_next_match(team_info['id'])
            
            if not next_match:
                return f"❌ No upcoming matches found for {team_info['name']}"
            
            # Analyze the match
            await self.specific_scanner._analyze_team_match(team_info, next_match)
            
            # Get the latest team alert file
            alert_files = self._get_latest_alert_files(f"team_{team_info['name'].replace(' ', '_')}")
            if alert_files:
                latest_file = alert_files[0]
                return f"✅ Team analysis completed! Results saved to: {latest_file}"
            else:
                return f"✅ Team analysis completed! Check the betting_alerts directory for results."
                
        except Exception as e:
            return f"❌ Error during team search: {e}"
    
    def _get_latest_alert_files(self, prefix: str) -> List[str]:
        """Get the latest alert files with the given prefix."""
        try:
            alert_dir = "betting_alerts"
            if not os.path.exists(alert_dir):
                return []
            
            files = [f for f in os.listdir(alert_dir) if f.startswith(prefix) and f.endswith('.txt')]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(alert_dir, x)), reverse=True)
            
            return [os.path.join(alert_dir, f) for f in files]
        except:
            return []
    
    def get_help(self) -> str:
        """Get help information for chat commands."""
        return """
🤖 CHAT INTERFACE HELP
======================

Available commands:

1. **Full Scan**
   - "Run full scan"
   - "Scan all leagues"
   - "Get worldwide alerts"

2. **League Search**
   - "Search [country] leagues"
   - "Find leagues in [country]"
   - "Analyze [league name] in [country]"

3. **Team Search**
   - "Find [team name] next match"
   - "Search for [team name]"
   - "Analyze [team name]"

4. **Help**
   - "Help"
   - "Show commands"
   - "What can you do?"

Examples:
- "Run full scan"
- "Search England leagues"
- "Analyze Premier League in England"
- "Find Manchester United next match"
- "Search for Real Madrid"

💡 The system will automatically generate focused output files and open them for you!
"""
    
    async def process_command(self, command: str) -> str:
        """Process a chat command and return the result."""
        command = command.lower().strip()
        
        # Full scan commands
        if any(phrase in command for phrase in ["run full scan", "scan all leagues", "get worldwide alerts", "full scan"]):
            return await self.run_full_scan()
        
        # League search commands
        elif "search" in command and "leagues" in command:
            # Extract country from command
            words = command.split()
            country = None
            for i, word in enumerate(words):
                if word == "leagues" and i > 0:
                    country = words[i-1]
                    break
            
            if country:
                return await self.search_league(country)
            else:
                return "❌ Please specify a country. Example: 'Search England leagues'"
        
        elif "analyze" in command and "in" in command:
            # Extract league and country
            words = command.split()
            league_parts = []
            country = None
            
            for i, word in enumerate(words):
                if word == "in" and i < len(words) - 1:
                    country = words[i + 1]
                    league_parts = words[1:i]
                    break
            
            if country and league_parts:
                league_name = " ".join(league_parts)
                return await self.search_league(country, league_name)
            else:
                return "❌ Please specify league and country. Example: 'Analyze Premier League in England'"
        
        # Team search commands
        elif any(phrase in command for phrase in ["find", "search for", "analyze"]) and any(phrase in command for phrase in ["next match", "match"]):
            # Extract team name
            words = command.split()
            team_parts = []
            
            for i, word in enumerate(words):
                if word in ["find", "search", "analyze"] and i < len(words) - 1:
                    # Get everything after the action word until "next" or "match"
                    for j in range(i + 1, len(words)):
                        if words[j] in ["next", "match"]:
                            break
                        team_parts.append(words[j])
                    break
            
            if team_parts:
                team_name = " ".join(team_parts)
                return await self.search_team(team_name)
            else:
                return "❌ Please specify a team name. Example: 'Find Manchester United next match'"
        
        # Help commands
        elif any(phrase in command for phrase in ["help", "show commands", "what can you do"]):
            return self.get_help()
        
        else:
            return f"❌ Command not recognized: '{command}'\n\n{self.get_help()}"


# Example usage
async def main():
    """Example usage of the chat interface."""
    interface = ChatInterface()
    
    # Example commands
    commands = [
        "Run full scan",
        "Search England leagues",
        "Analyze Premier League in England",
        "Find Manchester United next match",
        "Help"
    ]
    
    for command in commands:
        print(f"\n💬 Command: {command}")
        result = await interface.process_command(command)
        print(f"🤖 Result: {result}")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
