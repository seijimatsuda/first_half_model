#!/usr/bin/env python3
"""
Examine the structure of GB_24_25.tar to understand market types and data format
"""

import tarfile
import bz2
import json
from collections import defaultdict

def examine_gb_structure(tar_path, sample_size=100):
    """Examine the structure of the GB tar file"""
    print(f"Examining structure of {sample_size} files from GB_24_25.tar...")
    
    market_types = defaultdict(int)
    market_names = defaultdict(int)
    event_names = []
    sample_events = []
    
    with tarfile.open(tar_path, "r") as tar:
        bz2_files = [m for m in tar.getmembers() if m.name.endswith('.bz2')]
        
        for i, member in enumerate(bz2_files[:sample_size]):
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
                                
                                if event_name:
                                    event_names.append(event_name)
                                    
                                    # Collect market type and name info
                                    if market_type:
                                        market_types[market_type] += 1
                                    if market_name:
                                        market_names[market_name] += 1
                                    
                                    # Store sample events
                                    if len(sample_events) < 20:
                                        sample_events.append({
                                            'file': member.name,
                                            'event_name': event_name,
                                            'market_name': market_name,
                                            'market_type': market_type,
                                            'lines_count': len(lines)
                                        })
                                    
            except Exception as e:
                pass
    
    print(f"\n=== MARKET TYPES FOUND ===")
    for market_type, count in sorted(market_types.items(), key=lambda x: x[1], reverse=True):
        print(f"{market_type}: {count}")
    
    print(f"\n=== MARKET NAMES FOUND ===")
    for market_name, count in sorted(market_names.items(), key=lambda x: x[1], reverse=True):
        print(f"{market_name}: {count}")
    
    print(f"\n=== SAMPLE EVENTS ===")
    for i, event in enumerate(sample_events):
        print(f"{i+1:2d}. {event['event_name']}")
        print(f"    Market: {event['market_name']}")
        print(f"    Type: {event['market_type']}")
        print(f"    Lines: {event['lines_count']}")
        print()
    
    # Look for first half over/under markets
    print(f"=== SEARCHING FOR FIRST HALF MARKETS ===")
    first_half_markets = []
    
    with tarfile.open(tar_path, "r") as tar:
        bz2_files = [m for m in tar.getmembers() if m.name.endswith('.bz2')]
        
        for i, member in enumerate(bz2_files[:500]):  # Check first 500 files
            try:
                extracted_bz2 = tar.extractfile(member)
                if extracted_bz2:
                    decompressed_data = bz2.decompress(extracted_bz2.read()).decode('utf-8')
                    lines = decompressed_data.strip().split('\n')
                    
                    if lines:
                        first_line_data = json.loads(lines[0])
                        if 'mc' in first_line_data and first_line_data['mc']:
                            market_definition = first_line_data['mc'][0].get('marketDefinition')
                            if market_definition:
                                event_name = market_definition.get('eventName')
                                market_name = market_definition.get('name')
                                market_type = market_definition.get('marketType')
                                
                                # Look for first half or over/under markets
                                if (market_name and 
                                    ('First Half' in market_name or 
                                     '1st Half' in market_name or
                                     'Over/Under' in market_name or
                                     '0.5' in market_name)):
                                    
                                    first_half_markets.append({
                                        'event_name': event_name,
                                        'market_name': market_name,
                                        'market_type': market_type,
                                        'file': member.name
                                    })
                                    
                                    if len(first_half_markets) >= 20:
                                        break
                                    
            except Exception as e:
                pass
    
    print(f"Found {len(first_half_markets)} first half markets:")
    for i, market in enumerate(first_half_markets):
        print(f"{i+1:2d}. {market['event_name']}")
        print(f"    Market: {market['market_name']}")
        print(f"    Type: {market['market_type']}")
        print()

def main():
    tar_path = '/Users/seijimatsuda/first_half_model/data/GB_24_25.tar'
    examine_gb_structure(tar_path)

if __name__ == "__main__":
    main()
