
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
from fh_over.service.scan import ScannerService
from fh_over.service.export import export_to_csv, export_to_json

class MultiLeagueScanner:
    """Scanner that can handle all available leagues."""
    
    def __init__(self):
        self.scanner = ScannerService()
        self.results_by_league = {}
    
    async def scan_all_leagues(self, league_ids: List[int], days_ahead: int = 7) -> Dict[str, List]:
        """Scan all specified leagues for upcoming fixtures."""
        
        print(f"🚀 Starting multi-league scan for {len(league_ids)} leagues...")
        
        # Fetch all fixtures
        all_fixtures = await fetch_all_league_fixtures(league_ids, days_ahead)
        
        if not all_fixtures:
            print("❌ No fixtures found")
            return {}
        
        # Group by league
        fixtures_by_league = {}
        for fixture in all_fixtures:
            league_name = fixture['league_name']
            if league_name not in fixtures_by_league:
                fixtures_by_league[league_name] = []
            fixtures_by_league[league_name].append(fixture)
        
        # Scan each league
        for league_name, fixtures in fixtures_by_league.items():
            print(f"\n📊 Scanning {league_name} ({len(fixtures)} fixtures)...")
            
            league_results = []
            for fixture in fixtures:
                # Convert to internal format and scan
                # This would need to be adapted to work with the existing scanner
                result = await self._scan_fixture(fixture)
                if result:
                    league_results.append(result)
            
            self.results_by_league[league_name] = league_results
            print(f"   ✅ Found {len(league_results)} value signals")
        
        return self.results_by_league
    
    async def _scan_fixture(self, fixture_data: Dict) -> Dict:
        """Scan a single fixture for value."""
        # This would implement the same logic as the existing scanner
        # but work with the API-Football data format
        pass
    
    def export_results(self, output_dir: str = "multi_league_results"):
        """Export results for all leagues."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for league_name, results in self.results_by_league.items():
            if results:
                # Clean league name for filename
                clean_name = league_name.replace(" ", "_").replace("/", "_")
                
                # Export CSV
                csv_file = f"{output_dir}/{clean_name}_projections.csv"
                export_to_csv(results, csv_file)
                
                # Export JSON
                json_file = f"{output_dir}/{clean_name}_projections.json"
                export_to_json(results, json_file)
                
                print(f"✅ Exported {league_name} results to {output_dir}/")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all leagues."""
        summary = {
            'total_leagues': len(self.results_by_league),
            'total_fixtures': sum(len(results) for results in self.results_by_league.values()),
            'total_signals': sum(len([r for r in results if r.get('signal', False)]) 
                               for results in self.results_by_league.values()),
            'leagues': {}
        }
        
        for league_name, results in self.results_by_league.items():
            signals = [r for r in results if r.get('signal', False)]
            summary['leagues'][league_name] = {
                'total_fixtures': len(results),
                'signals': len(signals),
                'signal_rate': len(signals) / len(results) if results else 0
            }
        
        return summary

# Usage example
async def main():
    # Get top leagues from our previous analysis
    top_leagues = [
        39,   # Premier League
        40,   # Championship
        41,   # League One
        42,   # League Two
        140,  # La Liga
        141,  # Segunda División
        78,   # Bundesliga
        79,   # 2. Bundesliga
        135,  # Serie A
        136,  # Serie B
        179,  # Scottish Premiership
        180,  # Scottish Championship
    ]
    
    scanner = MultiLeagueScanner()
    results = await scanner.scan_all_leagues(top_leagues, days_ahead=7)
    
    # Export results
    scanner.export_results()
    
    # Print summary
    summary = scanner.get_summary()
    print(f"\n📈 SUMMARY")
    print(f"   Total Leagues: {summary['total_leagues']}")
    print(f"   Total Fixtures: {summary['total_fixtures']}")
    print(f"   Total Signals: {summary['total_signals']}")
    
    for league, stats in summary['leagues'].items():
        print(f"   {league}: {stats['signals']}/{stats['total_fixtures']} signals ({stats['signal_rate']:.1%})")

if __name__ == "__main__":
    asyncio.run(main())
