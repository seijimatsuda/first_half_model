"""Sample collection and management for first-half goal analysis."""

from datetime import datetime
from typing import List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

from fh_over.vendors.base import FirstHalfSample


@dataclass
class TeamSamples:
    """Container for team first-half goal samples."""
    team_id: str
    scope: str  # "home" or "away"
    samples: List[float]
    match_dates: List[datetime]
    season: str
    n_samples: int
    
    def __post_init__(self):
        self.n_samples = len(self.samples)


def build_team_samples(
    samples: List[FirstHalfSample],
    team_id: str,
    scope: str,
    season: Optional[str] = None,
    date_range: Optional[Tuple[datetime, datetime]] = None
) -> TeamSamples:
    """Build team samples from FirstHalfSample list."""
    
    # Filter samples by team, scope, season, and date range
    filtered_samples = []
    for sample in samples:
        if sample.team_id != team_id:
            continue
        if sample.scope != scope:
            continue
        if season and sample.season != season:
            continue
        if date_range:
            start_date, end_date = date_range
            if not (start_date <= sample.match_date <= end_date):
                continue
        
        filtered_samples.append(sample)
    
    # Sort by match date
    filtered_samples.sort(key=lambda x: x.match_date)
    
    # Extract data
    goal_samples = [float(sample.first_half_goals) for sample in filtered_samples]
    match_dates = [sample.match_date for sample in filtered_samples]
    season_name = season or (filtered_samples[0].season if filtered_samples else "unknown")
    
    return TeamSamples(
        team_id=team_id,
        scope=scope,
        samples=goal_samples,
        match_dates=match_dates,
        season=season_name,
        n_samples=len(goal_samples)
    )


def get_home_away_samples(
    all_samples: List[FirstHalfSample],
    home_team_id: str,
    away_team_id: str,
    season: Optional[str] = None,
    date_range: Optional[Tuple[datetime, datetime]] = None
) -> Tuple[TeamSamples, TeamSamples]:
    """Get home and away samples for a fixture."""
    
    home_samples = build_team_samples(
        all_samples, home_team_id, "home", season, date_range
    )
    away_samples = build_team_samples(
        all_samples, away_team_id, "away", season, date_range
    )
    
    return home_samples, away_samples


def validate_samples(
    home_samples: TeamSamples,
    away_samples: TeamSamples,
    min_samples_home: int = 8,
    min_samples_away: int = 8
) -> Tuple[bool, List[str]]:
    """Validate that samples meet minimum requirements."""
    
    reasons = []
    
    if home_samples.n_samples < min_samples_home:
        reasons.append(f"Insufficient home samples: {home_samples.n_samples} < {min_samples_home}")
    
    if away_samples.n_samples < min_samples_away:
        reasons.append(f"Insufficient away samples: {away_samples.n_samples} < {min_samples_away}")
    
    if home_samples.n_samples == 0:
        reasons.append("No home samples available")
    
    if away_samples.n_samples == 0:
        reasons.append("No away samples available")
    
    valid = len(reasons) == 0
    return valid, reasons


def get_sample_statistics(samples: TeamSamples) -> dict:
    """Calculate basic statistics for a team's samples."""
    
    if not samples.samples:
        return {
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "median": 0.0,
            "n_samples": 0
        }
    
    samples_array = np.array(samples.samples)
    
    return {
        "mean": float(np.mean(samples_array)),
        "std": float(np.std(samples_array, ddof=1)),
        "min": float(np.min(samples_array)),
        "max": float(np.max(samples_array)),
        "median": float(np.median(samples_array)),
        "n_samples": len(samples_array)
    }


def filter_recent_samples(
    samples: TeamSamples,
    days_back: int = 30
) -> TeamSamples:
    """Filter samples to only include recent matches."""
    
    if not samples.samples:
        return samples
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    filtered_samples = []
    filtered_dates = []
    
    for sample, date in zip(samples.samples, samples.match_dates):
        if date >= cutoff_date:
            filtered_samples.append(sample)
            filtered_dates.append(date)
    
    return TeamSamples(
        team_id=samples.team_id,
        scope=samples.scope,
        samples=filtered_samples,
        match_dates=filtered_dates,
        season=samples.season,
        n_samples=len(filtered_samples)
    )
