"""Command-line interface for the First-Half Over scanner."""

import asyncio
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from fh_over.config import config
from fh_over.db import create_tables, get_session
from fh_over.service.scan import ScannerService
from fh_over.service.export import export_to_csv, export_to_json, export_to_summary
from fh_over.data_loader import load_excel_dataset
from fh_over.premier_league_loader import load_premier_league_dataset
from fh_over.backtest import Backtester, run_backtest
from fh_over.realistic_backtest import RealisticBacktester, run_realistic_backtest
from fh_over.weekly_backtest import WeeklyBacktester, run_weekly_backtest
from fh_over.vendors.sportradar import SportradarAdapter
from fh_over.vendors.sportmonks import SportMonksAdapter
from fh_over.vendors.api_football import ApiFootballAdapter
from fh_over.vendors.flashscore import FlashScoreAdapter
from fh_over.vendors.theoddsapi import TheOddsApiAdapter
from fh_over.vendors.betfair import BetfairAdapter
from fh_over.service.data_sync import DataSyncService, sync_all_data
from fh_over.service.multi_league_sync import MultiLeagueSyncService, sync_all_leagues
from fh_over.odds_integration import OddsIntegrationService

app = typer.Typer(help="First-Half Over 0.5 Value Betting Scanner")
console = Console()


@app.command()
def init():
    """Initialize the database and create tables."""
    console.print("Initializing database...", style="blue")
    
    try:
        create_tables()
        console.print("✅ Database initialized successfully", style="green")
    except Exception as e:
        console.print(f"❌ Error initializing database: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def backfill(
    season: str = typer.Option("2024", help="Season to backfill (e.g., '2024')"),
    days_back: int = typer.Option(30, help="Number of days back to fetch data"),
    provider: Optional[str] = typer.Option(None, help="Specific provider to use")
):
    """Backfill historical data for all leagues."""
    console.print(f"Backfilling data for season {season}...", style="blue")
    
    async def _backfill():
        # Initialize data adapters
        adapters = {}
        
        if not provider or provider == "sportradar":
            if config.sportradar_api_key:
                adapters["sportradar"] = SportradarAdapter(config.sportradar_api_key)
        
        if not provider or provider == "sportmonks":
            if config.sportmonks_key:
                adapters["sportmonks"] = SportMonksAdapter(config.sportmonks_key)
        
        if not provider or provider == "api_football":
            if config.apifootball_key:
                adapters["api_football"] = ApiFootballAdapter(config.apifootball_key)
        
        if not adapters:
            console.print("❌ No data providers configured", style="red")
            return
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for provider_name, adapter in adapters.items():
                task = progress.add_task(f"Fetching data from {provider_name}...", total=None)
                
                try:
                    async with adapter:
                        # Get leagues
                        leagues = await adapter.list_leagues()
                        console.print(f"Found {len(leagues)} leagues from {provider_name}")
                        
                        # Get fixtures
                        fixtures = await adapter.list_fixtures(
                            date_range=(start_date, end_date),
                            season=season
                        )
                        console.print(f"Found {len(fixtures)} fixtures from {provider_name}")
                        
                        # TODO: Store data in database
                        # This would typically involve:
                        # 1. Storing leagues
                        # 2. Storing teams
                        # 3. Storing fixtures
                        # 4. Storing first-half samples
                        
                        progress.update(task, description=f"✅ {provider_name} completed")
                
                except Exception as e:
                    console.print(f"❌ Error with {provider_name}: {e}", style="red")
                    progress.update(task, description=f"❌ {provider_name} failed")
    
    asyncio.run(_backfill())


