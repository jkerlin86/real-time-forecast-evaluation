"""Revision analysis: how much, in which direction, and how predictably do
first releases move?

The noise-vs-news diagnostic follows the classical regression form: regress
the revision (latest minus first release) on the first release itself. If
first releases were efficient forecasts of the final value (pure "news"
revisions), the slope would be zero and the revision unpredictable. A
significant slope on information available at first release means part of
the revision was, in principle, knowable at release time ("noise").
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .vintages import growth


def revision_stats(frame: pd.DataFrame, value_col: str = "first_release") -> dict:
    """Distribution of the revision of a transformed series.

    ``frame`` is a revision frame on the transformed scale (for example,
    monthly percent growth): columns first_release, latest, revision.
    Revisions of exactly zero are common for price indexes with long final
    stretches; the share revised is reported alongside, never hidden.
    """
    rev = frame["revision_latest_minus_first"].dropna()
    first = frame.loc[rev.index, value_col]
    if len(rev) == 0:
        return {"n": 0}
    return {
        "n": int(len(rev)),
        "mean_revision": float(rev.mean()),
        "mean_abs_revision": float(rev.abs().mean()),
        "median_abs_revision": float(rev.abs().median()),
        "sd_revision": float(rev.std(ddof=1)) if len(rev) > 1 else 0.0,
        "share_revised_up": float((rev > 0).mean()),
        "share_revised_down": float((rev < 0).mean()),
        "share_unrevised": float((rev == 0).mean()),
        "p90_abs_revision": float(rev.abs().quantile(0.90)),
        "corr_first_revision": float(np.corrcoef(first, rev)[0, 1]) if len(rev) > 2 else np.nan,
    }


def growth_revision_frame(matrix: pd.DataFrame, min_age_vintages: int = 24) -> pd.DataFrame:
    """Revision frame on the growth scale, maturity-restricted.

    First-release growth of observation t is the growth rate as published in
    the first vintage that contains t (which is also the first vintage whose
    growth for t can be computed from consecutive values in that vintage).
    Latest growth uses the latest vintage throughout. Only observations
    whose first vintage is at least ``min_age_vintages`` before the final
    vintage are included: a recently published observation has not finished
    revising, and including it would understate revisions mechanically.
    """
    first_growth = {}
    for vintage in matrix.columns:
        column = matrix[vintage]
        g = growth(column)
        for obs, value in g.items():
            if pd.notna(value) and obs not in first_growth:
                first_growth[obs] = (vintage, value)
    latest_growth = growth(matrix.iloc[:, -1])
    vintage_positions = {v: i for i, v in enumerate(matrix.columns)}
    last_position = len(matrix.columns) - 1
    rows = {}
    for obs, (vintage, value) in first_growth.items():
        if last_position - vintage_positions[vintage] < min_age_vintages:
            continue
        if obs in latest_growth.index and pd.notna(latest_growth[obs]):
            rows[obs] = {
                "first_release": value,
                "latest": float(latest_growth[obs]),
                "first_vintage": vintage,
            }
    frame = pd.DataFrame.from_dict(rows, orient="index")
    frame["revision_latest_minus_first"] = frame["latest"] - frame["first_release"]
    return frame.sort_index()


def noise_vs_news(frame: pd.DataFrame, hac_lags: int = 12) -> dict:
    """Regress the revision on the first release (HAC standard errors).

    Returns the slope, its HAC t-statistic and p-value, and the R-squared.
    A slope significantly different from zero rejects the pure-news null in
    favour of a predictable (noise) component.
    """
    data = frame[["first_release", "revision_latest_minus_first"]].dropna()
    if len(data) < 30:
        return {"n": int(len(data)), "status": "insufficient observations"}
    x = sm.add_constant(data["first_release"].to_numpy(dtype=float))
    y = data["revision_latest_minus_first"].to_numpy(dtype=float)
    fit = sm.OLS(y, x).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    return {
        "n": int(len(data)),
        "intercept": float(fit.params[0]),
        "slope_on_first_release": float(fit.params[1]),
        "slope_se_hac": float(fit.bse[1]),
        "slope_t": float(fit.tvalues[1]),
        "slope_p": float(fit.pvalues[1]),
        "r_squared": float(fit.rsquared),
    }


def cycle_phase(index: pd.PeriodIndex, freq: str = "M") -> pd.Series:
    """Business-cycle phase of each period, from NBER peak/trough dates.

    Phases are expansion and contraction, assigned by the NBER monthly cycle
    chronology (peaks and troughs as published by the NBER Business Cycle
    Dating Committee). For quarterly series the phase is the phase of the
    quarter's middle month.
    """
    peaks = ["2001-03", "2007-12", "2020-02"]
    troughs = ["2001-11", "2009-06", "2020-04"]
    months = index.to_timestamp(how="start").to_period("M") if freq != "M" else index
    if freq == "Q":
        months = pd.PeriodIndex([p.asfreq("M", how="start") + 1 for p in index], freq="M")
    phase = pd.Series("expansion", index=index, dtype=object)
    for peak, trough in zip(peaks, troughs, strict=True):
        p = pd.Period(peak, freq="M")
        t = pd.Period(trough, freq="M")
        mask = np.asarray((months >= p) & (months <= t))
        if mask.any():
            phase.iloc[np.flatnonzero(mask)] = "contraction"
    return phase


def revision_stats_by_phase(frame: pd.DataFrame, freq: str = "M") -> dict:
    """Revision statistics split by NBER cycle phase (where n supports it)."""
    phases = cycle_phase(pd.PeriodIndex(frame.index, freq=freq), freq=freq)
    phase_values = phases.to_numpy()
    out = {}
    for name in ["expansion", "contraction"]:
        sub = frame[phase_values == name]
        stats = revision_stats(sub)
        stats["reported"] = bool(stats.get("n", 0) >= 24)
        out[name] = stats
    return out


def vintage_coverage(matrix: pd.DataFrame) -> dict:
    """Coverage facts of a vintage matrix, exactly as retrieved."""
    first_col = matrix.iloc[:, 0].dropna()
    last_col = matrix.iloc[:, -1].dropna()
    return {
        "n_observations": int(matrix.shape[0]),
        "n_vintages": int(matrix.shape[1]),
        "first_vintage": str(matrix.columns[0]),
        "last_vintage": str(matrix.columns[-1]),
        "first_obs_in_first_vintage": str(first_col.index[0]) if len(first_col) else None,
        "last_obs_in_first_vintage": str(first_col.index[-1]) if len(first_col) else None,
        "first_obs_in_latest_vintage": str(last_col.index[0]) if len(last_col) else None,
        "last_obs_in_latest_vintage": str(last_col.index[-1]) if len(last_col) else None,
        "cells_populated": int(matrix.notna().sum().sum()),
    }
