#!/usr/bin/env python3
"""
Fixed examination of odds structure
"""

import json
import subprocess
import bz2
import os

def examine_file_with_odds(file_path):
    """Examine a specific file to find odds data"""
    print(f"=== Examining {file_path} ===")
    
    try:
        # Extract file
        subprocess.run(['tar', '-xf', 'data/GB_24_25.tar', file_path], 
                     cwd='/Users/seijimatsuda/first_half_model', 
                     capture_output=True)
        
        # Read file
        with bz2.open(file_path, 'rt') as f:
            lines = f.readlines()
            
            print(f"Total lines: {len(lines)}")
            
            # Look for lines with odds data
            for i, line in enumerate(lines):
                try:
                    data = json.loads(line)
                    
                    if 'mc' in data and len(data['mc']) > 0:
                        mc_data = data['mc'][0]
                        
                        # Check for odds data
                        if 'rc' in mc_data:
                            print(f"Line {i+1}: Found odds data")
                            rc_data = mc_data['rc']
                            
                            # Handle different rc structures
                            if isinstance(rc_data, dict):
                                print(f"  Runners: {list(rc_data.keys())}")
                                for runner_id, runner_data in rc_data.items():
                                    print(f"    Runner {runner_id}: {runner_data}")
                            elif isinstance(rc_data, list):
                                print(f"  Runners list: {len(rc_data)} items")
                                for j, runner_data in enumerate(rc_data):
                                    print(f"    Runner {j}: {runner_data}")
                        
                        # Check for market definition
                        if 'marketDefinition' in mc_data:
                            md = mc_data['marketDefinition']
                            if i == 0:  # First line
                                print(f"  Event: {md.get('eventName', 'N/A')}")
                                print(f"  Market: {md.get('name', 'N/A')}")
                                print(f"  Status: {md.get('status', 'N/A')}")
                
                except json.JSONDecodeError:
                    continue
        
        # Clean up
        os.remove(file_path)
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    # Examine a file with many lines (Man Utd v Fulham had 298 lines)
    examine_file_with_odds("BASIC/2024/Aug/16/33356474/1.229974298.bz2")

if __name__ == "__main__":
    main()
