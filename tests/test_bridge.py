from pathlib import Path

import pandas as pd
import pytest

from realtime_forecast.bridge import (
    monthly_vintage_for_quarter,
    run_bridge_evaluation,
)
from realtime_forecast.vintages import load_rtdsm_matrix


def test_monthly_vintage_alignment_is_middle_month():
    assert monthly_vintage_for_quarter(pd.Period("2015Q1", freq="Q")) == pd.Period(
        "2015-02", freq="M"
    )
    assert monthly_vintage_for_quarter(pd.Period("2015Q4", freq="Q")) == pd.Period(
        "2015-11", freq="M"
    )


@pytest.mark.skipif(
    not Path("data/raw/pcpiMvMd.xlsx").exists(),
    reason="raw data not downloaded")
def test_bridge_runs_on_real_matrices():
    pce = load_rtdsm_matrix("data/raw/pconQvQd.xlsx", "Q")
    cpi = load_rtdsm_matrix("data/raw/pcpiMvMd.xlsx", "M")
    ppi = load_rtdsm_matrix("data/raw/pppiMvMd.xlsx", "M")
    origins = [c for c in pce.columns if pd.Period("2010Q1", freq="Q") <= c <= pd.Period("2012Q4", freq="Q")]
    frame = run_bridge_evaluation(pce, cpi, ppi, origins, min_train=40)
    assert len(frame) >= 8
    assert {"realtime_error", "naive_error"} <= set(frame.columns)
