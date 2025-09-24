#!/usr/bin/env python3
"""
Simple script to extract Betfair odds for Excel fixtures
Usage: python extract_odds_for_fixtures.py
"""

from betfair_odds_extractor import BetfairOddsExtractor
import os

def main():
    extractor = BetfairOddsExtractor()
    
    # File paths - UPDATE THESE TO MATCH YOUR FILES
    tar_path = "/Users/seijimatsuda/first_half_model/data/GB_24_25.tar"
    excel_path = "/Users/seijimatsuda/first_half_model/data/ENP_2024-2025_M.xlsx"
    
    # Alternative paths you might have:
    # excel_path = "/Users/seijimatsuda/first_half_model/data/SC0_FM_Final_FX.xlsx"  # Scottish Premiership
    
    print("=== Betfair Odds Extractor ===")
    print(f"Tar file: {tar_path}")
    print(f"Excel file: {excel_path}")
    
    # Check if files exist
    if not os.path.exists(tar_path):
        print(f"ERROR: Tar file not found: {tar_path}")
        return
    
    if not os.path.exists(excel_path):
        print(f"ERROR: Excel file not found: {excel_path}")
        return
    
    # Process the files
    try:
        extractor.process_betfair_archive(tar_path, excel_path)
        print("\n✅ Processing completed successfully!")
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
