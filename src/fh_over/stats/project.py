"""Statistical projection and confidence interval calculations."""

from typing import Tuple, List
import numpy as np
from scipy import stats
from dataclasses import dataclass

from .samples import TeamSamples


@dataclass
class ProjectionResult:
    """Result of statistical projection."""
    lambda_hat: float
    p_hat: float
    p_ci_low: float
    p_ci_high: float
    prob_ci_width: float
    n_bootstrap: int


def calculate_lambda_hat(home_samples: TeamSamples, away_samples: TeamSamples) -> float:
    """Calculate lambda_hat as median of home and away means."""
    
    home_mean = np.mean(home_samples.samples) if home_samples.samples else 0.0
    away_mean = np.mean(away_samples.samples) if away_samples.samples else 0.0
    
    # Use median of the two means (which equals their average for two values)
    return float(np.median([home_mean, away_mean]))


def poisson_probability_over_05(lambda_val: float) -> float:
    """Calculate probability of Over 0.5 goals using Poisson distribution."""
    # P(X > 0.5) = 1 - P(X = 0) = 1 - exp(-lambda)
    return 1.0 - np.exp(-lambda_val)


def bootstrap_samples(
    home_samples: TeamSamples,
    away_samples: TeamSamples,
    n_bootstrap: int = 5000
) -> List[float]:
    """Bootstrap resample from home and away samples."""
    
    # Combine all samples for joint resampling
    all_samples = home_samples.samples + away_samples.samples
    
    if not all_samples:
        return [0.0] * n_bootstrap
    
    # Bootstrap resampling
    bootstrap_lambdas = []
    
    for _ in range(n_bootstrap):
        # Resample with replacement
        resampled = np.random.choice(all_samples, size=len(all_samples), replace=True)
        
        # Calculate lambda for this bootstrap sample
        lambda_val = float(np.mean(resampled))
        bootstrap_lambdas.append(lambda_val)
    
    return bootstrap_lambdas


def calculate_confidence_intervals(
    bootstrap_lambdas: List[float],
    confidence_level: float = 0.95
) -> Tuple[float, float, float]:
    """Calculate confidence intervals for lambda and probability."""
    
    if not bootstrap_lambdas:
        return 0.0, 0.0, 0.0
    
    # Calculate CI for lambda
    alpha = 1 - confidence_level
    lambda_ci_low = np.percentile(bootstrap_lambdas, 100 * alpha / 2)
    lambda_ci_high = np.percentile(bootstrap_lambdas, 100 * (1 - alpha / 2))
    
    # Calculate CI for probability
    prob_samples = [poisson_probability_over_05(lam) for lam in bootstrap_lambdas]
    p_ci_low = np.percentile(prob_samples, 100 * alpha / 2)
    p_ci_high = np.percentile(prob_samples, 100 * (1 - alpha / 2))
    
    return p_ci_low, p_ci_high, p_ci_high - p_ci_low


def project_first_half_over_05(
    home_samples: TeamSamples,
    away_samples: TeamSamples,
    n_bootstrap: int = 5000,
    confidence_level: float = 0.95
) -> ProjectionResult:
    """Project probability of first-half Over 0.5 goals."""
    
    # Calculate lambda_hat
    lambda_hat = calculate_lambda_hat(home_samples, away_samples)
    
    # Calculate point estimate for probability
    p_hat = poisson_probability_over_05(lambda_hat)
    
    # Bootstrap for confidence intervals
    bootstrap_lambdas = bootstrap_samples(home_samples, away_samples, n_bootstrap)
    
    # Calculate confidence intervals
    p_ci_low, p_ci_high, prob_ci_width = calculate_confidence_intervals(
        bootstrap_lambdas, confidence_level
    )
    
    return ProjectionResult(
        lambda_hat=lambda_hat,
        p_hat=p_hat,
        p_ci_low=p_ci_low,
        p_ci_high=p_ci_high,
        prob_ci_width=prob_ci_width,
        n_bootstrap=n_bootstrap
    )


def calculate_fair_odds(p_hat: float) -> float:
    """Calculate fair odds from probability."""
    if p_hat <= 0 or p_hat >= 1:
        return 1.0
    return 1.0 / p_hat


def validate_projection(
    projection: ProjectionResult,
    lambda_threshold: float = 1.5,
    max_prob_ci_width: float = 0.20
) -> Tuple[bool, List[str]]:
    """Validate projection meets quality thresholds."""
    
    reasons = []
    
    if projection.lambda_hat < lambda_threshold:
        reasons.append(f"Lambda too low: {projection.lambda_hat:.3f} < {lambda_threshold}")
    
    if projection.prob_ci_width > max_prob_ci_width:
        reasons.append(f"CI width too wide: {projection.prob_ci_width:.3f} > {max_prob_ci_width}")
    
    if projection.p_hat <= 0 or projection.p_hat >= 1:
        reasons.append(f"Invalid probability: {projection.p_hat:.3f}")
    
    valid = len(reasons) == 0
    return valid, reasons


def get_projection_summary(projection: ProjectionResult) -> dict:
    """Get summary statistics for a projection."""
    
    return {
        "lambda_hat": projection.lambda_hat,
        "p_hat": projection.p_hat,
        "p_ci_low": projection.p_ci_low,
        "p_ci_high": projection.p_ci_high,
        "prob_ci_width": projection.prob_ci_width,
        "fair_odds": calculate_fair_odds(projection.p_hat),
        "n_bootstrap": projection.n_bootstrap
    }
