#!/usr/bin/env python3
"""
Simple script to extract odds data from GB_24_25.tar
"""

import json
import subprocess
import pandas as pd
import bz2
import os

def extract_sample_odds():
    """Extract odds from a sample of files to understand structure"""
    print("Extracting sample odds data...")
    
    # Get list of files
    result = subprocess.run(['tar', '-tf', 'data/GB_24_25.tar'], 
                          capture_output=True, text=True, cwd='/Users/seijimatsuda/first_half_model')
    
    files = [f for f in result.stdout.strip().split('\n') if f.endswith('.bz2')]
    
    # Process first 20 files
    sample_files = files[:20]
    
    for i, file_path in enumerate(sample_files):
        print(f"\n=== Processing {file_path} ===")
        
        try:
            # Extract file
            subprocess.run(['tar', '-xf', 'data/GB_24_25.tar', file_path], 
                         cwd='/Users/seijimatsuda/first_half_model', 
                         capture_output=True)
            
            # Read file
            with bz2.open(file_path, 'rt') as f:
                lines = f.readlines()
                
                print(f"Number of lines: {len(lines)}")
                
                # Show first line structure
                if lines:
                    first_data = json.loads(lines[0])
                    print(f"First line keys: {list(first_data.keys())}")
                    
                    if 'mc' in first_data:
                        mc_data = first_data['mc'][0]
                        print(f"Market data keys: {list(mc_data.keys())}")
                        
                        if 'marketDefinition' in mc_data:
                            md = mc_data['marketDefinition']
                            print(f"Market name: {md.get('name', 'N/A')}")
                            print(f"Event name: {md.get('eventName', 'N/A')}")
                            print(f"Market type: {md.get('marketType', 'N/A')}")
                            print(f"Status: {md.get('status', 'N/A')}")
                            print(f"Runners: {len(md.get('runners', []))}")
                            
                            for runner in md.get('runners', []):
                                print(f"  Runner: {runner.get('name', 'N/A')} (ID: {runner.get('id', 'N/A')})")
                
                # Show last line structure
                if len(lines) > 1:
                    last_data = json.loads(lines[-1])
                    print(f"Last line keys: {list(last_data.keys())}")
                    
                    if 'mc' in last_data:
                        mc_data = last_data['mc'][0]
                        if 'rc' in mc_data:
                            print(f"Runners with odds: {len(mc_data['rc'])}")
                            
                            for runner_id, runner_data in mc_data['rc'].items():
                                print(f"  Runner {runner_id}: {runner_data}")
            
            # Clean up
            os.remove(file_path)
            
        except Exception as e:
            print(f"Error: {e}")
            continue

if __name__ == "__main__":
    extract_sample_odds()
