# Betfair Odds Extraction Results

## 🎯 Successfully Completed!

The Betfair odds extraction has been successfully completed for both Premier League and Scottish Premiership fixtures.

## 📊 Results Summary

### Premier League (ENP_2024-2025_M.xlsx)
- **Total Fixtures**: 417
- **Fixtures with Odds**: 286
- **Coverage**: 68.6%
- **Output File**: `ENP_2024-2025_M_avg10min_fixed.xlsx`

### Scottish Premiership (SC0_FM_Final_FX.xlsx)
- **Total Fixtures**: 228
- **Fixtures with Odds**: 187
- **Coverage**: 82.0%
- **Output File**: `SC0_FM_Final_FX_avg10min_fixed.xlsx`

## 📈 Odds Statistics (Premier League)
- **Mean**: 2.561
- **Minimum**: 1.096
- **Maximum**: 7.480
- **Standard Deviation**: 1.241

## 🔧 Technical Details

### What Was Extracted
- **Market**: First Half Goals 0.5
- **Runner**: Under 0.5 Goals (Runner ID: 5851482)
- **Data**: Last Traded Price (LTP) ticks
- **Time Window**: Last 10 ticks (representing last 10 minutes before kickoff)
- **Calculation**: Average of recent LTP ticks

### Team Name Matching
Successfully matched fixtures using comprehensive team aliases:
- Manchester United → Man Utd, Man United, Manchester Utd
- Tottenham Hotspur → Tottenham, Spurs, Tottenham H
- Heart of Midlothian → Hearts, Hearts FC
- And many more variations...

## 📁 Generated Files

1. **`ENP_2024-2025_M_avg10min_fixed.xlsx`** - Premier League with odds
2. **`SC0_FM_Final_FX_avg10min_fixed.xlsx`** - Scottish Premiership with odds

Both files contain:
- ✅ All original columns preserved
- ✅ New column: `HTU0_5_Avg10min` with average Under 0.5 Goals odds
- ✅ Ready for analysis and betting strategy development

## 🎲 Sample Results

### Premier League Sample
| Home Team | Away Team | Date | HTU0_5_Avg10min |
|-----------|-----------|------|------------------|
| Arsenal | Wolves | 2024-08-16 | 2.814 |
| Brentford | Crystal Palace | 2024-08-16 | 1.904 |
| Chelsea | Man City | 2024-08-16 | 2.993 |
| Everton | Brighton | 2024-08-16 | 2.124 |
| Ipswich | Liverpool | 2024-08-16 | 1.194 |

### Scottish Premiership Sample
| Home Team | Away Team | Date | HTU0_5_Avg10min |
|-----------|-----------|------|------------------|
| Hearts | Rangers | 2024-08-03 | 2.803 |
| Dundee United | Dundee | 2024-08-04 | 3.067 |
| St Mirren | Hibernian | 2024-08-04 | 1.186 |
| Celtic | Kilmarnock | 2024-08-04 | 5.060 |
| St Johnstone | Aberdeen | 2024-08-05 | 1.276 |

## 🚀 Next Steps

The extracted odds data is now ready for:
1. **Lay Betting Analysis**: Use the `HTU0_5_Avg10min` column for betting calculations
2. **Strategy Development**: Compare actual odds with your model predictions
3. **Backtesting**: Apply your first-half goal models with real market odds
4. **Profit/Loss Calculations**: Calculate theoretical PnL using these odds

## 📋 Files Used

- **Betfair Archive**: `data/GB_24_25.tar` (8,165 bz2 files processed)
- **Script**: `betfair_odds_extractor_fixed.py`
- **Total Matches Found**: 6,966 matches with odds data
- **Processing Time**: ~2-3 minutes per file

The extraction successfully processed the entire Betfair Great Britain archive and matched a significant portion of your fixture data with real market odds!
