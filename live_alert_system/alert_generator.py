"""Alert generation module for the live betting alert system."""

import os
import pytz
from datetime import datetime
from typing import List, Dict
from config import OUTPUT_DIRECTORY, TIMESTAMP_FORMAT, DATE_FORMAT


class AlertGenerator:
    """Handles generation of betting alert files."""
    
    def __init__(self):
        # Create output directory if it doesn't exist
        os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
    
    def _format_match_time(self, match_date_str: str) -> str:
        """Format match time to display in Pacific time."""
        try:
            # Parse the match date (should already be in Pacific time from match_discovery)
            if 'T' in match_date_str:
                # Handle timezone-aware datetime
                if '+' in match_date_str or 'Z' in match_date_str:
                    if 'Z' in match_date_str:
                        dt = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                    else:
                        dt = datetime.fromisoformat(match_date_str)
                    
                    # Convert to Pacific time
                    pacific_tz = pytz.timezone('US/Pacific')
                    dt_pacific = dt.astimezone(pacific_tz)
                    return dt_pacific.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    # Assume it's already in Pacific time format
                    return match_date_str[:19].replace('T', ' ')
            else:
                return match_date_str
        except Exception:
            # Fallback to original string if parsing fails
            return match_date_str[:19].replace('T', ' ') if 'T' in match_date_str else match_date_str
    
    def generate_alert_file(self, analysis_results: List[Dict], total_matches_scanned: int) -> str:
        """Generate the betting alert text file."""
        
        # Separate alert and non-alert matches
        alert_matches = [r for r in analysis_results if r["should_alert"]]
        non_alert_matches = [r for r in analysis_results if not r["should_alert"]]
        
        # Generate filename with current date
        current_date = datetime.now().strftime(DATE_FORMAT)
        filename = os.path.join(OUTPUT_DIRECTORY, f"betting_alerts_{current_date}.txt")
        
        # Generate content
        content = self._generate_content(
            alert_matches, 
            non_alert_matches, 
            total_matches_scanned,
            len(analysis_results)
        )
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filename
    
    def _generate_content(self, alert_matches: List[Dict], non_alert_matches: List[Dict], 
                         total_scanned: int, teams_with_data: int) -> str:
        """Generate the content for the alert file."""
        
        # Use Pacific time for display
        pacific_tz = pytz.timezone('US/Pacific')
        current_time_pacific = datetime.now(pacific_tz).strftime(TIMESTAMP_FORMAT)
        current_date_pacific = datetime.now(pacific_tz).strftime(DATE_FORMAT)
        
        content = f"""LIVE BETTING ALERTS - {current_date_pacific}
{'='*50}
Generated at: {current_time_pacific} (Pacific Time)
Scan period: Next 24 hours (Pacific Time)

"""
        
        if alert_matches:
            content += f"""ALERT MATCHES (≥1.5 avg first-half goals):
{'='*45}
"""
            for i, match in enumerate(alert_matches, 1):
                formatted_time = self._format_match_time(match['match_date'])
                content += f"""{i}. {match['home_team_name']} vs {match['away_team_name']}
   League: {match['league_name']} ({match['country']})
   Date: {formatted_time} (Pacific Time)
   Home Avg: {match['home_avg']:.2f} | Away Avg: {match['away_avg']:.2f} | Combined: {match['combined_avg']:.2f}
   ✅ BETTING ALERT

"""
        else:
            content += "ALERT MATCHES (≥1.5 avg first-half goals):\n"
            content += "=" * 45 + "\n"
            content += "No matches meet the alert criteria.\n\n"
        
        if non_alert_matches:
            content += f"""NO ALERT MATCHES (<1.5 avg):
{'='*30}
"""
            for i, match in enumerate(non_alert_matches, len(alert_matches) + 1):
                content += f"""{i}. {match['home_team_name']} vs {match['away_team_name']}
   League: {match['league_name']} ({match['country']})
   Combined: {match['combined_avg']:.2f} (below threshold)

"""
        
        # Summary
        alert_rate = (len(alert_matches) / teams_with_data * 100) if teams_with_data > 0 else 0
        
        content += f"""SUMMARY:
{'='*10}
Total matches scanned: {total_scanned}
Teams with sufficient data: {teams_with_data}
Matches meeting criteria: {len(alert_matches)}
Alert rate: {alert_rate:.1f}%

BETTING STRATEGY:
================
Target: First Half Over 0.5 Goals
Method: Lay betting (betting against Under 0.5)
Threshold: Combined team average ≥ 1.5 first-half goals
Minimum data: 4 matches per team

RECOMMENDED STAKING:
===================
- Flat stake per bet (e.g., $100)
- Commission: 2% on winning bets
- Expected ROI: Based on historical backtesting

DISCLAIMER:
===========
This is an automated analysis tool. Always do your own research
and never bet more than you can afford to lose. Past performance
does not guarantee future results.
"""
        
        return content
    
    def print_summary(self, analysis_results: List[Dict], total_matches_scanned: int):
        """Print a summary to console."""
        
        alert_matches = [r for r in analysis_results if r["should_alert"]]
        teams_with_data = len(analysis_results)
        
        print(f"\n🎯 BETTING ALERT SUMMARY")
        print(f"{'='*30}")
        print(f"Total matches scanned: {total_matches_scanned}")
        print(f"Teams with sufficient data: {teams_with_data}")
        print(f"Matches meeting criteria: {len(alert_matches)}")
        
        if teams_with_data > 0:
            alert_rate = len(alert_matches) / teams_with_data * 100
            print(f"Alert rate: {alert_rate:.1f}%")
        
        if alert_matches:
            print(f"\n✅ ALERT MATCHES ({len(alert_matches)}):")
            for match in alert_matches[:5]:  # Show first 5
                print(f"  • {match['home_team_name']} vs {match['away_team_name']} ({match['combined_avg']:.2f})")
            
            if len(alert_matches) > 5:
                print(f"  ... and {len(alert_matches) - 5} more")
        else:
            print(f"\n❌ No matches meet the alert criteria today")
