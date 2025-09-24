#!/usr/bin/env python3
"""
Extract all matches from GB_24_25.tar dataset with correct market type
"""

import tarfile
import bz2
import json
import pandas as pd

# Runner IDs for "Under 0.5 Goals" and "Over 0.5 Goals" in FIRST_HALF_GOALS_05 market
UNDER_05_GOALS_RUNNER_ID = 5851482
OVER_05_GOALS_RUNNER_ID = 5851483

def extract_all_gb_matches(tar_path):
    """Extract all match information from the tar file"""
    print("Extracting all matches from GB_24_25.tar...")
    
    all_matches = []
    match_count = 0
    processed_files = 0
    
    with tarfile.open(tar_path, "r") as tar:
        bz2_files = [m for m in tar.getmembers() if m.name.endswith('.bz2')]
        print(f"Found {len(bz2_files)} bz2 files to process")
        
        for i, member in enumerate(bz2_files):
            processed_files += 1
            if processed_files % 1000 == 0:
                print(f"Processed {processed_files}/{len(bz2_files)} files, found {match_count} matches")
            
            try:
                extracted_bz2 = tar.extractfile(member)
                if extracted_bz2:
                    decompressed_data = bz2.decompress(extracted_bz2.read()).decode('utf-8')
                    lines = decompressed_data.strip().split('\n')
                    
                    # Get match info from first line
                    if lines:
                        first_line_data = json.loads(lines[0])
                        if 'mc' in first_line_data and first_line_data['mc']:
                            market_definition = first_line_data['mc'][0].get('marketDefinition')
                            if market_definition:
                                event_name = market_definition.get('eventName')
                                market_name = market_definition.get('name')
                                market_type = market_definition.get('marketType')
                                
                                # Look for FIRST_HALF_GOALS_05 markets
                                if (event_name and 
                                    " v " in event_name and 
                                    market_type == "FIRST_HALF_GOALS_05" and
                                    "Test" not in event_name):  # Exclude test events
                                    
                                    match_count += 1
                                    
                                    # Try to extract odds from the data
                                    under_05_odds = None
                                    over_05_odds = None
                                    
                                    # Look through lines for odds data
                                    for line in reversed(lines):  # Start from end to get latest odds
                                        data = json.loads(line)
                                        if 'mc' in data and data['mc']:
                                            for market_change in data['mc']:
                                                if 'rc' in market_change:
                                                    for runner_change in market_change['rc']:
                                                        if runner_change.get('id') == UNDER_05_GOALS_RUNNER_ID and 'ltp' in runner_change:
                                                            under_05_odds = runner_change['ltp']
                                                        if runner_change.get('id') == OVER_05_GOALS_RUNNER_ID and 'ltp' in runner_change:
                                                            over_05_odds = runner_change['ltp']
                                                    if under_05_odds and over_05_odds:
                                                        break
                                            if under_05_odds and over_05_odds:
                                                break
                                    
                                    all_matches.append({
                                        'file_path': member.name,
                                        'event_name': event_name,
                                        'market_name': market_name,
                                        'market_type': market_type,
                                        'under_05_odds': under_05_odds,
                                        'over_05_odds': over_05_odds,
                                        'lines_count': len(lines)
                                    })
                                    
            except Exception as e:
                pass
    
    print(f"Extraction complete: {match_count} matches found")
    return all_matches

def analyze_matches(matches):
    """Analyze the extracted matches"""
    if not matches:
        print("No matches found!")
        return
    
    df = pd.DataFrame(matches)
    
    print(f"\n=== GB_24_25.tar MATCH ANALYSIS ===")
    print(f"Total matches found: {len(df)}")
    
    # Check for matches with odds
    with_odds = df[(df['under_05_odds'].notna()) & (df['over_05_odds'].notna())]
    print(f"Matches with odds data: {len(with_odds)}")
    
    if len(with_odds) > 0:
        print(f"Under 0.5 Goals odds range: {with_odds['under_05_odds'].min():.2f} - {with_odds['under_05_odds'].max():.2f}")
        print(f"Over 0.5 Goals odds range: {with_odds['over_05_odds'].min():.2f} - {with_odds['over_05_odds'].max():.2f}")
    
    # Show sample matches
    print(f"\n=== SAMPLE MATCHES ===")
    sample_df = df.head(20)[['event_name', 'under_05_odds', 'over_05_odds']]
    print(sample_df.to_string(index=False))
    
    # Save to CSV
    df.to_csv('gb_24_25_all_matches.csv', index=False)
    print(f"\nAll matches saved to gb_24_25_all_matches.csv")
    
    # Show unique event names
    print(f"\n=== ALL UNIQUE EVENT NAMES ===")
    unique_events = sorted(df['event_name'].unique())
    print(f"Total unique events: {len(unique_events)}")
    
    for i, event in enumerate(unique_events):
        print(f"{i+1:3d}. {event}")
    
    return df

def main():
    tar_path = '/Users/seijimatsuda/first_half_model/data/GB_24_25.tar'
    
    print("=== EXTRACTING GB_24_25.tar MATCHES ===")
    matches = extract_all_gb_matches(tar_path)
    
    if matches:
        df = analyze_matches(matches)
        return df
    else:
        print("No matches found in the tar file!")
        return None

if __name__ == "__main__":
    main()
