"""Specific alert generator module for focused output formats."""

import os
import subprocess
import platform
from datetime import datetime
from typing import List, Dict, Optional
from config import OUTPUT_DIRECTORY, TIMESTAMP_FORMAT, DATE_FORMAT


class SpecificAlertGenerator:
    """Handles generation of focused, detailed output formats for specific searches."""
    
    def __init__(self):
        """Initialize with output directory and formatting settings."""
        # Create output directory if it doesn't exist
        os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
        
        # Platform-specific file opening commands
        self.system = platform.system().lower()
        if self.system == "windows":
            self.open_command = "start"
        elif self.system == "darwin":  # macOS
            self.open_command = "open"
        else:  # Linux and others
            self.open_command = "xdg-open"
    
    def generate_league_alert(self, league_name: str, country: str, 
                            matches: List[Dict], analysis_results: List[Dict]) -> str:
        """Generate focused format for specific league results."""
        
        # Separate alert and non-alert matches
        alert_matches = [r for r in analysis_results if r["should_alert"]]
        non_alert_matches = [r for r in analysis_results if not r["should_alert"]]
        
        # Generate filename
        safe_league_name = self._sanitize_filename(league_name)
        current_date = datetime.now().strftime(DATE_FORMAT)
        filename = os.path.join(OUTPUT_DIRECTORY, f"league_{safe_league_name}_{current_date}.txt")
        
        # Generate content
        content = self._generate_league_content(
            league_name, country, matches, alert_matches, non_alert_matches, analysis_results
        )
        
        # Save and open file
        return self.save_and_open_file(content, filename)
    
    def generate_team_alert(self, team_name: str, match: Dict, 
                          analysis_result: Dict) -> str:
        """Generate focused format for specific team's next match."""
        
        # Generate filename
        safe_team_name = self._sanitize_filename(team_name)
        current_date = datetime.now().strftime(DATE_FORMAT)
        filename = os.path.join(OUTPUT_DIRECTORY, f"team_{safe_team_name}_{current_date}.txt")
        
        # Generate content
        content = self._generate_team_content(team_name, match, analysis_result)
        
        # Save and open file
        return self.save_and_open_file(content, filename)
    
    def _generate_league_content(self, league_name: str, country: str, 
                               matches: List[Dict], alert_matches: List[Dict], 
                               non_alert_matches: List[Dict], analysis_results: List[Dict]) -> str:
        """Generate the content for league-specific alerts."""
        
        current_time = datetime.now().strftime(TIMESTAMP_FORMAT)
        current_date = datetime.now().strftime(DATE_FORMAT)
        
        content = f"""{league_name.upper()} BETTING ALERTS - {current_date}
{'='*60}
Generated at: {current_time}
League: {league_name} ({country})
Total matches: {len(matches)}
Analysis period: Next 24 hours

"""
        
        if alert_matches:
            content += f"""ALERT MATCHES (≥1.5 avg first-half goals):
{'='*50}
"""
            for i, match in enumerate(alert_matches, 1):
                content += f"""{i}. {match['home_team_name']} vs {match['away_team_name']}
   Date: {match['match_date'][:19].replace('T', ' ')}
   Home Avg: {match['home_avg']:.2f} | Away Avg: {match['away_avg']:.2f} | Combined: {match['combined_avg']:.2f}
   ✅ BETTING ALERT

"""
        else:
            content += """ALERT MATCHES (≥1.5 avg first-half goals):
==================================================
No matches meet the alert criteria.

"""
        
        if non_alert_matches:
            content += f"""NO ALERT MATCHES (<1.5 avg):
{'='*35}
"""
            for i, match in enumerate(non_alert_matches, len(alert_matches) + 1):
                content += f"""{i}. {match['home_team_name']} vs {match['away_team_name']}
   Date: {match['match_date'][:19].replace('T', ' ')}
   Combined: {match['combined_avg']:.2f} (below threshold)

"""
        
        # League summary
        teams_with_data = len(analysis_results)
        alert_rate = (len(alert_matches) / teams_with_data * 100) if teams_with_data > 0 else 0
        
        content += f"""LEAGUE SUMMARY:
{'='*20}
Total matches analyzed: {len(matches)}
Teams with sufficient data: {teams_with_data}
Matches meeting criteria: {len(alert_matches)}
Alert rate: {alert_rate:.1f}%

BETTING STRATEGY:
=================
Target: First Half Over 0.5 Goals
Method: Lay betting (betting against Under 0.5)
Threshold: Combined team average ≥ 1.5 first-half goals
Minimum data: 4 matches per team

DISCLAIMER:
===========
This is an automated analysis tool. Always do your own research
and never bet more than you can afford to lose. Past performance
does not guarantee future results.
"""
        
        return content
    
    def _generate_team_content(self, team_name: str, match: Dict, analysis_result: Dict) -> str:
        """Generate the content for team-specific alerts."""
        
        current_time = datetime.now().strftime(TIMESTAMP_FORMAT)
        current_date = datetime.now().strftime(DATE_FORMAT)
        
        # Extract match details
        home_team = match['home_team_name']
        away_team = match['away_team_name']
        league_name = match['league_name']
        country = match['country']
        match_date = match['match_date'][:19].replace('T', ' ')
        
        # Extract analysis details
        home_avg = analysis_result['home_avg']
        away_avg = analysis_result['away_avg']
        combined_avg = analysis_result['combined_avg']
        should_alert = analysis_result['should_alert']
        
        content = f"""{team_name.upper()} NEXT MATCH ANALYSIS
{'='*50}
Generated at: {current_time}

MATCH DETAILS:
{'='*15}
{home_team} vs {away_team}
League: {league_name} ({country})
Date: {match_date}

TEAM ANALYSIS:
{'='*15}
Home Team: {home_team}
- Average first-half goals (home matches): {home_avg:.2f}
- Matches analyzed: [Data from API]

Away Team: {away_team}
- Average first-half goals (away matches): {away_avg:.2f}
- Matches analyzed: [Data from API]

COMBINED ANALYSIS:
{'='*20}
Combined Average: {combined_avg:.2f} first-half goals
Threshold: 1.5 first-half goals
Status: {'MEETS THRESHOLD' if should_alert else 'BELOW THRESHOLD'}

RECOMMENDATION:
{'='*15}
{'✅ BETTING ALERT - Combined average ≥ 1.5' if should_alert else '❌ NO ALERT - Combined average < 1.5'}
Target: First Half Over 0.5 Goals
Method: Lay betting (betting against Under 0.5)
Confidence: {'High' if should_alert else 'Low'} (both teams have sufficient data)

HISTORICAL CONTEXT:
{'='*20}
{home_team} home first-half goals:
- Season average: {home_avg:.2f} first-half goals
- Analysis based on recent home matches

{away_team} away first-half goals:
- Season average: {away_avg:.2f} first-half goals
- Analysis based on recent away matches

BETTING STRATEGY:
=================
Target: First Half Over 0.5 Goals
Method: Lay betting (betting against Under 0.5)
Threshold: Combined team average ≥ 1.5 first-half goals
Minimum data: 4 matches per team

DISCLAIMER:
===========
This is an automated analysis tool. Always do your own research
and never bet more than you can afford to lose. Past performance
does not guarantee future results.
"""
        
        return content
    
    def save_and_open_file(self, content: str, filename: str) -> str:
        """Save content to file and auto-open it."""
        try:
            # Save content to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Auto-open file
            try:
                if self.system == "windows":
                    os.startfile(filename)
                else:
                    subprocess.run([self.open_command, filename], check=True)
                print(f"📁 File opened automatically: {filename}")
            except Exception as e:
                print(f"⚠️  Could not auto-open file: {e}")
                print(f"📁 File saved to: {filename}")
            
            return filename
            
        except Exception as e:
            print(f"❌ Error saving file: {e}")
            raise
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename by removing invalid characters."""
        # Replace invalid filename characters with underscores
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Remove extra spaces and limit length
        name = '_'.join(name.split())
        return name[:50]  # Limit filename length
    
    def generate_custom_alert(self, title: str, content: str, filename_prefix: str = "custom") -> str:
        """Generate a custom alert with specified content."""
        current_date = datetime.now().strftime(DATE_FORMAT)
        safe_title = self._sanitize_filename(title)
        filename = os.path.join(OUTPUT_DIRECTORY, f"{filename_prefix}_{safe_title}_{current_date}.txt")
        
        # Add header to content
        current_time = datetime.now().strftime(TIMESTAMP_FORMAT)
        full_content = f"""{title.upper()}
{'='*len(title)}
Generated at: {current_time}