@app.command()
def scan(
    scan_date: Optional[str] = typer.Option(None, help="Date to scan (YYYY-MM-DD)"),
    export_csv: Optional[str] = typer.Option(None, help="Export results to CSV file"),
    export_json: Optional[str] = typer.Option(None, help="Export results to JSON file"),
    export_summary: Optional[str] = typer.Option(None, help="Export summary to text file"),
    show_all: bool = typer.Option(False, help="Show all fixtures, not just value signals"),
    leagues: Optional[str] = typer.Option(None, help="Comma-separated list of league IDs to scan"),
    all_leagues: bool = typer.Option(False, help="Scan all available leagues"),
    exclude_leagues: Optional[str] = typer.Option(None, help="Comma-separated list of league IDs to exclude"),
    league_types: Optional[str] = typer.Option(None, help="Filter by league types (League,Cup)"),
    countries: Optional[str] = typer.Option(None, help="Comma-separated list of countries to include")
):
    """Scan fixtures for value bets."""
    
    async def _scan():
        scanner = ScannerService()
        
        # Parse league filters
        league_filters = {}
        if leagues:
            league_filters['include_leagues'] = [int(x.strip()) for x in leagues.split(',')]
        if exclude_leagues:
            league_filters['exclude_leagues'] = [int(x.strip()) for x in exclude_leagues.split(',')]
        if league_types:
            league_filters['league_types'] = [x.strip() for x in league_types.split(',')]
        if countries:
            league_filters['countries'] = [x.strip() for x in countries.split(',')]
        if all_leagues:
            league_filters['all_leagues'] = True
        
        if scan_date:
            try:
                scan_dt = datetime.strptime(scan_date, "%Y-%m-%d").date()
                start_date = datetime.combine(scan_dt, datetime.min.time())
                end_date = datetime.combine(scan_dt, datetime.max.time())
                results = await scanner.scan_date_range(start_date, end_date, league_filters=league_filters)
            except ValueError:
                console.print("❌ Invalid date format. Use YYYY-MM-DD", style="red")
                return
        else:
            results = await scanner.scan_today(league_filters=league_filters)
        
        if not results:
            console.print("No fixtures found to scan", style="yellow")
            return
        
        # Filter results if not showing all
        if not show_all:
            results = [r for r in results if r.signal]
        
        if not results:
            console.print("No value signals found", style="yellow")
            return
        
        # Display results in table
        table = Table(title="First-Half Over 0.5 Value Signals")
        table.add_column("Fixture", style="cyan")
        table.add_column("League", style="magenta")
        table.add_column("Date", style="green")
        table.add_column("Lambda", style="blue")
        table.add_column("P(Over 0.5)", style="blue")
        table.add_column("Fair Odds", style="yellow")
        table.add_column("Market Odds", style="yellow")
        table.add_column("Edge %", style="red")
        table.add_column("Stake", style="green")
        table.add_column("Signal", style="bold")
        
        for result in results:
            table.add_row(
                f"{result.home_team} vs {result.away_team}",
                result.league_name,
                result.match_date.strftime("%Y-%m-%d %H:%M"),
                f"{result.lambda_hat:.3f}",
                f"{result.p_hat:.3f}",
                f"{result.fair_odds:.2f}",
                f"{result.market_odds:.2f}" if result.market_odds else "N/A",
                f"{result.edge_pct:.2f}%" if result.edge_pct else "N/A",
                f"${result.stake_amount:.2f}",
                "✅" if result.signal else "❌"
            )
        
        console.print(table)
        
        # Export results if requested
        if export_csv:
            export_to_csv(results, export_csv)
            console.print(f"✅ Results exported to {export_csv}", style="green")
        
        if export_json:
            export_to_json(results, export_json)
            console.print(f"✅ Results exported to {export_json}", style="green")
        
        if export_summary:
            export_to_summary(results, export_summary)
            console.print(f"✅ Summary exported to {export_summary}", style="green")
    
    asyncio.run(_scan())


