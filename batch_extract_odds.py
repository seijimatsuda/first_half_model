#!/usr/bin/env python3
"""
Batch process multiple Excel fixture files with the same Betfair tar archive
"""

from betfair_odds_extractor import BetfairOddsExtractor
import os
import glob

def main():
    extractor = BetfairOddsExtractor()
    
    # Configuration
    tar_path = "/Users/seijimatsuda/first_half_model/data/GB_24_25.tar"
    data_directory = "/Users/seijimatsuda/first_half_model/data/"
    
    # Find all Excel files in the data directory
    excel_files = glob.glob(os.path.join(data_directory, "*.xlsx"))
    
    print("=== Batch Betfair Odds Extractor ===")
    print(f"Tar file: {tar_path}")
    print(f"Found {len(excel_files)} Excel files:")
    
    for excel_file in excel_files:
        print(f"  - {os.path.basename(excel_file)}")
    
    if not os.path.exists(tar_path):
        print(f"ERROR: Tar file not found: {tar_path}")
        return
    
    if not excel_files:
        print("ERROR: No Excel files found in data directory")
        return
    
    # Process each Excel file
    successful = 0
    failed = 0
    
    for excel_path in excel_files:
        print(f"\n{'='*60}")
        print(f"Processing: {os.path.basename(excel_path)}")
        print(f"{'='*60}")
        
        try:
            extractor.process_betfair_archive(tar_path, excel_path)
            successful += 1
            print(f"✅ Successfully processed: {os.path.basename(excel_path)}")
        except Exception as e:
            failed += 1
            print(f"❌ Failed to process: {os.path.basename(excel_path)}")
            print(f"Error: {e}")
    
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Total files: {len(excel_files)}")

if __name__ == "__main__":
    main()
