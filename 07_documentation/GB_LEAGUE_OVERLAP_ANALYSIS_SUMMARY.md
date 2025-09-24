# GB League Overlap Analysis Summary

## Overview
This analysis examined the overlap between the GB_24_25.tar dataset (Betfair historical odds data) and the leagues analyzed in the comprehensive first-half goal model backtest.

## Key Findings

### 1. League Overlap
- **Total leagues analyzed**: 1,193 leagues worldwide
- **Leagues with bets**: 404 leagues
- **Overlapping leagues found**: 18 leagues
- **Matches with actual odds data**: 2,699 matches in GB dataset
- **Successfully matched predictions**: 17 bets

### 2. Overlapping Leagues
The following leagues appeared in both datasets:

#### Premier League (England)
- **Bets placed**: 20
- **Accuracy**: 70.0%
- **Original PnL**: $1,243.00
- **Original ROI**: 62.2%

#### League Two (England)  
- **Bets placed**: 4
- **Accuracy**: 100.0%
- **Original PnL**: $392.00
- **Original ROI**: 98.0%

#### Other Premier Leagues (Various Countries)
- Ukraine, Wales, Jamaica, Kuwait, Hong Kong, Lebanon, Belarus, Kazakhstan, Russia, Singapore, Malta, Bahrain, Bangladesh, Syria, China
- **Total bets**: 167
- **Combined PnL**: $10,741.00
- **Average ROI**: 61.0%

### 3. Actual Odds vs Predicted Performance

#### Overall Results with Actual Betfair Odds:
- **Total matched bets**: 17
- **Accuracy**: 70.6%
- **Original PnL**: $1,084.00 (63.8% ROI)
- **Actual PnL**: -$12,895.25 (-758.5% ROI)

#### Breakdown by League:
- **Premier League**: 14 bets, 64.3% accuracy
  - Original ROI: 56.4%
  - Actual ROI: -931.2%
  
- **League Two**: 3 bets, 100.0% accuracy
  - Original ROI: 98.0%
  - Actual ROI: 47.4%

### 4. Key Insights

#### Why Actual ROI is Much Lower:
1. **Market Efficiency**: Betfair odds are much more efficient than the theoretical odds used in the original analysis
2. **Lay Betting Complexity**: The actual lay betting mechanics with real odds show significant variance
3. **Commission Impact**: 2% commission on all winning bets significantly impacts profitability
4. **Odds Movement**: Real odds fluctuate during matches, affecting final outcomes

#### Sample Match Results:
- **Ipswich vs Liverpool**: Predicted loss (-31.0), Actual loss (-3,302.0) at odds 34.00
- **Newcastle vs Southampton**: Predicted win (98.0), Actual win (81.87) at odds 6.20
- **Arsenal vs Wolves**: Predicted win (98.0), Actual win (38.83) at odds 1.69

### 5. Recommendations

#### For Live Betting Implementation:
1. **Focus on League Two**: Shows positive actual ROI (47.4%) with 100% accuracy
2. **Avoid Premier League**: Negative actual ROI (-931.2%) despite good theoretical performance
3. **Consider Odds Thresholds**: Only bet when actual odds provide sufficient margin
4. **Risk Management**: Use smaller stakes due to high variance in actual outcomes

#### Model Improvements Needed:
1. **Odds Integration**: Incorporate real-time odds into the prediction model
2. **Market Efficiency Analysis**: Account for market efficiency in different leagues
3. **Commission Modeling**: Better modeling of exchange commission impact
4. **Dynamic Staking**: Adjust stake sizes based on actual odds and market conditions

### 6. Data Quality Assessment

#### GB Dataset Strengths:
- **Comprehensive Coverage**: 2,699 matches with complete odds data
- **Real Market Data**: Actual Betfair exchange odds
- **High Frequency**: Detailed odds movements throughout matches

#### Limitations:
- **Limited Match Overlap**: Only 17 out of 191 predicted bets had matching odds data
- **League Coverage**: Primarily English leagues (Premier League, League Two)
- **Time Period**: Limited to 2024-2025 season data

### 7. Conclusion

While the theoretical model shows strong performance across 1,193 leagues with 67.2% overall ROI, the actual implementation with real Betfair odds reveals significant challenges:

- **Market efficiency** makes profitable betting much more difficult
- **Commission costs** significantly impact returns
- **Odds variance** creates high-risk scenarios

The analysis suggests that successful implementation would require:
1. Focus on lower-tier leagues where market efficiency is lower
2. Sophisticated odds analysis and timing
3. Careful risk management and position sizing
4. Continuous model refinement based on actual market data

**Final Recommendation**: The model shows promise in League Two but requires significant refinement before live implementation in Premier League or other major leagues.