@app.command()
def markets(
    fixture_id: str = typer.Argument(..., help="Fixture ID to check markets for")
):
    """Show available markets for a fixture."""
    
    async def _markets():
        console.print(f"Checking markets for fixture {fixture_id}...", style="blue")
        
        # Initialize odds adapters
        adapters = {}
        
        if config.theoddsapi_key:
            adapters["theoddsapi"] = TheOddsApiAdapter(config.theoddsapi_key)
        
        if config.betfair_app_key:
            adapters["betfair"] = BetfairAdapter(
                config.betfair_app_key,
                config.betfair_cert or "",
                config.betfair_key or "",
                "username",  # Would need to be configured
                "password"   # Would need to be configured
            )
        
        if not adapters:
            console.print("❌ No odds providers configured", style="red")
            return
        
        for provider_name, adapter in adapters.items():
            try:
                async with adapter:
                    markets = await adapter.get_available_markets(fixture_id)
                    
                    if markets:
                        console.print(f"\n📊 Markets from {provider_name}:", style="bold")
                        for market in markets:
                            console.print(f"  • {market.get('market_name', 'Unknown')}")
                    else:
                        console.print(f"No markets found from {provider_name}")
            
            except Exception as e:
                console.print(f"❌ Error with {provider_name}: {e}", style="red")
    
    asyncio.run(_markets())


@app.command()
def config_show():
    """Show current configuration."""
    console.print("Current Configuration:", style="bold")
    
    # Providers
    console.print("\n📡 Data Providers:", style="blue")
    for provider in config.get_enabled_providers():
        console.print(f"  ✅ {provider}")
    
    console.print("\n💰 Odds Providers:", style="blue")
    for provider in config.get_enabled_odds_providers():
        console.print(f"  ✅ {provider}")
    
    # Thresholds
    console.print("\n🎯 Thresholds:", style="blue")
    console.print(f"  Lambda threshold: {config.thresholds.lambda_threshold}")
    console.print(f"  Min samples (home): {config.thresholds.min_samples_home}")
    console.print(f"  Min samples (away): {config.thresholds.min_samples_away}")
    console.print(f"  Min edge %: {config.thresholds.min_edge_pct}")
    console.print(f"  Max CI width: {config.thresholds.max_prob_ci_width}")
    
    # Staking
    console.print("\n💰 Staking:", style="blue")
    console.print(f"  Mode: {config.staking.mode}")
    console.print(f"  Bankroll: ${config.staking.bankroll}")
    if config.staking.mode == "dynamic":
        console.print(f"  Kelly fraction: {config.staking.kelly_fraction}")
        console.print(f"  Stake cap: {config.staking.stake_cap}")
    else:
        console.print(f"  Flat size: ${config.staking.flat_size}")


@app.command()
def load_excel(
    file_path: str = typer.Argument(..., help="Path to Excel file"),
    inspect_only: bool = typer.Option(False, help="Only inspect data, don't load to database"),
    premier_league: bool = typer.Option(False, help="Use Premier League specific loader")
):
    """Load Excel dataset into the database."""
    console.print(f"Loading Excel dataset from {file_path}...", style="blue")
    
    if inspect_only:
        if premier_league:
            from fh_over.premier_league_loader import PremierLeagueLoader
            loader = PremierLeagueLoader(file_path)
            loader.load_data()
            loader.inspect_data()
        else:
            from fh_over.data_loader import ExcelDataLoader
            loader = ExcelDataLoader(file_path)
            loader.load_data()
            loader.inspect_data()
            mappings = loader.detect_columns()
            console.print(f"\n🔍 Detected column mappings:")
            for field, column in mappings.items():
                console.print(f"  {field}: {column}")
    else:
        if premier_league:
            load_premier_league_dataset(file_path)
        else:
            load_excel_dataset(file_path)


