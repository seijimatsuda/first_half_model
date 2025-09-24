# 🚀 Enhanced Live Betting Alert System

A comprehensive Python-based system that scans worldwide football matches and generates betting alerts based on first-half goal analysis with **real-time progress tracking** and **targeted search capabilities**.

## ✨ **NEW FEATURES**

### 🎯 **Two Main Scripts**
1. **`start_betting_alerts.py`** - Full worldwide scan with progress tracking
2. **`search_specific.py`** - Targeted search by league or team

### 📊 **Real-Time Progress Tracking**
- Visual progress bars with Unicode characters
- Time elapsed and estimated remaining time
- Current operation display
- Smooth updates without terminal spam

### 🔍 **Targeted Search Options**
- **Country/League Search**: Select country → List leagues → Pick one → Analyze
- **Team Search**: Enter team name → Find next match → Analyze
- Focused output formats for specific searches

### 📁 **Auto-File Opening**
- Generated files open automatically
- Cross-platform compatibility (Windows, macOS, Linux)
- Clear file paths displayed in terminal

## 📁 **File Structure**

```
live_alert_system/
├── config.py                    # Configuration settings
├── league_scanner.py            # Discovers all available leagues
├── team_analyzer.py             # Calculates team performance metrics
├── alert_generator.py           # Generates full scan alerts
├── live_betting_scanner.py      # Original main execution script
├── progress_tracker.py          # 🆕 Progress bar and time tracking
├── specific_alert_generator.py  # 🆕 Focused output format generator
├── start_betting_alerts.py      # 🆕 Full worldwide scan script
├── search_specific.py           # 🆕 Targeted search script
├── test_system.py               # 🆕 System testing script
├── README.md                    # Original system documentation
├── ENHANCED_README.md           # 🆕 This enhanced documentation
└── betting_alerts/              # Output directory
    ├── betting_alerts_YYYY-MM-DD.txt           # Full scan results
    ├── league_[LEAGUE_NAME]_YYYY-MM-DD.txt     # League-specific results
    └── team_[TEAM_NAME]_YYYY-MM-DD.txt         # Team-specific results
```

## 🚀 **Quick Start**

### **Option 1: Full Worldwide Scan**
```bash
cd live_alert_system
python3 start_betting_alerts.py
```

**What it does:**
- Scans all available leagues worldwide
- Shows real-time progress with time estimates
- Generates comprehensive alert file
- Auto-opens the results file
- Displays summary statistics

### **Option 2: Targeted Search**
```bash
cd live_alert_system
python3 search_specific.py
```

**What it does:**
- Shows interactive menu
- Option 1: Search by country/league
- Option 2: Search by team name
- Generates focused output files
- Auto-opens the results

## 📊 **Progress Tracking Examples**

### **Full Scan Progress**
```
🚀 Starting Enhanced Live Betting Alert System
============================================================
📊 Threshold: 1.5 first-half goals
📈 Minimum matches required: 4
⏰ Scan period: Next 24 hours
============================================================

🔍 Step 1: Discovering leagues...
🚀 Starting: League Discovery
📊 Total steps: 1
------------------------------------------------------------
Fetching all available leagues... [██████████████████████████████████████████████████] 100.0% (2s elapsed, 0s remaining)
✅ Completed: League Discovery
⏱️  Total time: 2s
📊 Final progress: 1/1 steps
------------------------------------------------------------

🏈 Step 2: Scanning 500 leagues for upcoming matches...
🚀 Starting: Match Scanning
📊 Total steps: 500
------------------------------------------------------------
Scanning league 39... [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 16.0% (30s elapsed, 2m 30s remaining)
```

### **Team Analysis Progress**
```
⚽ Step 3: Analyzing 1,247 matches...
🚀 Starting: Team Analysis
📊 Total steps: 1,247
------------------------------------------------------------
Analyzing Manchester United vs Arsenal... [██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 60.0% (1m 45s elapsed, 1m 15s remaining)
```

## 🎯 **Search Options**

### **Country/League Search**
```
🌍 COUNTRY/LEAGUE SEARCH
------------------------------
Enter country name (e.g., England, Spain, Germany): England

🔍 Searching for leagues in England...
🚀 Starting: Searching leagues in England
📊 Total steps: 1
------------------------------------------------------------
Fetching leagues for England... [██████████████████████████████████████████████████] 100.0% (1s elapsed, 0s remaining)
✅ Completed: Searching leagues in England
⏱️  Total time: 1s
📊 Final progress: 1/1 steps
------------------------------------------------------------

📋 Found 15 leagues in England:
--------------------------------------------------
 1. Premier League (League)
 2. Championship (League)
 3. League One (League)
 4. League Two (League)
 5. National League (League)
 6. FA Cup (Cup)
 7. EFL Cup (Cup)
 8. Community Shield (Cup)
 9. Women's Super League (League)
10. Women's Championship (League)
11. U21 Premier League (League)
12. U18 Premier League (League)
13. U23 Premier League (League)
14. U19 Premier League (League)
15. U17 Premier League (League)

Select league (1-15): 1
```

### **Team Search**
```
⚽ TEAM SEARCH
---------------
Enter team name (e.g., Manchester United, Real Madrid): Manchester United

🔍 Searching for team: Manchester United...
🚀 Starting: Searching for Manchester United
📊 Total steps: 1
------------------------------------------------------------
Finding Manchester United... [██████████████████████████████████████████████████] 100.0% (1s elapsed, 0s remaining)
✅ Completed: Searching for Manchester United
⏱️  Total time: 1s
📊 Final progress: 1/1 steps
------------------------------------------------------------

🏈 Finding next match for Manchester United...
🚀 Starting: Finding next match for Manchester United
📊 Total steps: 1
------------------------------------------------------------
Searching upcoming matches... [██████████████████████████████████████████████████] 100.0% (1s elapsed, 0s remaining)
✅ Completed: Finding next match for Manchester United
⏱️  Total time: 1s
📊 Final progress: 1/1 steps
------------------------------------------------------------
```

