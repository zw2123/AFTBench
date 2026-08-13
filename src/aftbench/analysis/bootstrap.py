"""Deterministic bootstrap confidence interval computation.

Provides bootstrap_ci() for computing confidence intervals over arbitrary
scalar metrics using the percentile method with a fixed random seed for
reproducibility.
"""

from __future__ import annotations

import random
import statistics
from typing import Sequence


def bootstrap_ci(
    values: Sequence[float],
    seed: int = 42,
    n_bootstrap: int = 1000,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Compute a bootstrap confidence interval for the mean.

    Uses the percentile method: resample `values` with replacement
    `n_bootstrap` times, compute the mean of each resample, then return
    the (alpha/2) and (1 - alpha/2) percentiles of the bootstrap
    distribution as the lower and upper bounds.

    Args:
        values: Sequence of numeric observations.
        seed: Random seed for reproducibility.
        n_bootstrap: Number of bootstrap resamples.
        alpha: Significance level (e.g. 0.05 for a 95% CI).

    Returns:
        (lower, upper, mean) where lower and upper are the CI bounds
        and mean is the sample mean of the original values.

    Raises:
        ValueError: If values is empty.
    """
    if not values:
        raise ValueError("Cannot compute bootstrap CI on empty sequence")

    values_list = list(values)
    n = len(values_list)
    sample_mean = statistics.fmean(values_list)

    if n == 1:
        # Degenerate case: single observation, CI is just the point estimate
        return (sample_mean, sample_mean, sample_mean)

    rng = random.Random(seed)
    bootstrap_means: list[float] = []

    for _ in range(n_bootstrap):
        resample = [rng.choice(values_list) for _ in range(n)]
        bootstrap_means.append(statistics.fmean(resample))

    bootstrap_means.sort()

    # Percentile indices
    lower_pct = alpha / 2.0
    upper_pct = 1.0 - alpha / 2.0

    lower_idx = int(lower_pct * (n_bootstrap - 1))
    upper_idx = int(upper_pct * (n_bootstrap - 1))

    # Clamp indices
    lower_idx = max(0, min(lower_idx, n_bootstrap - 1))
    upper_idx = max(0, min(upper_idx, n_bootstrap - 1))

    lower = bootstrap_means[lower_idx]
    upper = bootstrap_means[upper_idx]

    return (lower, upper, sample_mean)


def bootstrap_ci_for_groups(
    rows: list,
    group_key_fn,
    value_fn,
    seed: int = 42,
    n_bootstrap: int = 1000,
    alpha: float = 0.05,
) -> dict[tuple, tuple[float, float, float]]:
    """Compute bootstrap CIs for grouped data.

    Args:
        rows: List of result rows.
        group_key_fn: Function extracting the group key from a row.
        value_fn: Function extracting the numeric value from a row.
        seed: Random seed.
        n_bootstrap: Number of bootstrap resamples.
        alpha: Significance level.

    Returns:
        Dict mapping group keys to (lower, upper, mean) tuples.
    """
    from collections import defaultdict

    groups: dict[tuple, list[float]] = defaultdict(list)
    for row in rows:
        key = group_key_fn(row)
        val = value_fn(row)
        if val is not None:
            groups[key].append(float(val))

    results: dict[tuple, tuple[float, float, float]] = {}
    for key, vals in groups.items():
        if vals:
            results[key] = bootstrap_ci(vals, seed=seed, n_bootstrap=n_bootstrap, alpha=alpha)

    return results