@app.command()
def backtest(
    start_date: Optional[str] = typer.Option(None, help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, help="End date (YYYY-MM-DD)"),
    league: Optional[str] = typer.Option(None, help="League to backtest"),
    export_csv: Optional[str] = typer.Option(None, help="Export results to CSV"),
    min_samples: int = typer.Option(8, help="Minimum samples required"),
    realistic: bool = typer.Option(False, help="Use realistic chronological backtesting")
):
    """Run backtest on historical data."""
    console.print("🚀 Starting backtest...", style="blue")
    
    if realistic:
        # Use realistic backtester
        backtester = RealisticBacktester()
        
        # Parse dates
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                console.print("❌ Invalid start date format. Use YYYY-MM-DD", style="red")
                return
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                console.print("❌ Invalid end date format. Use YYYY-MM-DD", style="red")
                return
        
        # Run realistic backtest
        backtester.run_backtest(
            start_date=start_dt,
            end_date=end_dt,
            league_filter=league,
            min_samples_home=min_samples,
            min_samples_away=min_samples
        )
        
        # Export results if requested
        if export_csv:
            backtester.export_results(export_csv)
            console.print(f"✅ Results exported to {export_csv}", style="green")
    else:
        # Use original backtester
        backtester = Backtester()
        
        # Parse dates
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                console.print("❌ Invalid start date format. Use YYYY-MM-DD", style="red")
                return
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                console.print("❌ Invalid end date format. Use YYYY-MM-DD", style="red")
                return
        
        # Run backtest
        summary = backtester.run_backtest(
            start_date=start_dt,
            end_date=end_dt,
            league_filter=league,
            min_samples_home=min_samples,
            min_samples_away=min_samples
        )
        
        # Export results if requested
        if export_csv:
            backtester.export_results(export_csv)
            console.print(f"✅ Results exported to {export_csv}", style="green")


@app.command()
def weekly_backtest(
    start_week: int = typer.Option(9, help="Starting matchweek"),
    end_week: Optional[int] = typer.Option(None, help="Ending matchweek"),
    league: Optional[str] = typer.Option(None, help="League to backtest"),
    export_csv: Optional[str] = typer.Option(None, help="Export results to CSV"),
    export_weekly: Optional[str] = typer.Option(None, help="Export weekly summary to CSV"),
    min_samples: int = typer.Option(5, help="Minimum samples required")
):
    """Run weekly backtest starting from specified matchweek."""
    console.print(f"🚀 Starting weekly backtest from matchweek {start_week}...", style="blue")
    
    backtester = WeeklyBacktester()
    
    # Run weekly backtest
    backtester.run_weekly_backtest(
        start_week=start_week,
        end_week=end_week,
        league_filter=league,
        min_samples_home=min_samples,
        min_samples_away=min_samples
    )
    
    # Export results if requested
    if export_csv:
        backtester.export_results(export_csv)
        console.print(f"✅ Results exported to {export_csv}", style="green")
    
    if export_weekly:
        backtester.export_weekly_summary(export_weekly)
        console.print(f"✅ Weekly summary exported to {export_weekly}", style="green")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload")
):
    """Start the FastAPI server."""
    import uvicorn
    
    console.print(f"Starting server on {host}:{port}", style="blue")
    uvicorn.run("fh_over.api:app", host=host, port=port, reload=reload)


