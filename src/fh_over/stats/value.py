"""Value detection and edge calculation."""

from typing import Optional, Tuple, List
from dataclasses import dataclass

from .project import ProjectionResult


@dataclass
class ValueResult:
    """Result of value analysis."""
    fair_odds: float
    market_odds: Optional[float]
    edge_pct: Optional[float]
    odds_provider: Optional[str]
    value_signal: bool
    reasons: List[str]


def calculate_edge_percentage(fair_odds: float, market_odds: float) -> float:
    """Calculate edge percentage."""
    if fair_odds <= 0 or market_odds <= 0:
        return 0.0
    
    return (market_odds / fair_odds - 1.0) * 100.0


def detect_value(
    projection: ProjectionResult,
    market_odds: Optional[float] = None,
    odds_provider: Optional[str] = None,
    min_edge_pct: float = 3.0
) -> ValueResult:
    """Detect value in a betting opportunity."""
    
    fair_odds = 1.0 / projection.p_hat if projection.p_hat > 0 else 1.0
    reasons = []
    
    # Calculate edge if market odds available
    edge_pct = None
    if market_odds and market_odds > 0:
        edge_pct = calculate_edge_percentage(fair_odds, market_odds)
    
    # Check value conditions
    value_signal = False
    
    if market_odds is None:
        reasons.append("No market odds available")
    elif edge_pct is None:
        reasons.append("Invalid market odds")
    elif edge_pct < min_edge_pct:
        reasons.append(f"Edge too low: {edge_pct:.2f}% < {min_edge_pct}%")
    else:
        value_signal = True
        reasons.append(f"Value detected: {edge_pct:.2f}% edge")
    
    return ValueResult(
        fair_odds=fair_odds,
        market_odds=market_odds,
        edge_pct=edge_pct,
        odds_provider=odds_provider,
        value_signal=value_signal,
        reasons=reasons
    )


def get_best_odds(odds_quotes: List[dict]) -> Optional[Tuple[float, str]]:
    """Get best available odds from multiple quotes."""
    
    if not odds_quotes:
        return None
    
    best_odds = 0.0
    best_provider = None
    
    for quote in odds_quotes:
        odds = quote.get("back_odds") or quote.get("lay_odds")
        if odds and odds > best_odds:
            best_odds = odds
            best_provider = quote.get("provider", "unknown")
    
    if best_odds > 0:
        return best_odds, best_provider
    
    return None


def validate_value_conditions(
    projection: ProjectionResult,
    value_result: ValueResult,
    lambda_threshold: float = 1.5,
    min_samples_home: int = 8,
    min_samples_away: int = 8,
    min_edge_pct: float = 3.0,
    max_prob_ci_width: float = 0.20
) -> Tuple[bool, List[str]]:
    """Validate all conditions for a value bet."""
    
    reasons = []
    
    # Lambda threshold
    if projection.lambda_hat < lambda_threshold:
        reasons.append(f"Lambda threshold not met: {projection.lambda_hat:.3f} < {lambda_threshold}")
    
    # Sample size thresholds (would need to be passed in)
    # This is handled in the calling code
    
    # Edge threshold
    if value_result.edge_pct is None:
        reasons.append("No edge calculation available")
    elif value_result.edge_pct < min_edge_pct:
        reasons.append(f"Edge threshold not met: {value_result.edge_pct:.2f}% < {min_edge_pct}%")
    
    # CI width threshold
    if projection.prob_ci_width > max_prob_ci_width:
        reasons.append(f"CI width too wide: {projection.prob_ci_width:.3f} > {max_prob_ci_width}")
    
    # Market odds available
    if value_result.market_odds is None:
        reasons.append("No market odds available")
    
    valid = len(reasons) == 0
    return valid, reasons


def get_value_summary(value_result: ValueResult) -> dict:
    """Get summary of value analysis."""
    
    return {
        "fair_odds": value_result.fair_odds,
        "market_odds": value_result.market_odds,
        "edge_pct": value_result.edge_pct,
        "odds_provider": value_result.odds_provider,
        "value_signal": value_result.value_signal,
        "reasons": value_result.reasons
    }
