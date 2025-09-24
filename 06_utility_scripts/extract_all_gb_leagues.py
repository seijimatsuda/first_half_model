#!/usr/bin/env python3
"""
Extract all leagues and matches from GB_24_25.tar dataset
"""

import tarfile
import json
import bz2
import pandas as pd
from collections import defaultdict
import re
from datetime import datetime

def extract_all_gb_leagues(tar_file_path):
    """Extract all leagues and matches from the GB dataset."""
    
    print("🔍 Extracting all leagues and matches from GB_24_25.tar...")
    print("=" * 60)
    
    leagues_data = defaultdict(lambda: {
        'matches': [],
        'date_range': set(),
        'total_events': 0
    })
    
    total_files = 0
    processed_files = 0
    
    try:
        with tarfile.open(tar_file_path, 'r') as tar:
            total_files = len(tar.getnames())
            print(f"Total files in archive: {total_files}")
            
            for member in tar.getmembers():
                if member.name.endswith('.bz2'):
                    try:
                        file_obj = tar.extractfile(member)
                        if file_obj:
                            decompressed = bz2.decompress(file_obj.read())
                            lines = decompressed.decode('utf-8').strip().split('\n')
                            
                            for line in lines:
                                if line.strip():
                                    try:
                                        data = json.loads(line)
                                        
                                        if 'mc' in data and data['mc']:
                                            for market in data['mc']:
                                                if 'marketDefinition' in market:
                                                    md = market['marketDefinition']
                                                    
                                                    # Check if it's a first half goals market
                                                    if 'name' in md and 'First Half Goals 0.5' in md['name']:
                                                        event_name = md.get('eventName', '')
                                                        event_id = md.get('eventId', '')
                                                        market_time = md.get('marketTime', '')
                                                        
                                                        # Extract league and teams
                                                        league, home_team, away_team = extract_league_and_teams(event_name)
                                                        
                                                        if league and home_team and away_team:
                                                            leagues_data[league]['total_events'] += 1
                                                            leagues_data[league]['date_range'].add(market_time[:10])
                                                            
                                                            # Store match info
                                                            match_info = {
                                                                'event_id': event_id,
                                                                'event_name': event_name,
                                                                'home_team': home_team,
                                                                'away_team': away_team,
                                                                'market_time': market_time,
                                                                'date': market_time[:10]
                                                            }
                                                            
                                                            # Avoid duplicates
                                                            if match_info not in leagues_data[league]['matches']:
                                                                leagues_data[league]['matches'].append(match_info)
                                        
                                    except json.JSONDecodeError:
                                        continue
                            
                            processed_files += 1
                            if processed_files % 500 == 0:
                                print(f"Processed {processed_files}/{total_files} files...")
                                
                    except Exception as e:
                        print(f"Error processing {member.name}: {e}")
                        continue
    
    except Exception as e:
        print(f"Error opening tar file: {e}")
        return None
    
    print(f"\n✅ Extraction complete! Processed {processed_files} files")
    
    # Convert to summary
    league_summary = []
    for league, data in leagues_data.items():
        if data['total_events'] > 0:
            date_range = sorted(data['date_range'])
            league_summary.append({
                'League': league,
                'Total_Events': data['total_events'],
                'Unique_Matches': len(data['matches']),
                'Date_Range': f"{date_range[0]} to {date_range[-1]}" if date_range else "Unknown",
                'Matches': data['matches']
            })
    
    # Sort by event count
    league_summary.sort(key=lambda x: x['Total_Events'], reverse=True)
    
    return league_summary

