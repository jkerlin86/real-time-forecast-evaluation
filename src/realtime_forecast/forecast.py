"""The honest-vs-naive experiment.

One fixed benchmark specification, applied identically to both arms:

- an autoregression on the growth rate, order p chosen by BIC inside each
  training window (p in 0..max_p; p = 0 is the historical-mean forecast),
- estimated recursively at every forecast origin.

The honest (real-time) arm estimates on the vintage that was actually
available at the origin. The naive arm estimates the identical specification
on the latest vintage (final data). Both are scored against the same target:
the latest-vintage growth rate of the target period. Any accuracy advantage
of the naive arm is accuracy no forecaster could have had.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from .vintages import as_of, growth


def ar_forecast(train_growth: pd.Series, max_p: int = 12) -> tuple[float, int]:
    """One-step AR(p) forecast with BIC order selection inside the window.

    Returns the forecast and the selected order. Estimation uses only the
    series handed in; the caller is responsible for handing in the right
    vintage (and the engine asserts it).
    """
    y = train_growth.dropna().to_numpy(dtype=float)
    n = len(y)
    if n < max_p + 24:
        raise ValueError("Training window too short for AR order selection")
    best = None
    for p in range(0, max_p + 1):
        if p == 0:
            resid = y - y.mean()
            sse = float((resid**2).sum())
            k = 1
            forecast = float(y.mean())
        else:
            x = np.column_stack([np.ones(n - p)] + [y[p - j - 1 : n - j - 1] for j in range(p)])
            beta, *_ = np.linalg.lstsq(x, y[p:], rcond=None)
            resid = y[p:] - x @ beta
            sse = float((resid**2).sum())
            k = p + 1
            last = np.array([1.0] + [y[-1 - j] for j in range(p)])
            forecast = float(last @ beta)
        m = len(resid)
        bic = m * np.log(max(sse, 1e-300) / m) + k * np.log(m)
        if best is None or bic < best[0]:
            best = (bic, forecast, p)
    return best[1], best[2]


def _origin_target(matrix: pd.DataFrame, vintage: pd.Period) -> pd.Period:
    """First observation period not yet published in ``vintage``."""
    column = matrix[vintage].dropna()
    last_known = column.index[-1]
    return last_known + 1


def run_evaluation(
    matrix: pd.DataFrame,
    origins: list[pd.Period],
    max_p: int = 12,
    min_train: int = 60,
    check_leakage: bool = True,
) -> pd.DataFrame:
    """Run both arms over ``origins`` and return per-origin forecast records.

    For each origin (a vintage), the target is the first observation not yet
    published in that vintage. The real-time arm trains on growth computed
    inside that vintage's column; the naive arm trains on growth from the
    latest vintage over the same observation span (observations up to the
    last one the origin vintage contains). Both forecasts are scored against
    the latest-vintage growth of the target.
    """
    from .vintages import assert_no_future_vintage

    latest_growth = growth(matrix.iloc[:, -1])
    records = []
    for vintage in origins:
        column = as_of(matrix, vintage)
        if check_leakage:
            assert_no_future_vintage(matrix, vintage, column)
        target = _origin_target(matrix, vintage)
        actual = latest_growth.get(target, np.nan)
        if pd.isna(actual):
            continue
        rt_growth = growth(column).dropna()
        if len(rt_growth) < min_train:
            continue
        rt_forecast, rt_p = ar_forecast(rt_growth, max_p=max_p)
        naive_column = matrix.iloc[:, -1].reindex(column.dropna().index)
        nv_growth = growth(naive_column).dropna()
        nv_forecast, nv_p = ar_forecast(nv_growth, max_p=max_p)
        records.append(
            {
                "origin_vintage": vintage,
                "target_period": target,
                "actual_latest_growth": float(actual),
                "realtime_forecast": float(rt_forecast),
                "realtime_p": int(rt_p),
                "naive_forecast": float(nv_forecast),
                "naive_p": int(nv_p),
            }
        )
    frame = pd.DataFrame.from_records(records)
    if len(frame):
        frame["realtime_error"] = frame["actual_latest_growth"] - frame["realtime_forecast"]
        frame["naive_error"] = frame["actual_latest_growth"] - frame["naive_forecast"]
    return frame


def score(frame: pd.DataFrame) -> dict:
    """RMSE / MAE for both arms on the evaluation frame."""
    out = {"n_origins": int(len(frame))}
    for arm in ["realtime", "naive"]:
        err = frame[f"{arm}_error"].to_numpy(dtype=float)
        out[f"{arm}_rmse"] = float(np.sqrt(np.mean(err**2)))
        out[f"{arm}_mae"] = float(np.mean(np.abs(err)))
    out["rmse_gap_naive_minus_realtime"] = out["naive_rmse"] - out["realtime_rmse"]
    return out


def diebold_mariano(frame: pd.DataFrame, h: int = 1) -> dict:
    """Diebold-Mariano test on squared-error loss differential.

    d_t = e_naive^2 - e_realtime^2; a positive mean with a significant
    statistic means the naive (final-data) track record is significantly
    worse... note the sign convention carefully: because the naive arm is
    expected to look *better* than it honestly was, the interesting outcome
    here is a *negative* mean differential with significance, i.e. the
    final-data evaluation flatters the model. Newey-West lag = h.
    """
    d = frame["naive_error"].to_numpy(dtype=float) ** 2 - frame["realtime_error"].to_numpy(
        dtype=float
    ) ** 2
    n = len(d)
    mean_d = float(d.mean())
    gamma0 = float(np.var(d, ddof=1))
    var_mean = gamma0 / n
    for lag in range(1, h + 1):
        cov = float(np.cov(d[lag:], d[:-lag], ddof=1)[0, 1])
        var_mean += 2 * (1 - lag / (h + 1)) * cov / n
    if var_mean <= 0:
        return {"n": n, "mean_loss_diff_naive_minus_realtime": mean_d, "status": "degenerate"}
    dm = mean_d / np.sqrt(var_mean)
    p = 2 * (1 - scipy_stats.t.cdf(abs(dm), df=n - 1))
    return {
        "n": n,
        "mean_loss_diff_naive_minus_realtime": mean_d,
        "dm_statistic": float(dm),
        "dm_p_value": float(p),
        "lag": h,
    }


def block_bootstrap_gap(
    frame: pd.DataFrame, block: int = 12, reps: int = 2000, seed: int = 20261110
) -> dict:
    """Circular block bootstrap of the RMSE gap (naive minus real-time).

    Resamples blocks of origins to respect the serial dependence induced by
    overlapping revision windows. Returns the percentile interval for the
    gap; a gap whose interval excludes zero in the negative direction is the
    measured flattery of final-data evaluation.
    """
    e_rt = frame["realtime_error"].to_numpy(dtype=float)
    e_nv = frame["naive_error"].to_numpy(dtype=float)
    n = len(frame)
    rng = np.random.default_rng(seed)
    gaps = np.empty(reps)
    n_blocks = int(np.ceil(n / block))
    for r in range(reps):
        starts = rng.integers(0, n, size=n_blocks)
        idx = np.concatenate([(np.arange(s, s + block) % n) for s in starts])[:n]
        gaps[r] = np.sqrt(np.mean(e_nv[idx] ** 2)) - np.sqrt(np.mean(e_rt[idx] ** 2))
    return {
        "reps": reps,
        "block": block,
        "seed": seed,
        "gap_p05": float(np.quantile(gaps, 0.05)),
        "gap_p50": float(np.quantile(gaps, 0.50)),
        "gap_p95": float(np.quantile(gaps, 0.95)),
        "gap_ci90_low": float(np.quantile(gaps, 0.05)),
        "gap_ci90_high": float(np.quantile(gaps, 0.95)),
        "share_of_reps_gap_negative": float((gaps < 0).mean()),
    }
