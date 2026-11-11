"""Bridge specification for the PCE price index (the documented bridge case).

A bridge equation forecasts a quarterly aggregate from monthly indicators
observed inside the quarter. The origin is the quarterly vintage taken in
the middle month of quarter q: at that point the first month of q has been
published in both monthly price series, while the quarter's PCE price index
has not. The bridge regressors are that first month's CPI and PPI inflation,
taken from the monthly vintage of the quarter's middle month (the monthly
analogue of the same information date), plus an autoregressive term in
quarterly PCE inflation. The equation is estimated on final data assembled
with exactly the same timing, and estimated in real time on the vintages,
mirroring the AR experiment.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .vintages import growth


def monthly_vintage_for_quarter(quarter: pd.Period) -> pd.Period:
    """Monthly vintage aligned to a quarterly vintage: the quarter's middle month."""
    first_month = quarter.asfreq("M", how="start")
    return first_month + 1


def quarter_first_month_growth(
    monthly_matrix: pd.DataFrame, quarters: list[pd.Period], realtime: bool
) -> pd.Series:
    """Growth of the first month of each quarter, with release timing honoured.

    realtime=True reads the value from the monthly vintage of the quarter's
    middle month (only the first month of the quarter is published by then,
    and its growth uses the previous month from the same vintage).
    realtime=False reads the final (latest-vintage) value.
    """
    out = {}
    latest_growth = growth(monthly_matrix.iloc[:, -1])
    for q in quarters:
        first_month = q.asfreq("M", how="start")
        if realtime:
            vintage = monthly_vintage_for_quarter(q)
            if vintage not in monthly_matrix.columns:
                continue
            g = growth(monthly_matrix[vintage])
            value = g.get(first_month, np.nan)
        else:
            value = latest_growth.get(first_month, np.nan)
        if pd.notna(value):
            out[q] = float(value)
    return pd.Series(out, dtype=float)


def _design(
    pce_growth_series: pd.Series,
    cpi_first: pd.Series,
    ppi_first: pd.Series,
    target_quarter: pd.Period,
    train_end: pd.Period,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Assemble (X, y, x_forecast) for the bridge as of ``train_end``.

    Training rows are quarters up to ``train_end`` whose PCE growth and both
    first-month growth rates are available. The forecast row is
    ``target_quarter`` using its own first-month values (already published
    at the origin) and the PCE growth of ``train_end``.
    """
    rows_x, rows_y = [], []
    for q in pce_growth_series.index:
        if q > train_end:
            break
        if q in cpi_first.index and q in ppi_first.index and pd.notna(pce_growth_series[q]):
            prev = pce_growth_series.get(q - 1, np.nan)
            if pd.notna(prev):
                rows_x.append([1.0, cpi_first[q], ppi_first[q], prev])
                rows_y.append(pce_growth_series[q])
    x_fore = np.array(
        [
            [
                1.0,
                cpi_first[target_quarter],
                ppi_first[target_quarter],
                pce_growth_series[train_end],
            ]
        ]
    )
    return np.array(rows_x), np.array(rows_y), x_fore


def run_bridge_evaluation(
    pce_matrix: pd.DataFrame,
    cpi_matrix: pd.DataFrame,
    ppi_matrix: pd.DataFrame,
    origins: list[pd.Period],
    min_train: int = 40,
) -> pd.DataFrame:
    """Run the bridge in both arms over quarterly ``origins``.

    For origin vintage q (the vintage taken mid-quarter q), the target is
    quarter q's PCE inflation. Real-time arm: PCE history from vintage q's
    own prior column is not used; the PCE series as known at origin q is
    the column of vintage q (which contains quarters through q-1), and the
    first-month monthly growth rates come from the aligned monthly vintage.
    Naive arm: identical design on latest vintages throughout.
    """
    latest_pce_growth = growth(pce_matrix.iloc[:, -1])
    cpi_first_final = quarter_first_month_growth(cpi_matrix, list(pce_matrix.index), False)
    ppi_first_final = quarter_first_month_growth(ppi_matrix, list(pce_matrix.index), False)
    records = []
    for q in origins:
        if q not in pce_matrix.columns:
            continue
        target_actual = latest_pce_growth.get(q, np.nan)
        if pd.isna(target_actual):
            continue
        # real-time arm
        rt_pce_growth = growth(pce_matrix[q]).dropna()
        if len(rt_pce_growth) < min_train or (q - 1) not in rt_pce_growth.index:
            continue
        qs = [qq for qq in rt_pce_growth.index if qq < q]
        cpi_first_rt = quarter_first_month_growth(cpi_matrix, qs + [q], True)
        ppi_first_rt = quarter_first_month_growth(ppi_matrix, qs + [q], True)
        if q not in cpi_first_rt.index or q not in ppi_first_rt.index:
            continue
        x, y, xf = _design(rt_pce_growth, cpi_first_rt, ppi_first_rt, q, q - 1)
        if len(y) < min_train:
            continue
        fit_rt = sm.OLS(y, x).fit()
        rt_forecast = float(xf @ fit_rt.params)
        # naive arm: same design, latest data, training quarters before q
        nv_pce_growth = latest_pce_growth.reindex(rt_pce_growth.index)
        x2, y2, xf2 = _design(nv_pce_growth, cpi_first_final, ppi_first_final, q, q - 1)
        fit_nv = sm.OLS(y2, x2).fit()
        nv_forecast = float(xf2 @ fit_nv.params)
        records.append(
            {
                "origin_vintage": q,
                "target_period": q,
                "actual_latest_growth": float(target_actual),
                "realtime_forecast": rt_forecast,
                "naive_forecast": nv_forecast,
            }
        )
    frame = pd.DataFrame.from_records(records)
    if len(frame):
        frame["realtime_error"] = frame["actual_latest_growth"] - frame["realtime_forecast"]
        frame["naive_error"] = frame["actual_latest_growth"] - frame["naive_forecast"]
    return frame
