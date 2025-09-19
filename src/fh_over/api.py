"""FastAPI service for the First-Half Over scanner."""

from datetime import datetime, date
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fh_over.service.scan import ScannerService, ScanResult
from fh_over.db import get_session
from fh_over.models import Fixture
from sqlmodel import Session, select


# Pydantic models for API responses
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str


class ScanResponse(BaseModel):
    fixture_id: str
    league_name: str
    home_team: str
    away_team: str
    match_date: datetime
    lambda_hat: float
    p_hat: float
    p_ci_low: float
    p_ci_high: float
    prob_ci_width: float
    n_home: int
    n_away: int
    fair_odds: float
    market_odds: Optional[float]
    edge_pct: Optional[float]
    odds_provider: Optional[str]
    stake_mode: str
    stake_amount: float
    stake_fraction: float
    lambda_threshold_met: bool
    min_samples_met: bool
    edge_threshold_met: bool
    ci_width_threshold_met: bool
    signal: bool
    reasons: List[str]


class FixtureResponse(BaseModel):
    fixture_id: str
    league_name: str
    home_team: str
    away_team: str
    match_date: datetime
    status: str
    home_score: Optional[int]
    away_score: Optional[int]
    home_first_half_score: Optional[int]
    away_first_half_score: Optional[int]


# Initialize FastAPI app
app = FastAPI(
    title="First-Half Over 0.5 Scanner",
    description="Production-grade value betting scanner for first-half over 0.5 goals",
    version="0.1.0"
)

# Initialize scanner service
scanner = ScannerService()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="0.1.0"
    )


@app.get("/scan/today", response_model=List[ScanResponse])
async def scan_today():
    """Scan all fixtures for today."""
    try:
        results = await scanner.scan_today()
        return [ScanResponse(**result.__dict__) for result in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning today's fixtures: {str(e)}")


@app.get("/scan/date/{scan_date}", response_model=List[ScanResponse])
async def scan_date(scan_date: date):
    """Scan fixtures for a specific date."""
    try:
        start_date = datetime.combine(scan_date, datetime.min.time())
        end_date = datetime.combine(scan_date, datetime.max.time())
        
        results = await scanner.scan_date_range(start_date, end_date)
        return [ScanResponse(**result.__dict__) for result in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning fixtures for {scan_date}: {str(e)}")


@app.get("/fixtures/{fixture_id}", response_model=FixtureResponse)
async def get_fixture(fixture_id: str, session: Session = Depends(get_session)):
    """Get detailed fixture information."""
    try:
        # Query database for fixture
        statement = select(Fixture).where(Fixture.id == int(fixture_id))
        fixture = session.exec(statement).first()
        
        if not fixture:
            raise HTTPException(status_code=404, detail="Fixture not found")
        
        return FixtureResponse(
            fixture_id=str(fixture.id),
            league_name=fixture.league_name,
            home_team=fixture.home_team.name if fixture.home_team else "Unknown",
            away_team=fixture.away_team.name if fixture.away_team else "Unknown",
            match_date=fixture.match_date,
            status=fixture.status,
            home_score=fixture.home_score,
            away_score=fixture.away_score,
            home_first_half_score=fixture.home_first_half_score,
            away_first_half_score=fixture.away_first_half_score
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid fixture ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching fixture: {str(e)}")


@app.get("/fixtures/{fixture_id}/scan", response_model=ScanResponse)
async def scan_fixture(fixture_id: str, session: Session = Depends(get_session)):
    """Scan a specific fixture for value."""
    try:
        # Query database for fixture
        statement = select(Fixture).where(Fixture.id == int(fixture_id))
        fixture = session.exec(statement).first()
        
        if not fixture:
            raise HTTPException(status_code=404, detail="Fixture not found")
        
        result = await scanner.scan_fixture(fixture)
        if not result:
            raise HTTPException(status_code=404, detail="No scan result available")
        
        return ScanResponse(**result.__dict__)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid fixture ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning fixture: {str(e)}")


@app.get("/leagues", response_model=List[str])
async def list_leagues():
    """List all available leagues."""
    try:
        # This would typically query the database for leagues
        # For now, return a placeholder
        return ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing leagues: {str(e)}")


@app.get("/stats/summary")
async def get_stats_summary():
    """Get summary statistics."""
    try:
        # This would typically calculate stats from the database
        # For now, return placeholder data
        return {
            "total_fixtures_scanned": 0,
            "value_signals_found": 0,
            "signal_rate": 0.0,
            "average_lambda": 0.0,
            "average_edge": 0.0,
            "total_stake_recommended": 0.0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats summary: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