def extract_league_and_teams(event_name):
    """Extract league name and team names from event name."""
    
    # Common patterns for different leagues
    league_patterns = {
        'Premier League': r'(Arsenal|Chelsea|Liverpool|Man City|Man United|Tottenham|Newcastle|West Ham|Aston Villa|Brighton|Crystal Palace|Everton|Fulham|Leeds|Leicester|Southampton|Wolves|Brentford|Nottingham Forest|Sheffield United|Nottm Forest)',
        'Championship': r'(Championship|Norwich|Watford|Birmingham|Blackburn|Bristol City|Cardiff|Coventry|Huddersfield|Hull|Luton|Middlesbrough|Millwall|Preston|QPR|Reading|Rotherham|Stoke|Swansea|West Brom|Leeds|Sheffield Wednesday)',
        'League One': r'(League One|Barnsley|Blackpool|Bolton|Bristol Rovers|Burton|Cambridge|Charlton|Derby|Exeter|Fleetwood|Ipswich|Lincoln|MK Dons|Morecambe|Oxford|Peterborough|Plymouth|Portsmouth|Port Vale|Shrewsbury|Sunderland|Wigan|Wycombe)',
        'League Two': r'(League Two|AFC Wimbledon|Barrow|Bradford|Carlisle|Colchester|Crawley|Crewe|Doncaster|Forest Green|Gillingham|Grimsby|Harrogate|Hartlepool|Leyton Orient|Mansfield|Newport|Northampton|Oldham|Rochdale|Salford|Scunthorpe|Stevenage|Swindon|Tranmere|Walsall|Chesterfield|Fleetwood Town)',
        'Scottish Premiership': r'(Celtic|Rangers|Aberdeen|Hearts|Hibs|Motherwell|St Johnstone|Livingston|Ross County|St Mirren|Dundee|Kilmarnock)',
        'Scottish Championship': r'(Scottish Championship|Dundee United|Inverness|Partick Thistle|Ayr United|Dunfermline|Greenock Morton|Queen of the South|Raith Rovers)',
        'Scottish League One': r'(Scottish League One|Airdrieonians|Alloa|Clyde|Cove Rangers|East Fife|Falkirk|Forfar|Montrose|Peterhead|Stranraer)',
        'Scottish League Two': r'(Scottish League Two|Albion Rovers|Annan|Berwick|Cowdenbeath|Edinburgh City|Elgin|Stirling|Stenhousemuir)',
        'Women\'s Super League': r'(Women|WSL|Arsenal Women|Chelsea Women|Man City Women|Man United Women|Tottenham Women|Everton Women|Brighton Women|Aston Villa Women|West Ham Women|Birmingham Women|Reading Women)',
        'National League': r'(National League|Wrexham|Notts County|Chesterfield|Boreham Wood|Bromley|Dagenham|Eastleigh|FC Halifax|Gateshead|Grimsby|Hartlepool|Maidenhead|Maidstone|Oldham|Solihull|Southend|Stockport|Torquay|Woking|Yeovil)'
    }
    
    # Extract teams from event name
    teams = []
    if ' v ' in event_name:
        teams = event_name.split(' v ')
    elif ' vs ' in event_name:
        teams = event_name.split(' vs ')
    else:
        return None, None, None
    
    if len(teams) != 2:
        return None, None, None
    
    home_team = teams[0].strip()
    away_team = teams[1].strip()
    
    # Determine league based on team names
    for league, pattern in league_patterns.items():
        if re.search(pattern, event_name, re.IGNORECASE):
            return league, home_team, away_team
    
    # If no specific pattern matches, try to determine from team names
    all_teams = home_team + ' ' + away_team
    
    # Check for Premier League teams
    pl_teams = ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Man United', 'Tottenham', 'Newcastle', 'West Ham', 'Aston Villa', 'Brighton', 'Crystal Palace', 'Everton', 'Fulham', 'Leeds', 'Leicester', 'Southampton', 'Wolves', 'Brentford', 'Nottingham Forest', 'Sheffield United', 'Nottm Forest']
    if any(team in all_teams for team in pl_teams):
        return 'Premier League', home_team, away_team
    
    # Check for Championship teams
    champ_teams = ['Norwich', 'Watford', 'Birmingham', 'Blackburn', 'Bristol City', 'Cardiff', 'Coventry', 'Huddersfield', 'Hull', 'Luton', 'Middlesbrough', 'Millwall', 'Preston', 'QPR', 'Reading', 'Rotherham', 'Stoke', 'Swansea', 'West Brom', 'Sheffield Wednesday']
    if any(team in all_teams for team in champ_teams):
        return 'Championship', home_team, away_team
    
    # Check for Scottish teams
    scottish_teams = ['Celtic', 'Rangers', 'Aberdeen', 'Hearts', 'Hibs', 'Motherwell', 'St Johnstone', 'Livingston', 'Ross County', 'St Mirren', 'Dundee', 'Kilmarnock']
    if any(team in all_teams for team in scottish_teams):
        return 'Scottish Premiership', home_team, away_team
    
    # Check for League Two teams
    league_two_teams = ['AFC Wimbledon', 'Barrow', 'Bradford', 'Carlisle', 'Colchester', 'Crawley', 'Crewe', 'Doncaster', 'Forest Green', 'Gillingham', 'Grimsby', 'Harrogate', 'Hartlepool', 'Leyton Orient', 'Mansfield', 'Newport', 'Northampton', 'Oldham', 'Rochdale', 'Salford', 'Scunthorpe', 'Stevenage', 'Swindon', 'Tranmere', 'Walsall', 'Chesterfield', 'Fleetwood Town']
    if any(team in all_teams for team in league_two_teams):
        return 'League Two', home_team, away_team
    
    return 'Unknown', home_team, away_team

