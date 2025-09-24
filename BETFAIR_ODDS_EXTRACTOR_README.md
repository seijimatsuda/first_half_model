# Betfair Odds Extractor

This tool extracts the last 10 minutes of Under 0.5 Goals odds from Betfair tar archives and maps them to Excel fixture files.

## Files Created

1. **`betfair_odds_extractor.py`** - Main extraction class with all functionality
2. **`extract_odds_for_fixtures.py`** - Simple script for single file processing
3. **`batch_extract_odds.py`** - Batch processing for multiple Excel files

## Features

- ✅ Loads Excel fixture files and normalizes team names
- ✅ Extracts data from Betfair tar archives (bz2 compressed JSON streams)
- ✅ Identifies Half-Time Over/Under 0.5 Goals markets with flexible pattern matching
- ✅ Finds "Under 0.5" runners within those markets
- ✅ Collects LTP (Last Traded Price) ticks from last 10 minutes before kickoff
- ✅ Computes average of those ticks
- ✅ Maps results back to Excel fixtures with date and team name matching
- ✅ Adds new column `HTU0_5_Avg10min` to Excel files
- ✅ Preserves all original columns
- ✅ Provides coverage summary and sample results

## Usage

### Single File Processing
```bash
python extract_odds_for_fixtures.py
```

### Batch Processing (Multiple Excel Files)
```bash
python batch_extract_odds.py
```

## Market Pattern Matching

The tool recognizes various Betfair market naming conventions:
- "First Half Goals 0.5"
- "Half Time Over/Under 0.5 Goals"
- "Over/Under 0.5 Goals 1st Half"
- "1st Half Over/Under 0.5 Goals"
- "Half Time Goals 0.5"
- "HT Over/Under 0.5 Goals"
- "1H Over/Under 0.5 Goals"

## Runner Pattern Matching

Identifies "Under 0.5" runners with patterns like:
- "Under 0.5"
- "Under 0.5 Goals"
- "U 0.5"
- "U 0.5 Goals"

## Team Name Normalization

Includes comprehensive team aliases for:
- **Premier League**: Manchester United → Man Utd, etc.
- **Scottish Premiership**: Heart of Midlothian → Hearts, etc.
- **Common variations**: United → Utd, City → C, etc.

## Output

- Creates new Excel files with `_avg10min.xlsx` suffix
- Preserves all original columns
- Adds `HTU0_5_Avg10min` column with average odds
- Shows coverage summary (total fixtures, filled, unfilled)
- Displays sample results (first 5 rows with values)

## Example Output

```
=== RESULTS SUMMARY ===
Total fixtures: 417
Filled with odds: 380
Unfilled: 37
Coverage: 91.1%

=== SAMPLE RESULTS (First 5) ===
    Home Team           Away Team        Date  HTU0_5_Avg10min
0   Arsenal         Wolverhampton Wanderers  2024-08-16      2.45
1   Brentford       Crystal Palace          2024-08-16      1.89
2   Chelsea         Manchester City         2024-08-16      3.12
3   Everton         Brighton                2024-08-16      2.67
4   Ipswich         Liverpool               2024-08-17      1.45
```

## Configuration

Update file paths in the scripts:
- `tar_path` - Path to your Betfair tar archive
- `excel_path` - Path to your Excel fixture file
- `data_directory` - Directory containing multiple Excel files (for batch processing)

## Tested With

- ✅ Premier League fixtures (ENP_2024-2025_M.xlsx)
- ✅ Scottish Premiership fixtures (SC0_FM_Final_FX.xlsx)
- ✅ GB_24_25.tar Betfair archive

## Requirements

- pandas
- numpy
- openpyxl (for Excel file handling)

Install with:
```bash
pip install pandas numpy openpyxl
```
