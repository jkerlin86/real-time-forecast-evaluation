import numpy as np
import pandas as pd
import pytest

from realtime_forecast.forecast import ar_forecast, run_evaluation, score
from realtime_forecast.synthetic import make_synthetic_matrix
from realtime_forecast.vintages import assert_no_future_vintage, as_of


def test_leakage_assertion_fires_on_contaminated_column():
    """MANDATORY GATE (negative direction): a training series taken from a
    later vintage must trip the assertion."""
    matrix, _ = make_synthetic_matrix()
    origin = matrix.columns[80]
    later = matrix.columns[100]
    contaminated = as_of(matrix, later)
    with pytest.raises(AssertionError):
        assert_no_future_vintage(matrix, origin, contaminated)


def test_leakage_assertion_accepts_the_true_asof_column():
    matrix, _ = make_synthetic_matrix()
    origin = matrix.columns[80]
    assert_no_future_vintage(matrix, origin, as_of(matrix, origin))


def test_future_vintages_cannot_change_realtime_forecasts():
    """MANDATORY GATE (functional): corrupting every vintage after a set of
    origins must leave those origins' real-time forecasts bit-identical."""
    matrix, _ = make_synthetic_matrix()
    origins = list(matrix.columns[90:96])
    clean = run_evaluation(matrix, origins, max_p=4, min_train=60)
    corrupted = matrix.copy()
    cutoff = origins[-1]
    later_cols = [c for c in corrupted.columns if c > cutoff]
    corrupted.loc[:, later_cols] = (corrupted.loc[:, later_cols] * 7.0).to_numpy()
    dirty = run_evaluation(corrupted, origins, max_p=4, min_train=60, check_leakage=True)
    assert len(clean) == len(dirty) > 0
    assert np.allclose(
        clean["realtime_forecast"].to_numpy(), dirty["realtime_forecast"].to_numpy()
    )


def test_run_evaluation_on_synthetic_produces_both_arms():
    matrix, _ = make_synthetic_matrix()
    origins = list(matrix.columns[100:110])
    frame = run_evaluation(matrix, origins, max_p=4, min_train=60)
    assert len(frame) > 0
    assert {"realtime_error", "naive_error"} <= set(frame.columns)
    s = score(frame)
    assert s["n_origins"] == len(frame)
    assert s["realtime_rmse"] > 0 and s["naive_rmse"] > 0


def test_ar_forecast_recovers_mean_for_white_noise():
    rng = np.random.default_rng(7)
    y = pd.Series(rng.normal(0.3, 0.1, size=200))
    forecast, _ = ar_forecast(y, max_p=4)
    assert abs(forecast - 0.3) < 0.06
