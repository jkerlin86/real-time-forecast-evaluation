import pandas as pd
import pytest

from realtime_forecast.vintages import (
    as_of,
    first_release,
    growth,
    latest,
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
