import numpy as np

from realtime_forecast.revisions import (
    growth_revision_frame,
    noise_vs_news,
    revision_stats,
)
from realtime_forecast.synthetic import make_synthetic_matrix


def test_synthetic_recovery_gate():
    """MANDATORY GATE: the pipeline recovers the planted revision statistics.

    On the synthetic matrix the mean revision must equal minus the planted
    noise mean, and the mean absolute revision must equal the mean absolute
    planted noise, within tolerance. The comparison uses the same
    maturity restriction the real-data analysis uses.
    """
    matrix, planted = make_synthetic_matrix()
    frame = growth_revision_frame(matrix, min_age_vintages=24)
    stats = revision_stats(frame)
    assert stats["n"] > 100
    assert abs(stats["mean_revision"] - planted["expected_mean_revision"]) < 0.02
    assert abs(stats["mean_abs_revision"] - planted["expected_mean_abs_revision"]) < 0.02


def test_synthetic_noise_is_detectable():
    """The planted noise makes revisions predictable from the first release."""
    matrix, _ = make_synthetic_matrix()
    frame = growth_revision_frame(matrix, min_age_vintages=24)
    nn = noise_vs_news(frame, hac_lags=12)
    assert nn["slope_on_first_release"] < 0
    assert nn["slope_p"] < 0.01


def test_revision_stats_on_handcrafted_frame():
    import pandas as pd

    frame = pd.DataFrame(
        {
            "first_release": [1.0, 2.0, 3.0],
            "latest": [1.5, 2.0, 2.0],
            "revision_latest_minus_first": [0.5, 0.0, -1.0],
        }
    )
    stats = revision_stats(frame)
    assert stats["n"] == 3
    assert abs(stats["mean_revision"] - (-0.5 / 3)) < 1e-9
    assert stats["share_revised_up"] == 1 / 3
    assert stats["share_unrevised"] == 1 / 3
    assert np.isclose(stats["mean_abs_revision"], 0.5)
