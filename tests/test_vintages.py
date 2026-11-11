import pandas as pd
import pytest

from realtime_forecast.vintages import (
    as_of,
    first_release,
    growth,
    latest,
    load_alfred_matrix,
    load_rtdsm_matrix,
    parse_obs_label,
    parse_vintage_label,
)


def test_parse_vintage_label_monthly():
    assert parse_vintage_label("PCPI98M11", "M") == pd.Period("1998-11", freq="M")
    assert parse_vintage_label("PCPI05M3", "M") == pd.Period("2005-03", freq="M")


def test_parse_vintage_label_quarterly_and_century_rule():
    assert parse_vintage_label("PCON65Q4", "Q") == pd.Period("1965Q4", freq="Q")
    assert parse_vintage_label("PCON26Q4", "Q") == pd.Period("2026Q4", freq="Q")


def test_parse_vintage_label_rejects_garbage():
    with pytest.raises(ValueError):
        parse_vintage_label("not-a-vintage", "M")


def test_parse_obs_label():
    assert parse_obs_label("1947:01", "M") == pd.Period("1947-01", freq="M")
    assert parse_obs_label("1947:Q1", "Q") == pd.Period("1947Q1", freq="Q")


def _toy_matrix():
    idx = pd.period_range("2020-01", periods=4, freq="M")
    cols = pd.period_range("2020-02", periods=3, freq="M")
    data = [
        [100.0, 100.0, 100.0],
        [101.0, 101.5, 101.5],
        [float("nan"), 103.0, 103.2],
        [float("nan"), float("nan"), 104.0],
    ]
    return pd.DataFrame(data, index=idx, columns=cols)


def test_first_release_and_latest():
    m = _toy_matrix()
    fr = first_release(m)
    assert fr.loc[pd.Period("2020-03", freq="M")] == 103.0
    assert latest(m).loc[pd.Period("2020-03", freq="M")] == 103.2


def test_as_of_rejects_unknown_vintage():
    with pytest.raises(KeyError):
        as_of(_toy_matrix(), pd.Period("1999-01", freq="M"))


def test_growth_is_log_difference_percent():
    s = pd.Series([100.0, 110.0], index=pd.period_range("2020-01", periods=2, freq="M"))
    g = growth(s)
    assert abs(g.iloc[1] - 100.0 * 0.0953102) < 1e-4


def test_load_rtdsm_matrix_pcpi_shape_and_span():
    m = load_rtdsm_matrix("data/raw/pcpiMvMd.xlsx", "M")
    assert m.shape[1] == 336
    assert str(m.columns[0]) == "1998-11"
    assert str(m.columns[-1]) == "2026-10"


def test_load_alfred_matrix_monthly_snapshots(tmp_path):
    path = tmp_path / "alfred_toy_vintages.csv"
    path.write_text(
        "date,vintage_date,realtime_end,value\n"
        "2020-01-01,2020-02-10,2020-03-14,100\n"
        "2020-01-01,2020-03-15,2020-05-04,101\n"
        "2020-01-01,2020-05-05,9999-12-31,102\n"
        "2020-02-01,2020-03-15,9999-12-31,50\n"
    )
    m = load_alfred_matrix(str(path), "M")
    # One column per month from the first to the last vintage month,
    # including 2020-04, a month with no vintage date.
    assert [str(c) for c in m.columns] == ["2020-02", "2020-03", "2020-04", "2020-05"]
    jan = pd.Period("2020-01", freq="M")
    feb = pd.Period("2020-02", freq="M")
    # February snapshot: only the 2020-02-10 vintage exists in the month.
    assert m.loc[jan, pd.Period("2020-02", freq="M")] == 100.0
    assert pd.isna(m.loc[feb, pd.Period("2020-02", freq="M")])
    # March snapshot takes the 2020-03-15 vintage (the revision is in).
    assert m.loc[jan, pd.Period("2020-03", freq="M")] == 101.0
    assert m.loc[feb, pd.Period("2020-03", freq="M")] == 50.0
    # April has no vintage date: the snapshot carries the March state.
    assert m.loc[jan, pd.Period("2020-04", freq="M")] == 101.0
    # May snapshot picks up the 2020-05-05 revision.
    assert m.loc[jan, pd.Period("2020-05", freq="M")] == 102.0


def test_load_alfred_matrix_rsafs_shape_and_span():
    m = load_alfred_matrix("data/raw/alfred_rsafs_vintages.csv", "M")
    assert m.shape == (417, 305)
    assert str(m.columns[0]) == "2001-06"
    assert str(m.columns[-1]) == "2026-10"
    assert str(m.index[0]) == "1992-01"
    assert str(m.index[-1]) == "2026-09"
    # The first snapshot contains history only through the last observation
    # published by the 2001-06-13 vintage.
    first_col = m.iloc[:, 0].dropna()
    assert str(first_col.index[-1]) == "2001-05"
