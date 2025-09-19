"""Bankroll management and staking strategies."""

from typing import Optional, Tuple, List
from dataclasses import dataclass
import numpy as np

from fh_over.stats.project import ProjectionResult
from fh_over.stats.value import ValueResult


@dataclass
class StakingResult:
    """Result of staking calculation."""
    stake_mode: str
    stake_amount: float
    stake_fraction: float
    kelly_fraction: Optional[float] = None
    confidence_weight: Optional[float] = None
    value_weight: Optional[float] = None


def calculate_kelly_fraction(
    odds: float,
    probability: float,
    kelly_fraction: float = 0.5
) -> float:
    """Calculate Kelly fraction for binary outcome."""
    
    if odds <= 1.0 or probability <= 0 or probability >= 1:
        return 0.0
    
    # Kelly formula: f = (bp - q) / b
    # where b = odds - 1, p = probability, q = 1 - p
    b = odds - 1.0
    p = probability
    q = 1.0 - p
    
    kelly = (b * p - q) / b
    
    # Apply kelly fraction multiplier and ensure non-negative
    return max(0.0, kelly * kelly_fraction)


def calculate_confidence_weight(
    prob_ci_width: float,
    tau_conf: float = 0.20
) -> float:
    """Calculate confidence weight based on CI width."""
    
    if prob_ci_width <= 0:
        return 1.0
    
    # Weight decreases as CI width increases
    weight = max(0.0, 1.0 - (prob_ci_width / tau_conf))
    return weight


def calculate_value_weight(
    edge_pct: float,
    target_edge_pct: float = 5.0
) -> float:
    """Calculate value weight based on edge percentage."""
    
    if edge_pct <= 0:
        return 0.0
    
    # Weight increases with edge, capped at 1.0
    weight = min(1.0, edge_pct / target_edge_pct)
    return weight


def calculate_dynamic_stake(
    projection: ProjectionResult,
    value_result: ValueResult,
    bankroll: float,
    kelly_fraction: float = 0.5,
    tau_conf: float = 0.20,
    target_edge_pct: float = 5.0,
    stake_cap: float = 0.03
) -> StakingResult:
    """Calculate dynamic stake using Kelly criterion with confidence and value weights."""
    
    if not value_result.market_odds or value_result.market_odds <= 0:
        return StakingResult(
            stake_mode="dynamic",
            stake_amount=0.0,
            stake_fraction=0.0
        )
    
    # Calculate Kelly fraction
    kelly = calculate_kelly_fraction(
        value_result.market_odds,
        projection.p_hat,
        kelly_fraction
    )
    
    # Calculate confidence weight
    conf_weight = calculate_confidence_weight(
        projection.prob_ci_width,
        tau_conf
    )
    
    # Calculate value weight
    value_weight = calculate_value_weight(
        value_result.edge_pct or 0.0,
        target_edge_pct
    )
    
    # Calculate final stake fraction
    stake_fraction = kelly * conf_weight * value_weight
    
    # Apply stake cap
    stake_fraction = min(stake_fraction, stake_cap)
    
    # Calculate stake amount
    stake_amount = bankroll * stake_fraction
    
    return StakingResult(
        stake_mode="dynamic",
        stake_amount=stake_amount,
        stake_fraction=stake_fraction,
        kelly_fraction=kelly,
        confidence_weight=conf_weight,
        value_weight=value_weight
    )


def calculate_flat_stake(
    flat_size: float,
    bankroll: float
) -> StakingResult:
    """Calculate flat stake amount."""
    
    # Ensure stake doesn't exceed bankroll
    stake_amount = min(flat_size, bankroll)
    stake_fraction = stake_amount / bankroll if bankroll > 0 else 0.0
    
    return StakingResult(
        stake_mode="flat",
        stake_amount=stake_amount,
        stake_fraction=stake_fraction
    )


def calculate_stake(
    projection: ProjectionResult,
    value_result: ValueResult,
    stake_mode: str,
    bankroll: float,
    flat_size: float = 10.0,
    kelly_fraction: float = 0.5,
    tau_conf: float = 0.20,
    target_edge_pct: float = 5.0,
    stake_cap: float = 0.03
) -> StakingResult:
    """Calculate stake based on mode and parameters."""
    
    if stake_mode == "dynamic":
        return calculate_dynamic_stake(
            projection=projection,
            value_result=value_result,
            bankroll=bankroll,
            kelly_fraction=kelly_fraction,
            tau_conf=tau_conf,
            target_edge_pct=target_edge_pct,
            stake_cap=stake_cap
        )
    elif stake_mode == "flat":
        return calculate_flat_stake(flat_size, bankroll)
    else:
        raise ValueError(f"Invalid stake mode: {stake_mode}")


def validate_stake(
    stake_result: StakingResult,
    bankroll: float,
    min_stake: float = 1.0,
    max_stake_fraction: float = 0.1
) -> Tuple[bool, List[str]]:
    """Validate stake calculation."""
    
    reasons = []
    
    if stake_result.stake_amount < min_stake:
        reasons.append(f"Stake too small: {stake_result.stake_amount:.2f} < {min_stake}")
    
    if stake_result.stake_fraction > max_stake_fraction:
        reasons.append(f"Stake fraction too high: {stake_result.stake_fraction:.3f} > {max_stake_fraction}")
    
    if stake_result.stake_amount > bankroll:
        reasons.append(f"Stake exceeds bankroll: {stake_result.stake_amount:.2f} > {bankroll}")
    
    valid = len(reasons) == 0
    return valid, reasons


def get_stake_summary(stake_result: StakingResult) -> dict:
    """Get summary of staking calculation."""
    
    summary = {
        "stake_mode": stake_result.stake_mode,
        "stake_amount": stake_result.stake_amount,
        "stake_fraction": stake_result.stake_fraction
    }
    
    if stake_result.kelly_fraction is not None:
        summary["kelly_fraction"] = stake_result.kelly_fraction
    
    if stake_result.confidence_weight is not None:
        summary["confidence_weight"] = stake_result.confidence_weight
    
    if stake_result.value_weight is not None:
        summary["value_weight"] = stake_result.value_weight
    
    return summary