def main():
    """Main function to extract all GB leagues."""
    
    tar_file = 'data/GB_24_25.tar'
    
    print("🏴󠁧󠁢󠁥󠁮󠁧󠁿 Great Britain Leagues Extraction")
    print("=" * 60)
    
    league_summary = extract_all_gb_leagues(tar_file)
    
    if league_summary:
        print(f"\n📊 LEAGUE SUMMARY")
        print("=" * 60)
        
        total_matches = 0
        for league in league_summary:
            print(f"\n🏆 {league['League']}")
            print(f"   Total Events: {league['Total_Events']}")
            print(f"   Unique Matches: {league['Unique_Matches']}")
            print(f"   Date Range: {league['Date_Range']}")
            total_matches += league['Unique_Matches']
            
            # Show sample matches
            print(f"   Sample Matches:")
            for match in league['Matches'][:5]:
                print(f"     - {match['home_team']} v {match['away_team']} ({match['date']})")
            if len(league['Matches']) > 5:
                print(f"     ... and {len(league['Matches']) - 5} more matches")
        
        print(f"\n📈 TOTAL COVERAGE")
        print(f"   Total Leagues: {len(league_summary)}")
        print(f"   Total Unique Matches: {total_matches}")
        
        # Save detailed results
        all_matches = []
        for league in league_summary:
            for match in league['Matches']:
                all_matches.append({
                    'League': league['League'],
                    'Event_ID': match['event_id'],
                    'Event_Name': match['event_name'],
                    'Home_Team': match['home_team'],
                    'Away_Team': match['away_team'],
                    'Date': match['date'],
                    'Market_Time': match['market_time']
                })
        
        df = pd.DataFrame(all_matches)
        df.to_csv('all_gb_leagues_matches.csv', index=False)
        print(f"\n💾 All matches saved to: all_gb_leagues_matches.csv")
        
        # Save league summary
        summary_df = pd.DataFrame([{
            'League': league['League'],
            'Total_Events': league['Total_Events'],
            'Unique_Matches': league['Unique_Matches'],
            'Date_Range': league['Date_Range']
        } for league in league_summary])
        summary_df.to_csv('gb_leagues_summary.csv', index=False)
        print(f"💾 League summary saved to: gb_leagues_summary.csv")
        
    else:
        print("❌ Failed to extract leagues from dataset")

if __name__ == "__main__":
    main()