@app.command()
def sync_data(
    provider: str = typer.Option("api_football", help="Data provider to sync from"),
    days_back: int = typer.Option(30, help="Number of days back to fetch data"),
    leagues_only: bool = typer.Option(False, help="Only sync leagues, not fixtures"),
    fixtures_only: bool = typer.Option(False, help="Only sync fixtures, not leagues")
):
    """Sync data from external providers."""
    console.print(f"🚀 Starting data sync from {provider}...", style="blue")
    
    try:
        if leagues_only:
            sync_service = DataSyncService()
            leagues = asyncio.run(sync_service.sync_leagues(provider))
            console.print(f"✅ Synced {len(leagues)} leagues", style="green")
        elif fixtures_only:
            sync_service = DataSyncService()
            fixtures = asyncio.run(sync_service.sync_fixtures(days_back=days_back, provider_name=provider))
            console.print(f"✅ Synced {len(fixtures)} fixtures", style="green")
        else:
            result = asyncio.run(sync_all_data(provider, days_back))
            console.print(f"✅ Data sync complete: {result}", style="green")
    
    except Exception as e:
        console.print(f"❌ Error syncing data: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def multi_scan(
    days_ahead: int = typer.Option(7, help="Number of days ahead to scan"),
    top_leagues_only: bool = typer.Option(False, help="Scan only top-tier leagues"),
    export_csv: Optional[str] = typer.Option(None, help="Export results to CSV file"),
    export_json: Optional[str] = typer.Option(None, help="Export results to JSON file"),
    show_all: bool = typer.Option(False, help="Show all fixtures, not just value signals")
):
    """Scan multiple leagues for value bets."""
    
    async def _multi_scan():
        console.print("🌍 Starting multi-league scan...", style="blue")
        
        # First sync data for all leagues
        console.print("📊 Syncing league data...", style="blue")
        sync_result = await sync_all_leagues(days_ahead, top_leagues_only)
        
        if not sync_result:
            console.print("❌ Failed to sync league data", style="red")
            return
        
        console.print(f"✅ Synced {sync_result['leagues_synced']} leagues with {sync_result['total_fixtures']} fixtures", style="green")
        
        # Now scan all fixtures
        console.print("🔍 Scanning fixtures for value bets...", style="blue")
        scanner = ScannerService()
        
        # Get date range
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=days_ahead)
        
        # Scan all fixtures
        results = await scanner.scan_date_range(start_date, end_date)
        
        if not results:
            console.print("No fixtures found to scan", style="yellow")
            return
        
        # Filter results if not showing all
        if not show_all:
            results = [r for r in results if r.signal]
        
        if not results:
            console.print("No value signals found", style="yellow")
            return
        
        # Group results by league
        results_by_league = {}
        for result in results:
            league = result.league_name
            if league not in results_by_league:
                results_by_league[league] = []
            results_by_league[league].append(result)
        
        # Display results
        console.print(f"\n📈 Found {len(results)} value signals across {len(results_by_league)} leagues", style="green")
        
        for league_name, league_results in results_by_league.items():
            console.print(f"\n🏆 {league_name} ({len(league_results)} signals)", style="bold")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Fixture", style="cyan")
            table.add_column("Date", style="green")
            table.add_column("Lambda", style="blue")
            table.add_column("P(Over 0.5)", style="blue")
            table.add_column("Fair Odds", style="yellow")
            table.add_column("Market Odds", style="yellow")
            table.add_column("Edge %", style="red")
            table.add_column("Stake", style="green")
            
            for result in league_results[:10]:  # Show top 10 per league
                table.add_row(
                    f"{result.home_team} vs {result.away_team}",
                    result.match_date.strftime("%m-%d %H:%M"),
                    f"{result.lambda_hat:.3f}",
                    f"{result.p_hat:.3f}",
                    f"{result.fair_odds:.2f}",
                    f"{result.market_odds:.2f}" if result.market_odds else "N/A",
                    f"{result.edge_pct:.2f}%" if result.edge_pct else "N/A",
                    f"${result.stake_amount:.2f}"
                )
            
            console.print(table)
            
            if len(league_results) > 10:
                console.print(f"   ... and {len(league_results) - 10} more", style="dim")
        
        # Export results if requested
        if export_csv:
            export_to_csv(results, export_csv)
            console.print(f"✅ Results exported to {export_csv}", style="green")
        
        if export_json:
            export_to_json(results, export_json)
            console.print(f"✅ Results exported to {export_json}", style="green")
    
    asyncio.run(_multi_scan())