{content}

DISCLAIMER:
===========
This is an automated analysis tool. Always do your own research
and never bet more than you can afford to lose. Past performance
does not guarantee future results.
"""
        
        return self.save_and_open_file(full_content, filename)


# Example usage and testing
if __name__ == "__main__":
    # Test the specific alert generator
    generator = SpecificAlertGenerator()
    
    # Test league alert
    sample_matches = [
        {
            "home_team_name": "Manchester United",
            "away_team_name": "Arsenal",
            "match_date": "2025-09-23T15:00:00Z",
            "league_name": "Premier League",
            "country": "England"
        }
    ]
    
    sample_analysis = [
        {
            "home_team_name": "Manchester United",
            "away_team_name": "Arsenal",
            "match_date": "2025-09-23T15:00:00Z",
            "home_avg": 1.8,
            "away_avg": 1.2,
            "combined_avg": 1.5,
            "should_alert": True
        }
    ]
    
    print("Testing league alert generation...")
    league_file = generator.generate_league_alert(
        "Premier League", "England", sample_matches, sample_analysis
    )
    print(f"Generated: {league_file}")
    
    # Test team alert
    sample_match = {
        "home_team_name": "Manchester United",
        "away_team_name": "Arsenal",
        "match_date": "2025-09-23T15:00:00Z",
        "league_name": "Premier League",
        "country": "England"
    }
    
    sample_team_analysis = {
        "home_team_name": "Manchester United",
        "away_team_name": "Arsenal",
        "match_date": "2025-09-23T15:00:00Z",
        "home_avg": 1.8,
        "away_avg": 1.2,
        "combined_avg": 1.5,
        "should_alert": True
    }
    
    print("\nTesting team alert generation...")
    team_file = generator.generate_team_alert(
        "Manchester United", sample_match, sample_team_analysis
    )
    print(f"Generated: {team_file}")
    
    print("\n✅ Specific alert generator test completed!")
