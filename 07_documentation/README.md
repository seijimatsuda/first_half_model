# First Half Over 0.5 Goals Betting Model

A production-grade Python project that scans soccer leagues for **First-Half Over 0.5** value bets using season-to-date first-half goal environments and live odds.

## 🎯 Overview

This system analyzes historical first-half goal data to identify value betting opportunities in the "Over 0.5 Goals in First Half" market. It uses a lay betting strategy against "Under 0.5 Goals" with real Betfair odds integration.

## 🏗️ Architecture

### Core Components
- **Data Providers**: API-Football, Sportradar, Opta, SportMonks
- **Odds Providers**: Betfair, TheOddsAPI
- **Statistical Engine**: Bootstrap sampling, Poisson projections, confidence intervals
- **Betting Logic**: Lay betting strategy with risk management
- **Backtesting**: Historical performance analysis

### Project Structure
```
src/fh_over/
├── __init__.py
├── config.py              # Configuration management
├── db.py                  # Database engine
├── models.py              # SQLModel data models
├── api.py                 # FastAPI endpoints
├── cli.py                 # Command-line interface
├── data_loader.py         # Excel data loading
├── backtest.py            # Backtesting engine
├── realistic_backtest.py  # Chronological backtesting
├── weekly_backtest.py     # Week-by-week analysis
├── betfair_parser.py      # Betfair historical data parser
├── odds_integration.py    # Odds provider integration
├── premier_league_loader.py # Premier League data loader
├── service/
│   ├── scan.py            # Value detection service
│   ├── export.py          # CSV/JSON export
│   └── data_sync.py       # Data synchronization
├── stats/
│   ├── samples.py         # Sample building
│   ├── project.py         # Statistical projections
│   └── value.py           # Value calculation
├── staking/
│   └── bankroll.py        # Staking strategies
└── vendors/
    ├── base.py            # Adapter interfaces
    ├── api_football.py    # API-Football integration
    ├── sportradar.py      # Sportradar integration
    ├── opta.py            # Opta integration
    ├── sportmonks.py      # SportMonks integration
    ├── theoddsapi.py      # TheOddsAPI integration
    ├── betfair.py         # Betfair integration
    └── flashscore.py      # FlashScore scraper
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- API keys for data providers (API-Football, Betfair, etc.)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/seijimatsuda/first_half_model.git
cd first_half_model
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Initialize the database**
```bash
python -m fh_over.cli init
```

### Configuration

The system uses a YAML-based configuration system. Key settings:

```yaml
providers:
  api_football_enabled: true
  betfair_enabled: true
  
scanner:
  min_edge_pct: 0.0
  max_prob_ci_width: 1.0
  min_samples_home: 1
  min_samples_away: 1
  
staking:
  mode: "flat"
  flat_size: 100.0
```

## 📊 Usage

### Command Line Interface

```bash
# Initialize database
python -m fh_over.cli init

# Load Premier League data
python -m fh_over.cli load-excel --premier-league data/ENP_2024-2025_M.xlsx

# Run backtest
python -m fh_over.cli weekly-backtest

# Sync live data
python -m fh_over.cli sync-data

# Scan for today's value bets
python -m fh_over.cli scan

# Run odds analysis
python -m fh_over.cli odds-analysis
```

### API Endpoints

```bash
# Start the API server
python -m fh_over.cli serve

# Available endpoints:
GET /health                    # Health check
GET /scan/today               # Scan today's matches
GET /fixtures/{fixture_id}    # Get fixture details
GET /leagues                  # List available leagues
GET /stats/summary            # Performance summary
```

## 🎲 Betting Strategy

### Algorithm
1. **Data Collection**: Gather first-half goal samples for home/away teams
2. **Statistical Analysis**: Calculate team averages using season-to-date data
3. **Projection**: Use combined home/away averages to predict first-half goals
4. **Value Detection**: Identify bets where model probability > market probability
5. **Risk Management**: Filter out high-odds bets (>5.0) for risk control

### Lay Betting Logic
- **Strategy**: Lay (bet against) "Under 0.5 Goals in First Half"
- **Stake**: $100 flat stake per bet
- **Commission**: 2% on winning bets
- **Profit**: +$98 if goal scored before half-time
- **Loss**: -$100 × (Under Odds - 1) if 0-0 at half-time

## 📈 Performance Results

### 2024-25 Premier League Season
- **Total Bets**: 95 (filtered for odds ≤ 5.0)
- **Win Rate**: 78.9%
- **Total Profit**: $1,205
- **ROI**: 12.7%

### Monthly Breakdown
| Month | Bets | Win Rate | P&L | Cumulative |
|-------|------|----------|-----|------------|
| Sep 2024 | 6 | 100.0% | +$588 | +$588 |
| Oct 2024 | 14 | 78.6% | +$73 | +$661 |
| Nov 2024 | 12 | 66.7% | -$221 | +$440 |
| Dec 2024 | 15 | 80.0% | +$136 | +$576 |
| Jan 2025 | 9 | 77.8% | +$41 | +$617 |
| Feb 2025 | 9 | 88.9% | +$444 | +$1,061 |
| Mar 2025 | 7 | 57.1% | -$533 | +$528 |
| Apr 2025 | 13 | 69.2% | -$303 | +$225 |
| May 2025 | 10 | 100.0% | +$980 | +$1,205 |

## 🔧 Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Format code
black src/
isort src/

# Type checking
mypy src/
```

### Database Schema
The system uses SQLModel with SQLite (production-ready for PostgreSQL):

- **League**: Competition information
- **Team**: Team details and statistics
- **Fixture**: Match information and scheduling
- **SplitSample**: First-half goal samples
- **OddsQuote**: Market odds data
- **Result**: Betting outcomes and P&L

## 📝 Data Sources

### Primary Data Providers
- **API-Football**: Live fixtures and statistics
- **Betfair**: Exchange odds and historical data
- **Sportradar**: Professional sports data (enterprise)

### Fallback Providers
- **Opta/Stats Perform**: Enterprise data
- **SportMonks**: Alternative statistics
- **TheOddsAPI**: Bookmaker odds
- **FlashScore**: Web scraping fallback

## ⚠️ Risk Disclaimer

This software is for educational and research purposes only. Sports betting involves significant financial risk. Past performance does not guarantee future results. Always bet responsibly and within your means.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For questions or support, please open an issue on GitHub or contact the maintainers.

---

**Built with ❤️ for the sports betting community**