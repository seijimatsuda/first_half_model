"""SQLModel database models for the First-Half Over scanner."""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship


class Team(SQLModel, table=True):
    """Team model for storing team information."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    provider_id: str = Field(index=True, description="ID from data provider")
    provider_name: str = Field(description="Name of the data provider")
    name: str = Field(description="Team name")
    country: Optional[str] = Field(default=None)
    league_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships (commented out to avoid SQLModel issues)
    # home_fixtures: List["Fixture"] = Relationship(back_populates="home_team")
    # away_fixtures: List["Fixture"] = Relationship(back_populates="away_team")
    # home_samples: List["SplitSample"] = Relationship(back_populates="team")
    # away_samples: List["SplitSample"] = Relationship(back_populates="team")


class Fixture(SQLModel, table=True):
    """Fixture model for storing match information."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    provider_id: str = Field(index=True, description="ID from data provider")
    provider_name: str = Field(description="Name of the data provider")
    home_team_id: int = Field(foreign_key="team.id")
    away_team_id: int = Field(foreign_key="team.id")
    league_id: str = Field(index=True)
    league_name: str = Field()
    match_date: datetime = Field(index=True)
    season: Optional[str] = Field(default=None)
    status: str = Field(default="scheduled")  # scheduled, live, finished, cancelled
    home_score: Optional[int] = Field(default=None)
    away_score: Optional[int] = Field(default=None)
    home_first_half_score: Optional[int] = Field(default=None)
    away_first_half_score: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships (commented out to avoid SQLModel issues)
    # home_team: Optional[Team] = Relationship(back_populates="home_fixtures")
    # away_team: Optional[Team] = Relationship(back_populates="away_fixtures")
    # odds_quotes: List["OddsQuote"] = Relationship(back_populates="fixture")
    # results: List["Result"] = Relationship(back_populates="fixture")


class SplitSample(SQLModel, table=True):
    """Model for storing first-half goal samples for teams."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    fixture_id: int = Field(foreign_key="fixture.id", index=True)
    scope: str = Field(description="home or away")
    first_half_goals: int = Field(description="Total first-half goals (home + away)")
    match_date: datetime = Field(index=True)
    season: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships (commented out to avoid SQLModel issues)
    # team: Optional[Team] = Relationship(back_populates="home_samples")
    # fixture: Optional[Fixture] = Relationship()


class OddsQuote(SQLModel, table=True):
    """Model for storing odds quotes."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    fixture_id: int = Field(foreign_key="fixture.id", index=True)
    provider: str = Field(description="odds provider name")
    market: str = Field(description="market type (e.g., '1H_Over_0.5')")
    selection: str = Field(description="selection (e.g., 'Over 0.5')")
    back_odds: Optional[Decimal] = Field(default=None, description="Back odds")
    lay_odds: Optional[Decimal] = Field(default=None, description="Lay odds")
    back_size: Optional[Decimal] = Field(default=None, description="Available back size")
    lay_size: Optional[Decimal] = Field(default=None, description="Available lay size")
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships (commented out to avoid SQLModel issues)
    # fixture: Optional[Fixture] = Relationship(back_populates="odds_quotes")


class Result(SQLModel, table=True):
    """Model for storing scan results and value bets."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    fixture_id: int = Field(foreign_key="fixture.id", index=True)
    scan_date: datetime = Field(index=True)
    
    # Statistical projections
    lambda_hat: float = Field(description="Projected first-half goals")
    p_hat: float = Field(description="Probability of Over 0.5")
    p_ci_low: float = Field(description="Lower confidence interval")
    p_ci_high: float = Field(description="Upper confidence interval")
    prob_ci_width: float = Field(description="Width of probability CI")
    
    # Sample information
    n_home: int = Field(description="Number of home samples")
    n_away: int = Field(description="Number of away samples")
    home_samples_json: str = Field(description="Home team first-half goal samples (JSON)")
    away_samples_json: str = Field(description="Away team first-half goal samples (JSON)")
    
    # Odds and value
    fair_odds: float = Field(description="Fair odds (1/p_hat)")
    market_odds: Optional[float] = Field(default=None, description="Best market odds")
    edge_pct: Optional[float] = Field(default=None, description="Edge percentage")
    odds_provider: Optional[str] = Field(default=None, description="Source of market odds")
    
    # Staking
    stake_mode: str = Field(description="dynamic or flat")
    stake_amount: float = Field(description="Recommended stake amount")
    stake_fraction: float = Field(description="Stake as fraction of bankroll")
    
    # Decision gates
    lambda_threshold_met: bool = Field(description="Lambda threshold passed")
    min_samples_met: bool = Field(description="Minimum samples threshold passed")
    edge_threshold_met: bool = Field(description="Edge threshold passed")
    ci_width_threshold_met: bool = Field(description="CI width threshold passed")
    
    # Overall signal
    signal: bool = Field(description="Overall value signal")
    reasons_json: str = Field(description="Reasons for signal/no signal (JSON)")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships (commented out to avoid SQLModel issues)
    # fixture: Optional[Fixture] = Relationship(back_populates="results")


class League(SQLModel, table=True):
    """Model for storing league information."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    provider_id: str = Field(index=True, description="ID from data provider")
    provider_name: str = Field(description="Name of the data provider")
    name: str = Field(description="League name")
    country: Optional[str] = Field(default=None)
    season: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