## 📄 **Output Formats**

### **Full Scan Output**
```
LIVE BETTING ALERTS - 2025-09-23
==========================================
Generated at: 2025-09-23 10:30:00
Scan period: Next 24 hours

ALERT MATCHES (≥1.5 avg first-half goals):
==========================================
1. Manchester United vs Arsenal
   League: Premier League (England)
   Date: 2025-09-23 15:00:00
   Home Avg: 1.8 | Away Avg: 1.2 | Combined: 1.5
   ✅ BETTING ALERT

SUMMARY:
========
Total matches scanned: 1,247
Teams with sufficient data: 892
Matches meeting criteria: 23
Alert rate: 1.8%
```

### **League-Specific Output**
```
PREMIER LEAGUE BETTING ALERTS - 2025-09-23
==========================================
Generated at: 2025-09-23 10:30:00
League: Premier League (England)
Country: England
Total matches: 8
Analysis period: Next 24 hours

ALERT MATCHES (≥1.5 avg first-half goals):
==========================================
1. Manchester United vs Arsenal
   Date: 2025-09-23 15:00:00
   Home Avg: 1.8 | Away Avg: 1.2 | Combined: 1.5
   ✅ BETTING ALERT

LEAGUE SUMMARY:
===============
Total matches analyzed: 8
Teams with sufficient data: 6
Matches meeting criteria: 2
Alert rate: 25.0%
```

### **Team-Specific Output**
```
MANCHESTER UNITED NEXT MATCH ANALYSIS
====================================
Generated at: 2025-09-23 10:30:00

MATCH DETAILS:
==============
Manchester United vs Arsenal
League: Premier League (England)
Date: 2025-09-23 15:00:00

TEAM ANALYSIS:
==============
Home Team: Manchester United
- Average first-half goals (home matches): 1.80
- Matches analyzed: [Data from API]

Away Team: Arsenal
- Average first-half goals (away matches): 1.20
- Matches analyzed: [Data from API]

COMBINED ANALYSIS:
==================
Combined Average: 1.50 first-half goals
Threshold: 1.5 first-half goals
Status: MEETS THRESHOLD

RECOMMENDATION:
===============
✅ BETTING ALERT - Combined average ≥ 1.5
Target: First Half Over 0.5 Goals
Method: Lay betting (betting against Under 0.5)
Confidence: High (both teams have sufficient data)
```

## ⚙️ **Configuration**

All settings are in `config.py`:

```python
# API Configuration
API_KEY = "9620b5a904bfe764ace4bc327e9fa629"
BASE_URL = "https://v3.football.api-sports.io"

# Analysis Parameters
MIN_MATCHES_REQUIRED = 4
COMBINED_THRESHOLD = 1.5
SCAN_HOURS_AHEAD = 24
REQUEST_DELAY = 1.5  # seconds between API calls

# Output Settings
OUTPUT_DIRECTORY = "betting_alerts"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
```

## 🧪 **Testing**

Run the test script to verify everything works:

```bash
cd live_alert_system
python3 test_system.py
```

**Expected output:**
```
🧪 TESTING ENHANCED LIVE BETTING ALERT SYSTEM
============================================================

1️⃣ Testing Progress Tracker...
✅ Completed: Test Operation

2️⃣ Testing Specific Alert Generator...
✅ League alert generated: betting_alerts/league_Test_League_2025-09-23.txt
✅ Team alert generated: betting_alerts/team_Test_Team_A_2025-09-23.txt

3️⃣ Testing File Operations...
✅ League file exists: betting_alerts/league_Test_League_2025-09-23.txt
✅ Team file exists: betting_alerts/team_Test_Team_A_2025-09-23.txt

4️⃣ Testing Configuration...
✅ API Key configured: 9620b5a904...
✅ Base URL: https://v3.football.api-sports.io
✅ Min matches required: 4
✅ Combined threshold: 1.5

🎉 ALL TESTS COMPLETED SUCCESSFULLY!
```

## 🔧 **Dependencies**

- `httpx` - Async HTTP client
- `pandas` - Data manipulation
- `asyncio` - Async programming
- `time` - Progress tracking
- `subprocess` - File opening
- `platform` - Cross-platform compatibility

## 📋 **Requirements**

- Python 3.7+
- Valid API-Football key
- Internet connection
- 1-2 GB free disk space (for caching)

## 🎯 **Betting Strategy**

- **Target**: First Half Over 0.5 Goals
- **Method**: Lay betting (betting against Under 0.5)
- **Formula**: `(home_team_home_avg + away_team_away_avg) / 2`
- **Alert**: When combined average ≥ 1.5
- **Minimum data**: 4 matches per team

## ⚠️ **Disclaimer**

This is an automated analysis tool. Always do your own research and never bet more than you can afford to lose. Past performance does not guarantee future results.

## 🚀 **Ready to Use!**

The enhanced system is now ready with:
- ✅ Real-time progress tracking
- ✅ Targeted search capabilities
- ✅ Auto-file opening
- ✅ Focused output formats
- ✅ Comprehensive error handling
- ✅ Cross-platform compatibility

**Choose your preferred method:**
- **Full scan**: `python3 start_betting_alerts.py`
- **Targeted search**: `python3 search_specific.py`
