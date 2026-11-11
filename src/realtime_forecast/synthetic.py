"""Synthetic vintage matrices with planted revisions.

The validation gate needs data whose truth is known by construction:

- latent growth follows a stationary AR(1) (the data-generating process);
- the first release of observation t equals latent growth plus planted
  measurement noise with a known mean and standard deviation;
- each later vintage removes a fixed share of the remaining noise, so the
  latest vintage equals the latent truth exactly.

On such a matrix the revision statistics have known targets: the mean
revision (latest minus first release) equals minus the planted noise mean,
the mean absolute revision equals the mean absolute planted noise, and the
noise-vs-news slope on the first release is nonzero by construction (the
revision is mechanically predictable from the first release). The pipeline
must recover those targets within tolerance, and the leakage assertion must
fire when a training column is deliberately contaminated with a later
vintage.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_synthetic_matrix(
    n_obs: int = 240,
    n_vintages: int = 120,
    ar_coef: float = 0.45,
    growth_sd: float = 0.30,
    growth_mean: float = 0.25,
    noise_mean: float = -0.06,
    noise_sd: float = 0.20,
    revision_share: float = 0.5,
    seed: int = 20261110,
    freq: str = "M",
    start: str = "2000-01",
) -> tuple[pd.DataFrame, dict]:
    """Build the synthetic matrix in growth space, then integrate to levels.

    Vintages are the last ``n_vintages`` periods of the observation span;
    vintage v first publishes observation v (its diagonal), so the matrix
    has the same triangular availability pattern as a real RTDSM file.
    Returns the level matrix and the planted-parameter dict.
    """
    rng = np.random.default_rng(seed)
    obs_index = pd.period_range(start, periods=n_obs, freq=freq)
    eps = rng.normal(0.0, growth_sd, size=n_obs)
    g = np.empty(n_obs)
    g[0] = growth_mean
    for t in range(1, n_obs):
        g[t] = growth_mean + ar_coef * (g[t - 1] - growth_mean) + eps[t]
    noise = rng.normal(noise_mean, noise_sd, size=n_obs)

    vintage_index = obs_index[n_obs - n_vintages :]
    levels = np.full((n_obs, n_vintages), np.nan)
    # levels: integrate growth from a base of 100 at obs 0 (growth of obs 0
    # is defined against a pre-sample level of 100 in every vintage).
    for j, vintage in enumerate(vintage_index):
        latest_known = int(np.where(obs_index == vintage)[0][0])
        # observation t enters at vintage t; age a = j - (t - first_vintage_pos)
        first_vintage_pos = n_obs - n_vintages
        growth_vintage = np.full(n_obs, np.nan)
        for t in range(n_obs):
            if t < first_vintage_pos:
                # the first retained vintage is this observation's first
                # release in the matrix (age 0), then it revises normally
                age = j
            else:
                age = j - (t - first_vintage_pos)
            if t <= latest_known and age >= 0 and t >= 1:
                # every observation from t=1 on carries planted noise at first
                # release, including those published before the first retained
                # vintage (the matrix retains only their later vintages, so
                # the recovery test maturity-restricts, as on real data)
                growth_vintage[t] = g[t] + noise[t] * (1.0 - revision_share) ** age
        growth_vintage[0] = g[0]
        level = 100.0 * np.exp(np.cumsum(np.nan_to_num(growth_vintage, nan=0.0) / 100.0))
        level[:1] = 100.0 * np.exp(g[0] / 100.0)
        levels[:, j] = np.where(np.isnan(growth_vintage), np.nan, level)
    matrix = pd.DataFrame(levels, index=obs_index, columns=pd.PeriodIndex(vintage_index, freq=freq))
    planted = {
        "ar_coef": ar_coef,
        "growth_sd": growth_sd,
        "growth_mean": growth_mean,
        "noise_mean": noise_mean,
        "noise_sd": noise_sd,
        "revision_share": revision_share,
        "expected_mean_revision": -noise_mean,
        "expected_mean_abs_revision": float(np.mean(np.abs(noise))),
        "true_growth": g,
        "planted_noise": noise,
        "seed": seed,
    }
    return matrix, planted
