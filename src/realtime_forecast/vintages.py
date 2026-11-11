"""Vintage-matrix handling.

A vintage matrix is a two-dimensional frame: rows are observation periods,
columns are vintage dates, and each cell is the value of that observation as
published in that vintage. The single most important operation is the as-of
extraction: the series as it was known at a given vintage. Every extraction
in this package asserts that no cell from a later vintage is touched, which
is the programmatic form of the project's no-leakage rule.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

_VINTAGE_RE = re.compile(r"(\d{2}|\d{4})[MQ](\d{1,2})$")


def parse_vintage_label(label: str, freq: str) -> pd.Period:
    """Parse an RTDSM vintage column label such as ``PCPI98M11`` or ``PCON05Q3``.

    Labels carry a two-digit year (a four-digit year is also accepted). The
    century rule matches the RTDSM files, whose earliest vintage is 1965Q4:
    years 60 and above are 19xx, years below 60 are 20xx.
    """
    m = _VINTAGE_RE.search(str(label).strip())
    if m is None:
        raise ValueError(f"Unrecognised vintage label: {label!r}")
    year = int(m.group(1))
    if year < 100:
        year = 1900 + year if year >= 60 else 2000 + year
    sub = int(m.group(2))
    return pd.Period(year=year, month=sub, freq="M") if freq == "M" else pd.Period(
        year=year, quarter=sub, freq="Q"
    )


def parse_obs_label(label: str, freq: str) -> pd.Period:
    """Parse an RTDSM observation label such as ``1947:01`` or ``1947:Q1``."""
    text = str(label).strip()
    if freq == "M":
        year, month = text.split(":")
        return pd.Period(year=int(year), month=int(month), freq="M")
    year, quarter = text.upper().split(":Q")
    return pd.Period(year=int(year), quarter=int(quarter), freq="Q")


def load_rtdsm_matrix(path: str, freq: str) -> pd.DataFrame:
    """Load an RTDSM vintage file (xlsx) into a vintage matrix.

    Rows are observation periods (a monthly or quarterly :class:`pandas.PeriodIndex`),
    columns are vintage periods, values are floats with NaN where the vintage
    did not yet (or no longer) reports the observation.
    """
    raw = pd.read_excel(path, sheet_name=0)
    raw = raw.rename(columns={raw.columns[0]: "obs"})
    raw = raw[raw["obs"].notna()]
    obs = pd.PeriodIndex([parse_obs_label(x, freq) for x in raw["obs"]], freq=freq)
    vintages = [parse_vintage_label(c, freq) for c in raw.columns[1:]]
    values = raw.iloc[:, 1:].apply(pd.to_numeric, errors="coerce")
    matrix = pd.DataFrame(
        values.to_numpy(dtype=float),
        index=obs,
        columns=pd.PeriodIndex(vintages, freq=freq),
    )
    matrix = matrix.sort_index(axis=0).sort_index(axis=1)
    if matrix.index.has_duplicates or matrix.columns.has_duplicates:
        raise ValueError(f"Duplicate obs or vintage labels in {path}")
    return matrix


def as_of(matrix: pd.DataFrame, vintage: pd.Period) -> pd.Series:
    """Return the series exactly as known in ``vintage``.

    This is the only sanctioned way to read history for a forecast origin.
    The vintage must be a column of the matrix; anything else is a caller bug
    and raises, rather than silently reaching for a neighbouring vintage.
    """
    if vintage not in matrix.columns:
        raise KeyError(f"Vintage {vintage} is not a column of the matrix")
    return matrix.loc[:, vintage].copy()


def assert_no_future_vintage(matrix: pd.DataFrame, vintage: pd.Period, used: pd.Series) -> None:
    """Assert that ``used`` equals the as-of column for ``vintage`` exactly.

    The forecast engine calls this on the training data of every origin, so a
    leak is a test failure, not a modelling choice.
    """
    expected = as_of(matrix, vintage)
    aligned = used.reindex(expected.index)
    if not np.allclose(aligned.to_numpy(dtype=float), expected.to_numpy(dtype=float), equal_nan=True):
        raise AssertionError(
            f"Leakage: training data for origin {vintage} differ from the as-of vintage column"
        )


def first_release(matrix: pd.DataFrame) -> pd.Series:
    """First published value of each observation (first non-NaN across vintages)."""
    out = {}
    for obs, row in matrix.iterrows():
        valid = row.dropna()
        out[obs] = valid.iloc[0] if len(valid) else np.nan
    return pd.Series(out, dtype=float)


def first_vintage(matrix: pd.DataFrame) -> pd.Series:
    """First vintage in which each observation appears."""
    out = {}
    for obs, row in matrix.iterrows():
        valid = row.dropna()
        out[obs] = valid.index[0] if len(valid) else None
    return pd.Series(out, dtype=object)


def latest(matrix: pd.DataFrame) -> pd.Series:
    """Latest published value of each observation (the project's target vintage).

    "Latest" is the final column of the matrix as retrieved. It is treated as
    final for scoring, with the standing caveat that it is itself revisable.
    """
    return matrix.iloc[:, -1].copy()


def growth(series: pd.Series, periods: int = 1) -> pd.Series:
    """Percent growth over ``periods`` steps: 100 * log-difference."""
    return 100.0 * np.log(series / series.shift(periods))


def revision_frame(matrix: pd.DataFrame) -> pd.DataFrame:
    """Per-observation revision record: first release, latest, and the revision."""
    first = first_release(matrix)
    last = latest(matrix)
    fv = first_vintage(matrix)
    frame = pd.DataFrame(
        {
            "first_release": first,
            "latest": last,
            "first_vintage": fv,
            "revision_latest_minus_first": last - first,
        }
    )
    return frame