@app.command()
def list_leagues(
    provider: str = typer.Option("api_football", help="Data provider to query")
):
    """List available leagues from a provider."""
    console.print(f"🔍 Fetching leagues from {provider}...", style="blue")
    
    try:
        if provider == "api_football":
            async def fetch_leagues():
                async with ApiFootballAdapter(config.providers.api_football_key) as adapter:
                    return await adapter.list_leagues()
            
            leagues = asyncio.run(fetch_leagues())
        elif provider == "flashscore":
            async def fetch_leagues():
                async with FlashScoreAdapter() as adapter:
                    return await adapter.list_leagues()
            
            leagues = asyncio.run(fetch_leagues())
        else:
            console.print(f"❌ Provider {provider} not supported", style="red")
            raise typer.Exit(1)
        
        if not leagues:
            console.print("❌ No leagues found", style="red")
            return
        
        # Display leagues in a table
        table = Table(title=f"Leagues from {provider}")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Country", style="green")
        table.add_column("Season", style="yellow")
        
        for league in leagues[:20]:  # Show first 20
            table.add_row(
                league.provider_id,
                league.name,
                league.country or "N/A",
                league.season or "N/A"
            )
        
        console.print(table)
        console.print(f"✅ Found {len(leagues)} leagues", style="green")
    
    except Exception as e:
        console.print(f"❌ Error fetching leagues: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def test_provider(
    provider: str = typer.Option("api_football", help="Data provider to test"),
    api_key: Optional[str] = typer.Option(None, help="API key to test with")
):
    """Test a data provider connection."""
    console.print(f"🧪 Testing {provider} connection...", style="blue")
    
    try:
        if provider == "api_football":
            key = api_key or config.providers.api_football_key
            if not key:
                console.print("❌ No API key provided for API-Football", style="red")
                raise typer.Exit(1)
            
            async def test_connection():
                async with ApiFootballAdapter(key) as adapter:
                    leagues = await adapter.list_leagues()
                    return len(leagues)
            
            league_count = asyncio.run(test_connection())
            console.print(f"✅ API-Football connection successful! Found {league_count} leagues", style="green")
        
        elif provider == "flashscore":
            async def test_connection():
                async with FlashScoreAdapter() as adapter:
                    leagues = await adapter.list_leagues()
                    return len(leagues)
            
            league_count = asyncio.run(test_connection())
            console.print(f"✅ FlashScore connection successful! Found {league_count} leagues", style="green")
        
        else:
            console.print(f"❌ Provider {provider} not supported", style="red")
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"❌ Connection test failed: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def odds_analysis(
    predictions_file: str = typer.Argument("matchweek5_plus_predictions.csv", help="CSV file with predictions"),
    stake: float = typer.Option(100.0, "--stake", help="Flat stake amount per bet"),
    output_file: str = typer.Option("odds_analysis_results.csv", "--output", help="Output file for detailed results")
):
    """Run comprehensive odds analysis and PnL calculation using real odds only."""
    console.print("[blue]Running comprehensive odds analysis with real odds only...[/blue]")
    
    try:
        import pandas as pd
        
        # Load predictions
        predictions_df = pd.read_csv(predictions_file)
        console.print(f"Loaded {len(predictions_df)} predictions from {predictions_file}")
        
        # Create odds integration service
        service = OddsIntegrationService(config)
        
        # Check if any odds providers are configured
        betfair_configured = config.get_provider_api_key("betfair_app_key") is not None
        theoddsapi_configured = config.get_provider_api_key("theoddsapi_key") is not None
        
        if not betfair_configured and not theoddsapi_configured:
            console.print("[yellow]⚠️  No odds providers configured![/yellow]")
            console.print("Configure Betfair or TheOddsAPI API keys to enable real odds fetching")
            console.print("This system only works with real odds - no mock data will be generated")
            return
        
        console.print("Using real odds from available sources...")
        results = asyncio.run(service.calculate_pnl_with_real_odds(predictions_df, stake))
        
        # Display results
        console.print(f"\n[green]📊 ODDS ANALYSIS RESULTS[/green]")
        console.print("=" * 50)
        console.print(f"Total bets: {results['total_bets']}")
        console.print(f"Total staked: ${results['total_staked']:,.2f}")
        console.print(f"Winning bets: {results['winning_bets']}")
        console.print(f"Losing bets: {results['losing_bets']}")
        console.print(f"Win rate: {results['win_rate']:.1f}%")
        console.print(f"Total winnings: ${results['total_winnings']:,.2f}")
        console.print(f"Net profit: ${results['net_profit']:,.2f}")
        console.print(f"ROI: {results['roi']:.1f}%")
        
        if 'odds_sources_used' in results and results['odds_sources_used']:
            console.print(f"\nOdds sources used:")
            for source, count in results['odds_sources_used'].items():
                console.print(f"  {source}: {count} bets")
        
        if results['total_bets'] == 0:
            console.print(f"\n[yellow]⚠️  No bets processed - no real odds available for the predictions[/yellow]")
        else:
            # Save detailed results
            bet_details_df = pd.DataFrame(results['bet_details'])
            bet_details_df.to_csv(output_file, index=False)
            console.print(f"\n[green]Detailed results saved to: {output_file}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error running odds analysis: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
