# Peru Segunda División - Season Information

## 🏆 League Details
- **League ID**: 282
- **Full Name**: Segunda División
- **Country**: Peru 🇵🇪
- **Also Known As**: Liga 2

## 📅 Season Structure
Peru's football season typically follows a different calendar than European leagues:

### Typical Season Calendar:
- **Start**: Usually February/March
- **End**: Usually November/December
- **Format**: Often follows calendar year (e.g., 2024 season runs Jan-Dec 2024)

### What We Need to Check:
1. **Available Seasons**: What years have data in API-Football
2. **Current Season**: Which year is the "current" active season
3. **Season Dates**: When does the current season start/end
4. **Data Coverage**: How many fixtures have halftime data

## 🔍 What the API Can Tell Us:

### Without API Key:
- We can't access the actual data
- We can't see available seasons
- We can't check fixture counts

### With API Key:
1. **League Info**: Available seasons list
2. **Season-by-Season Check**: 
   - How many fixtures per season
   - How many have halftime data
   - Date ranges of matches
3. **Current Season Identification**: Which season is most recent/active

## 🎯 Next Steps:

### Option 1: Get API Key
1. Sign up at https://rapidapi.com/api-sports/api/api-football
2. Get free API key (usually 100 requests/day free)
3. Run `check_peru_segunda_seasons.py` to see available seasons
4. Then run the main extraction script

### Option 2: Manual Season Selection
If you know the correct season year, we can modify the script to target that specific season.

## 📊 Expected Data Structure:
Once we identify the correct season, we'll get:
```json
{
  "fixture_id": 12345,
  "league_name": "Peru Segunda División",
  "season": 2024,  // Actual season year
  "match_date": "2024-03-15T20:00:00+00:00",
  "home_team_name": "Team A",
  "away_team_name": "Team B",
  "home_ht_score": 1,
  "away_ht_score": 0,
  "total_ht_goals": 1,
  "match_status": "FT"
}
```

## ❓ Questions to Resolve:
1. What is the actual current season year for Peru Segunda División?
2. When did the current season start?
3. How many fixtures have been played so far?
4. What percentage have halftime data available?

**Answer**: We need API access to determine the correct season and available data.
